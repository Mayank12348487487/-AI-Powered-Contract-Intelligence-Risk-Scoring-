import re
import logging
from typing import List, Dict, Any, Optional

from app.config import settings
from app.core.clause_classifier import clause_classifier

logger = logging.getLogger(__name__)

# High-Risk Phrase Anomaly Patterns
ANOMALY_PATTERNS = [
    {
        "pattern": re.compile(r'unlimited liability|uncapped liability|liability.*shall be.*unlimited|shall not be subject to any cap', re.IGNORECASE),
        "category": "Unlimited Liability Exposure",
        "severity": "CRITICAL",
        "points": 25,
        "rationale": "Clause explicitly removes liability limits or establishes infinite financial exposure for damages.",
        "recommended_redline": "In no event shall either Party's total aggregate liability exceed the total fees paid in the twelve (12) months preceding the claim."
    },
    {
        "pattern": re.compile(r'sole and (?:absolute|unreviewable) discretion|unreviewable right|at its sole discretion without cause upon \d+\s*(?:hours|days)', re.IGNORECASE),
        "category": "One-Sided Discretionary Powers",
        "severity": "HIGH",
        "points": 12,
        "rationale": "Grants counterparty unilateral unreviewable authority to terminate, revoke licenses, or alter terms.",
        "recommended_redline": "Any exercise of termination or modification rights shall require reasonable cause and mutual written agreement with at least 30 days prior notice."
    },
    {
        "pattern": re.compile(r'assigns.*all right.*background source code|transfers.*pre-existing.*intellectual property|work made for hire.*background', re.IGNORECASE),
        "category": "Pre-Existing IP Forfeiture",
        "severity": "CRITICAL",
        "points": 22,
        "rationale": "Transfers background, pre-existing, or foundational intellectual property to the counterparty.",
        "recommended_redline": "Each Party retains exclusive ownership of its pre-existing Intellectual Property, background technology, and independent developments."
    },
    {
        "pattern": re.compile(r'regardless of.*(?:contributory\s+)?negligence|indemnif.*regardless of fault|solely indemnifies', re.IGNORECASE),
        "category": "Broad Unilateral Indemnification",
        "severity": "CRITICAL",
        "points": 18,
        "rationale": "Requires one party to indemnify counterparty even in instances of counterparty's own negligence or fault.",
        "recommended_redline": "Each Party shall defend and indemnify the other Party only for claims arising directly from its own gross negligence, willful misconduct, or IP infringement."
    },
    {
        "pattern": re.compile(r'non-compete.*(?:worldwide|anywhere worldwide|five\s*\(5\)\s*years|\d+\s*years)', re.IGNORECASE),
        "category": "Overbroad Non-Compete",
        "severity": "HIGH",
        "points": 16,
        "rationale": "Imposes overly restrictive non-compete covenants spanning multi-year durations or global geographic scope.",
        "recommended_redline": "Neither Party shall be restricted from conducting general business, provided confidential information is not disclosed."
    },
    {
        "pattern": re.compile(r'liquidated damages equal to \d+%|penalty of \d+%|200% of the shortfall', re.IGNORECASE),
        "category": "Harsh Liquidated Damages / Penalties",
        "severity": "HIGH",
        "points": 15,
        "rationale": "Establishes punitive liquidated damage multiples that may exceed actual financial damages.",
        "recommended_redline": "Liquidated damages, if any, shall represent genuine pre-estimates of loss and be strictly capped at 10% of the affected order value."
    },
    {
        "pattern": re.compile(r'inspect.*premises.*at any time without prior notice|unannounced.*audit', re.IGNORECASE),
        "category": "Unannounced Intrusive Audit Rights",
        "severity": "MEDIUM",
        "points": 8,
        "rationale": "Permits unannounced inspections of facilities and source code repositories without reasonable notice.",
        "recommended_redline": "Audits shall be conducted not more than once per year, during normal business hours, upon at least thirty (30) days' prior written notice."
    },
    {
        "pattern": re.compile(r'no event of force majeure.*shall excuse|no force majeure', re.IGNORECASE),
        "category": "Disallowance of Force Majeure Relief",
        "severity": "HIGH",
        "points": 14,
        "rationale": "Explicitly refuses relief for catastrophic events, acts of God, war, or natural disasters.",
        "recommended_redline": "Standard Force Majeure clause providing mutual relief for events beyond reasonable control."
    }
]

class RiskScoringEngine:
    def __init__(self):
        pass

    def evaluate_contract_risk(
        self,
        full_text: str,
        enriched_segments: List[Dict[str, Any]],
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute comprehensive multi-factor risk assessment.
        Returns composite score (0-100), risk tier, itemized triggers, and mitigation checklist.
        """
        category_summary = clause_classifier.get_detected_categories_summary(enriched_segments)
        detected_cat_ids = {c["category_id"] for c in category_summary["detected_categories"]}

        # 1. Evaluate Pillar 1: Missing Critical Protections (0-35 max)
        missing_penalties = 0
        missing_details = []

        if "cap_on_liability" not in detected_cat_ids and "unlimited_liability" not in detected_cat_ids:
            missing_penalties += 16
            missing_details.append({
                "item": "Missing Limitation of Liability Clause",
                "severity": "HIGH",
                "impact": 16,
                "recommendation": "Insert standard 12-month trailing fee liability cap."
            })

        if "force_majeure" not in detected_cat_ids:
            missing_penalties += 10
            missing_details.append({
                "item": "Missing Force Majeure Clause",
                "severity": "MEDIUM",
                "impact": 10,
                "recommendation": "Add mutual Force Majeure provision excusing performance for unforeseen disasters."
            })

        if "mutual_indemnification" not in detected_cat_ids and "unilateral_indemnification" not in detected_cat_ids:
            missing_penalties += 9
            missing_details.append({
                "item": "Missing Indemnification Structure",
                "severity": "MEDIUM",
                "impact": 9,
                "recommendation": "Incorporate mutual indemnity for third-party IP infringement and gross negligence."
            })

        if "governing_law" not in detected_cat_ids and not entities.get("governing_law"):
            missing_penalties += 8
            missing_details.append({
                "item": "Undefined Governing Law & Forum",
                "severity": "MEDIUM",
                "impact": 8,
                "recommendation": "Specify clear governing jurisdiction (e.g. Delaware / New York)."
            })

        pillar_1_score = min(35, missing_penalties)

        # 2. Evaluate Pillar 2: High-Risk Anomalies and Unfavorable Terms (0-35 max)
        anomalies_detected = []
        unfavorable_penalties = 0

        for seg in enriched_segments:
            seg_text = seg["text"]
            for anomaly_rule in ANOMALY_PATTERNS:
                if anomaly_rule["pattern"].search(seg_text):
                    unfavorable_penalties += anomaly_rule["points"]
                    anomalies_detected.append({
                        "category": anomaly_rule["category"],
                        "severity": anomaly_rule["severity"],
                        "points": anomaly_rule["points"],
                        "segment_id": seg["id"],
                        "section_heading": seg["heading"],
                        "flagged_text": seg_text,
                        "rationale": anomaly_rule["rationale"],
                        "recommended_redline": anomaly_rule["recommended_redline"]
                    })

        # Check for unilateral indemnification category match
        if "unilateral_indemnification" in detected_cat_ids:
            unfavorable_penalties += 15
            if not any(a["category"] == "Broad Unilateral Indemnification" for a in anomalies_detected):
                anomalies_detected.append({
                    "category": "One-Sided Unilateral Indemnification",
                    "severity": "CRITICAL",
                    "points": 15,
                    "section_heading": "Indemnification",
                    "flagged_text": "One-sided indemnity obligation identified in agreement.",
                    "rationale": "Only one party indemnifies the other with no reciprocal protections.",
                    "recommended_redline": "Make indemnification obligations reciprocal."
                })

        pillar_2_score = min(35, unfavorable_penalties)

        # 3. Evaluate Pillar 3: Operational & Lock-in Risk (0-20 max)
        operational_penalties = 0
        operational_flags = []

        # Check notice periods
        for np in entities.get("notice_periods", []):
            duration_text = np["duration"].lower()
            if "hours" in duration_text or "24 hours" in duration_text or "5 days" in duration_text:
                operational_penalties += 8
                operational_flags.append(f"Excessively short notice window ({np['duration']}) for {np['purpose']}")
            elif "365 days" in duration_text or "1 year" in duration_text:
                operational_penalties += 6
                operational_flags.append(f"Burden of extremely long non-renewal notice period ({np['duration']})")

        if "minimum_commitment" in detected_cat_ids:
            operational_penalties += 7
            operational_flags.append("Strict Take-or-pay / minimum volume commitment active.")

        pillar_3_score = min(20, operational_penalties)

        # 4. Evaluate Pillar 4: Ambiguity and Boilerplate Deviations (0-10 max)
        ambiguity_penalties = 0
        ambiguous_matches = re.findall(r'\b(?:at\s+its\s+sole\s+option|in\s+its\s+absolute\s+discretion|without\s+limitation|as\s+determined\s+by)\b', full_text, re.IGNORECASE)
        ambiguity_penalties = min(10, len(ambiguous_matches) * 2)
        pillar_4_score = ambiguity_penalties

        # Calculate Final Composite Score (0-100)
        total_risk_score = round(pillar_1_score + pillar_2_score + pillar_3_score + pillar_4_score)
        total_risk_score = max(0, min(100, total_risk_score))

        # Risk Classification Tier
        if total_risk_score <= settings.RISK_LOW_MAX:
            risk_tier = "LOW"
            risk_color = "#10B981" # Green
            tier_description = "Standard commercial terms with balanced mutual protections and minimal legal risk exposure."
        elif total_risk_score <= settings.RISK_MEDIUM_MAX:
            risk_tier = "MEDIUM"
            risk_color = "#F59E0B" # Amber
            tier_description = "Moderate risk. Contains some operational obligations or missing boilerplate that should be negotiated."
        elif total_risk_score <= settings.RISK_HIGH_MAX:
            risk_tier = "HIGH"
            risk_color = "#F97316" # Orange
            tier_description = "High business risk. Contains aggressive covenants, one-sided clauses, or significant liability exposure."
        else:
            risk_tier = "CRITICAL"
            risk_color = "#EF4444" # Red
            tier_description = "Critical risk flags detected. Uncapped liabilities, total IP forfeiture, or severe unilateral restrictions present."

        # Executive Summary Generation
        exec_summary = self._generate_executive_summary(
            risk_tier, total_risk_score, anomalies_detected, missing_details, entities
        )

        return {
            "composite_score": total_risk_score,
            "risk_tier": risk_tier,
            "risk_color": risk_color,
            "tier_description": tier_description,
            "pillar_breakdown": {
                "missing_protections": {
                    "score": pillar_1_score,
                    "max": 35,
                    "issues": missing_details
                },
                "unfavorable_terms_and_anomalies": {
                    "score": pillar_2_score,
                    "max": 35,
                    "count": len(anomalies_detected)
                },
                "operational_and_lockin_risk": {
                    "score": pillar_3_score,
                    "max": 20,
                    "flags": operational_flags
                },
                "ambiguity_risk": {
                    "score": pillar_4_score,
                    "max": 10,
                    "instances_count": len(ambiguous_matches)
                }
            },
            "anomalies": anomalies_detected,
            "missing_clauses": missing_details,
            "executive_summary": exec_summary,
            "actionable_recommendations": self._generate_recommendations(anomalies_detected, missing_details)
        }

    def _generate_executive_summary(
        self,
        risk_tier: str,
        score: int,
        anomalies: List[Dict[str, Any]],
        missing: List[Dict[str, Any]],
        entities: Dict[str, Any]
    ) -> str:
        parties_str = " and ".join([p["name"] for p in entities.get("parties", [])]) if entities.get("parties") else "the contracting parties"
        eff_date = entities.get("effective_date", {}).get("value", "an unspecified date") if entities.get("effective_date") else "an unspecified date"
        law = entities.get("governing_law", {}).get("jurisdiction", "Unspecified") if entities.get("governing_law") else "Unspecified"

        summary = (
            f"This contract between {parties_str} (Effective: {eff_date}, Jurisdiction: {law}) "
            f"has been evaluated with an overall Risk Score of {score}/100 ({risk_tier} RISK). "
        )

        if risk_tier in ["HIGH", "CRITICAL"]:
            top_flags = [a["category"] for a in anomalies[:3]]
            summary += f"Major compliance vulnerabilities identified include: {', '.join(top_flags)}. "
            summary += "Immediate legal counsel intervention and contract redlining are strongly recommended prior to signature."
        elif risk_tier == "MEDIUM":
            summary += "The contract is generally serviceable but contains minor one-sided terms or missing protective covenants that warrant standard redlining."
        else:
            summary += "The contract adheres closely to standard commercial contracting norms with balanced reciprocal protections and standard liability caps."

        return summary

    def _generate_recommendations(
        self,
        anomalies: List[Dict[str, Any]],
        missing: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        recs = []
        for m in missing:
            recs.append({
                "action": f"Draft & Insert: {m['item']}",
                "priority": "High" if m["severity"] in ["HIGH", "CRITICAL"] else "Medium",
                "guidance": m["recommendation"]
            })
        for a in anomalies:
            recs.append({
                "action": f"Redline: {a['category']}",
                "priority": "High" if a["severity"] in ["HIGH", "CRITICAL"] else "Medium",
                "guidance": a["recommended_redline"]
            })
        return recs[:8]

# Global singleton
risk_engine = RiskScoringEngine()
