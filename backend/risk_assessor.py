import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any

from .semantic_analyzer import ManuscriptFingerprint

logger = logging.getLogger(__name__)

@dataclass
class RiskAssessment:
    journal_title: str
    scope_edge_risk: str  # "Core Fit", "Peripheral Fit", "Edge Case"
    scope_edge_rationale: str
    prestige_vs_speed: str
    competing_submissions: str
    special_issues: str
    tier: int  # 1, 2, or 3
    recommendation: str

def assess_risks(fingerprint: ManuscriptFingerprint, scored_journals: List[Dict[str, Any]], api_key: str) -> List[RiskAssessment]:
    """
    Performs Strategic Submission Risk Assessment for the top journals using Claude.
    """
    if not api_key or not scored_journals:
        return [
            RiskAssessment(
                journal_title=j["journal_title"],
                scope_edge_risk="Core Fit" if j.get("cas", 0) > 80 else "Peripheral Fit",
                scope_edge_rationale="Automatically estimated based on CAS.",
                prestige_vs_speed="High IF typically implies longer review.",
                competing_submissions="Unknown",
                special_issues="None identified",
                tier=1 if j.get("cas", 0) > 80 else (2 if j.get("cas", 0) > 65 else 3),
                recommendation="Consider submitting based on CAS."
            ) for j in scored_journals
        ]

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        journals_info = []
        for i, j in enumerate(scored_journals):
            journals_info.append(f"{i+1}. {j['journal_title']} | CAS: {j.get('cas', 0)}% | IF: {j.get('impact_factor', 'N/A')} | Scope: {j.get('scope_text', '')[:200]}...")

        journals_text = "\n".join(journals_info)

        fp_text = f"""
Domain: {fingerprint.primary_domain}
Targets: {fingerprint.primary_targets}
Methodologies: {fingerprint.methodologies}
Translational Stage: {fingerprint.translational_stage}
"""

        prompt = f"""You are an elite academic publishing editor. Assess the submission risks for the following manuscript against these top candidate journals.

MANUSCRIPT:
{fp_text}

CANDIDATE JOURNALS:
{journals_text}

For each journal, provide a risk assessment strictly in JSON array format, where each object has:
- "journal_title": string
- "scope_edge_risk": "Core Fit" or "Peripheral Fit" or "Edge Case"
- "scope_edge_rationale": 1 sentence
- "prestige_vs_speed": 1 short phrase characterization
- "competing_submissions": "Unknown" or brief string
- "special_issues": "None identified" or brief string
- "tier": 1, 2, or 3
- "recommendation": 1-2 strategic sentences

Respond ONLY with valid JSON.
"""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        reply_text = response.content[0].text
        import re
        clean_text = re.sub(r'```json\s*', '', reply_text)
        clean_text = re.sub(r'```', '', clean_text).strip()
        data = json.loads(clean_text)

        assessments = []
        for item in data:
            assessments.append(RiskAssessment(
                journal_title=item.get("journal_title", ""),
                scope_edge_risk=item.get("scope_edge_risk", ""),
                scope_edge_rationale=item.get("scope_edge_rationale", ""),
                prestige_vs_speed=item.get("prestige_vs_speed", ""),
                competing_submissions=item.get("competing_submissions", ""),
                special_issues=item.get("special_issues", ""),
                tier=int(item.get("tier", 2)),
                recommendation=item.get("recommendation", "")
            ))
        return assessments

    except Exception as e:
        logger.error(f"Error assessing risks: {e}")
        return []
