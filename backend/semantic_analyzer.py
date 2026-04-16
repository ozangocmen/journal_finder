import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class KeywordTaxonomy:
    core: List[str] = field(default_factory=list)
    supporting: List[str] = field(default_factory=list)
    peripheral: List[str] = field(default_factory=list)

@dataclass
class ManuscriptFingerprint:
    primary_domain: List[str] = field(default_factory=list)
    primary_targets: List[str] = field(default_factory=list)
    secondary_targets: List[str] = field(default_factory=list)
    methodologies: List[str] = field(default_factory=list)
    study_type: str = ""
    translational_stage: str = ""
    hypothesis: str = ""
    novelty: str = ""
    clinical_relevance_score: int = 0
    keywords: KeywordTaxonomy = field(default_factory=KeywordTaxonomy)

def extract_fingerprint(manuscript_text: str, api_key: str) -> ManuscriptFingerprint:
    """
    Extracts a detailed semantic fingerprint from the manuscript text using Claude API.
    """
    if not api_key or not manuscript_text.strip():
        # Fallback to empty if no key or text
        return ManuscriptFingerprint()

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are an elite-tier academic publishing intelligence system.
Analyze the following manuscript summary and extract its semantic fingerprint.

MANUSCRIPT SUMMARY:
\"\"\"{manuscript_text}\"\"\"

Provide your analysis strictly as a JSON object with the following schema:
{{
  "primary_domain": ["list", "of", "domains"],
  "primary_targets": ["list", "of", "central biological targets"],
  "secondary_targets": ["list", "of", "contextual targets"],
  "methodologies": ["list", "of", "methodologies"],
  "study_type": "string (in vitro / in vivo / ex vivo / in silico / clinical / review / meta-analysis / case study)",
  "translational_stage": "string (Basic/Fundamental Research / Preclinical / Translational / Clinical / Post-Clinical / Epidemiological / Review)",
  "hypothesis": "Concise one-sentence hypothesis",
  "novelty": "Description of the claimed novelty (e.g. first-in-class finding, etc)",
  "clinical_relevance_score": integer (0 to 10),
  "keywords": {{
    "core": ["tier 1 keywords"],
    "supporting": ["tier 2 keywords"],
    "peripheral": ["tier 3 keywords"]
  }}
}}

Respond ONLY with valid JSON. No markdown formatting, no explanation.
"""
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        
        reply_text = response.content[0].text
        # Clean up in case Claude outputs markdown
        clean_text = re.sub(r'```json\s*', '', reply_text)
        clean_text = re.sub(r'```', '', clean_text).strip()
        
        data = json.loads(clean_text)
        
        taxonomy = KeywordTaxonomy(
            core=data.get("keywords", {}).get("core", []),
            supporting=data.get("keywords", {}).get("supporting", []),
            peripheral=data.get("keywords", {}).get("peripheral", [])
        )
        
        return ManuscriptFingerprint(
            primary_domain=data.get("primary_domain", []),
            primary_targets=data.get("primary_targets", []),
            secondary_targets=data.get("secondary_targets", []),
            methodologies=data.get("methodologies", []),
            study_type=data.get("study_type", ""),
            translational_stage=data.get("translational_stage", ""),
            hypothesis=data.get("hypothesis", ""),
            novelty=data.get("novelty", ""),
            clinical_relevance_score=int(data.get("clinical_relevance_score", 0)),
            keywords=taxonomy
        )

    except Exception as e:
        logger.error(f"Error extracting semantic fingerprint: {e}")
        # Return empty fingerprint on failure
        return ManuscriptFingerprint()
