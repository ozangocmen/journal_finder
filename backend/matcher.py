"""
matcher.py
==========
Smart journal matching engine.

Pipeline v2.0
-------------
1. Extract Semantic Fingerprint of manuscript using Claude
2. Build TF-IDF corpus from journal titles + scope texts (Pre-filter)
3. Live Aims & Scope web retrieval for top candidates
4. Multi-dimensional CAS scoring using Claude
5. Bibliometric enrichment
6. Strategic Risk Assessment
"""

from __future__ import annotations

import re
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from .semantic_analyzer import extract_fingerprint, ManuscriptFingerprint
from .scope_retriever import retrieve_scope, ScopeResult
from .bibliometrics import enrich_bibliometrics
from .risk_assessor import assess_risks, RiskAssessment

# ── Text helpers ──────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Lowercase and strip non-alphanumeric characters (keep spaces)."""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _journal_corpus_text(row: pd.Series) -> str:
    """Combine all relevant journal fields into a single text blob."""
    parts = [
        row.get("journal_title", ""),
        row.get("scope", ""),
        row.get("subject_area", ""),
        row.get("subject_category", ""),
    ]
    return " ".join(str(p) for p in parts if p)


@dataclass
class ScoredJournal:
    journal_row: pd.Series
    scope_result: ScopeResult
    dim_a: float
    dim_b: float
    dim_c: float
    dim_d: float
    cas: float
    relevance_justification: str

@dataclass
class AnalysisResult:
    fingerprint: ManuscriptFingerprint
    shortlist: pd.DataFrame  # CAS >= 60%
    borderline: pd.DataFrame # 45% <= CAS < 60%
    risks: Dict[str, RiskAssessment]


# ── Legacy TF-IDF Matcher class ───────────────────────────────────────────────

class JournalMatcher:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True).copy()
        self.corpus = [_clean(_journal_corpus_text(row)) for _, row in self.df.iterrows()]
        self.vectorizer = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
            min_df=1, max_features=20_000, stop_words="english",
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def match(self, query: str, top_k: int = 50, q1_only: bool = True, publisher_filter: Optional[list[str]] = None, min_score: float = 0.01) -> pd.DataFrame:
        if not query.strip():
            return pd.DataFrame()
        if publisher_filter:
            mask = self.df["publisher_id"].isin(publisher_filter) if "publisher_id" in self.df.columns else pd.Series([True] * len(self.df))
            working_df    = self.df[mask].reset_index(drop=True)
            working_mat   = self.tfidf_matrix[mask.values if hasattr(mask, "values") else mask]
        else:
            working_df  = self.df
            working_mat = self.tfidf_matrix
        if q1_only:
            q1_mask     = working_df["sjr_quartile"].str.upper().str.contains("Q1", na=False)
            working_df  = working_df[q1_mask].reset_index(drop=True)
            working_mat = working_mat[q1_mask.values]
        if working_df.empty: return pd.DataFrame()

        q_vec = self.vectorizer.transform([_clean(query)])
        scores = cosine_similarity(q_vec, working_mat).flatten()
        result_df = working_df.copy()
        result_df["match_score"] = scores
        result_df = result_df[result_df["match_score"] >= min_score].sort_values("match_score", ascending=False).head(top_k).reset_index(drop=True)
        if not result_df.empty:
            max_s = result_df["match_score"].max()
            result_df["match_pct"] = ((result_df["match_score"] / max_s * 100).round(1) if max_s > 0 else 0.0)
        return result_df

    @staticmethod
    def highlight_keywords(text: str, query: str, max_len: int = 300) -> str:
        tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
        snippet = text[:max_len] + ("…" if len(text) > max_len else "")
        for tok in tokens:
            snippet = re.sub(f"(?i)({re.escape(tok)})", r"**\1**", snippet)
        return snippet


# ── RAG Matcher Pipeline ───────────────────────────────────────────────

class RAGMatcher:
    def __init__(self, df: pd.DataFrame, api_key: str = ""):
        self.df = df
        self.api_key = api_key
        self.tfidf_engine = JournalMatcher(df)

    def analyze(self, manuscript_text: str, top_k: int = 20, q1_only: bool = True) -> AnalysisResult:
        logger.info("Extracting Semantic Fingerprint...")
        fingerprint = extract_fingerprint(manuscript_text, self.api_key)
        
        # Determine query for TF-IDF pre-filter
        if fingerprint.primary_domain:
            query = " ".join(fingerprint.primary_domain + fingerprint.primary_targets + fingerprint.keywords.core)
            if not query.strip(): query = manuscript_text
        else:
            query = manuscript_text

        logger.info("Running TF-IDF pre-filter...")
        pre_results = self.tfidf_engine.match(query=query, top_k=min(top_k * 2, 50), q1_only=q1_only)
        
        if pre_results.empty:
            return AnalysisResult(fingerprint, pd.DataFrame(), pd.DataFrame(), {})

        if not self.api_key:
            # Fallback to TF-IDF only if no key
            shortlist = enrich_bibliometrics(pre_results)
            shortlist["cas"] = shortlist["match_pct"]
            shortlist["dim_a"] = shortlist["match_pct"]
            shortlist["dim_b"] = 0
            shortlist["dim_c"] = 0
            shortlist["dim_d"] = 0
            shortlist["relevance_justification"] = "Fallback scoring based on TF-IDF. API key required for full CAS."
            shortlist["scope_retrieval_status"] = "NOT ATTEMPTED"
            shortlist["scope_url"] = ""
            shortlist["scope_text"] = shortlist["scope"]
            return AnalysisResult(fingerprint, shortlist, pd.DataFrame(), {})

        logger.info("Retrieving live scopes in parallel...")
        scope_results: Dict[str, ScopeResult] = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    retrieve_scope, 
                    row["journal_title"], 
                    row.get("publisher", ""), 
                    row.get("issn", ""),
                    row.get("eissn", "")
                ): row["journal_title"] 
                for _, row in pre_results.iterrows()
            }
            for future in as_completed(futures):
                j_title = futures[future]
                try:
                    scope_results[j_title] = future.result()
                except Exception as e:
                    logger.warning(f"Error fetching scope for {j_title}: {e}")
                    scope_results[j_title] = ScopeResult("", "", "RETRIEVAL ERROR", 0)

        logger.info("Computing Multi-Dimensional CAS...")
        scored_journals = self._score_cas(fingerprint, pre_results, scope_results)

        # Build output dataframes
        rows = []
        for sj in scored_journals:
            row_dict = sj.journal_row.to_dict()
            row_dict.update({
                "cas": sj.cas,
                "dim_a": sj.dim_a,
                "dim_b": sj.dim_b,
                "dim_c": sj.dim_c,
                "dim_d": sj.dim_d,
                "relevance_justification": sj.relevance_justification,
                "scope_retrieval_status": sj.scope_result.retrieval_status,
                "scope_url": sj.scope_result.source_url,
                "scope_text": sj.scope_result.text if sj.scope_result.text else sj.journal_row.get("scope", "")
            })
            rows.append(row_dict)

        df_scored = pd.DataFrame(rows)
        # Sort by CAS descending
        df_scored = df_scored.sort_values("cas", ascending=False).reset_index(drop=True)

        logger.info("Enriching bibliometrics...")
        df_scored = enrich_bibliometrics(df_scored)

        shortlist_df = df_scored[df_scored["cas"] >= 60].copy()
        borderline_df = df_scored[(df_scored["cas"] >= 45) & (df_scored["cas"] < 60)].copy()

        # Only assess risks for the shortlist
        risks_dict = {}
        if not shortlist_df.empty:
            logger.info("Assessing strategic risks...")
            shortlist_dicts = shortlist_df.to_dict('records')
            risks_list = assess_risks(fingerprint, shortlist_dicts, self.api_key)
            for r in risks_list:
                risks_dict[r.journal_title] = r

        return AnalysisResult(fingerprint, shortlist_df, borderline_df, risks_dict)

    def _score_cas(self, fingerprint: ManuscriptFingerprint, pre_results: pd.DataFrame, scope_results: Dict[str, ScopeResult]) -> List[ScoredJournal]:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        fp_text = f"""
Domain: {fingerprint.primary_domain}
Targets: {fingerprint.primary_targets}
Methodologies: {fingerprint.methodologies}
Translational Stage: {fingerprint.translational_stage}
"""
        
        # Batching because of max token limits
        scored = []
        batch_size = 10
        for i in range(0, len(pre_results), batch_size):
            batch = pre_results.iloc[i:i+batch_size]
            journals_text = ""
            for _, r in batch.iterrows():
                j_title = r["journal_title"]
                sr = scope_results.get(j_title, ScopeResult("","", "ERROR", 0))
                scope_text = sr.text if sr.text else r.get("scope", "")
                journals_text += f"\n--- JOURNAL: {j_title} ---\nSCOPE: {scope_text[:1500]}\n"

            prompt = f"""You are an elite academic publishing engine calculating the Composite Alignment Score (CAS) for candidate journals.

MANUSCRIPT FINGERPRINT:
{fp_text}

JOURNALS TO SCORE:
{journals_text}

For each journal, calculate 4 dimensions (0-100 each):
- DimA (Topical Overlap): Alignment of topics/targets.
- DimB (Methodological Alignment): Alignment of study methods.
- DimC (Translational Stage Fit): Alignment of translational stage.
- DimD (Audience & Impact Fit): Alignment of intended audience.

Output strictly as a JSON array of objects with keys:
"journal_title", "dim_a", "dim_b", "dim_c", "dim_d", "relevance_justification" (3-5 sentences explaining the alignment).
"""
            try:
                msg = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )
                txt = msg.content[0].text
                clean_text = re.sub(r'```json\s*', '', txt)
                clean_text = re.sub(r'```', '', clean_text).strip()
                data = json.loads(clean_text)

                for r in data:
                    j_title = r.get("journal_title")
                    # Find matching row
                    row_match = batch[batch["journal_title"].str.lower() == str(j_title).lower()]
                    if row_match.empty:
                        # fuzzy match if exact fails
                        continue
                    row = row_match.iloc[0]
                    
                    da, db, dc, dd = float(r.get("dim_a", 0)), float(r.get("dim_b", 0)), float(r.get("dim_c", 0)), float(r.get("dim_d", 0))
                    cas = (0.35 * da) + (0.25 * db) + (0.20 * dc) + (0.20 * dd)
                    
                    scored.append(ScoredJournal(
                        journal_row=row,
                        scope_result=scope_results.get(j_title, ScopeResult("","", "ERROR", 0)),
                        dim_a=da, dim_b=db, dim_c=dc, dim_d=dd, cas=round(cas, 1),
                        relevance_justification=r.get("relevance_justification", "")
                    ))

            except Exception as e:
                logger.error(f"CAS Scoring batch failed: {e}")
                # Fallback to zeros for this batch
                for _, r in batch.iterrows():
                    scored.append(ScoredJournal(
                        journal_row=r,
                        scope_result=scope_results.get(r["journal_title"], ScopeResult("","", "ERROR", 0)),
                        dim_a=0, dim_b=0, dim_c=0, dim_d=0, cas=0,
                        relevance_justification="Scoring failed."
                    ))

        return scored
