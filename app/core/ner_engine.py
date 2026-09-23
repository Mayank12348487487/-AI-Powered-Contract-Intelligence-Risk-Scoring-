import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# US States & International Jurisdictions
JURISDICTIONS = [
    "Delaware", "New York", "California", "Texas", "Massachusetts", "Illinois",
    "Washington", "Florida", "Ohio", "Pennsylvania", "New Jersey", "Georgia",
    "North Carolina", "Virginia", "Colorado", "Nevada", "England and Wales",
    "United Kingdom", "Switzerland", "Canton of Zurich", "Germany", "Singapore",
    "Hong Kong", "Japan", "India", "Australia", "New South Wales", "Victoria",
    "France", "Canada", "Ontario", "British Columbia", "Ireland", "Scotland",
    "Luxembourg", "Netherlands", "Sweden", "Cayman Islands", "Bermuda", "Dubai",
    "United Arab Emirates", "New Zealand", "Norway", "Denmark", "Finland"
]

PARTY_ROLES = [
    "Provider", "Customer", "Client", "Vendor", "Supplier", "Buyer", "Seller",
    "Licensor", "Licensee", "Disclosing Party", "Receiving Party", "Subscriber",
    "Company", "Contractor", "Consultant", "Partner", "Borrower", "Lender",
    "Distributor", "Reseller", "Author", "Publisher"
]

class LegalNER:
    def __init__(self):
        self._compile_regexes()

    def _compile_regexes(self):
        # Dates: October 15, 2025 | 15th day of October, 2025 | 15 October 2025 | 2025-10-15 | 10/15/2025 | 15/10/2025
        self.date_regex = re.compile(
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b',
            re.IGNORECASE
        )
        
        # Monetary Values: $120,000 USD | $1,500,000 | 500,000 USD | 2,500,000 EUR | €500,000 | £85,000 | ¥10,000,000 | ₹5,00,000 | CHF 250,000
        self.money_regex = re.compile(
            r'(?:\$|USD|EUR|GBP|€|£|AUD|CAD|INR|SGD|CHF|JPY|¥|₹|AED|NZD|SEK)\s*[\d,]+(?:\.\d{2})?(?:\s*(?:USD|EUR|GBP|AUD|CAD|INR|SGD|CHF|JPY|dollars|euros|pounds|million|billion|thousand|k))?|[\d,]+(?:\.\d{2})?\s*(?:USD|dollars|EUR|euros|GBP|pounds|AUD|CAD|INR|rupees|SGD|CHF|JPY|yen)',
            re.IGNORECASE
        )
        
        # Termination / Notice Periods: 30 days | sixty (60) days | 24 hours | 12 months | 5 business days
        self.notice_period_regex = re.compile(
            r'\b(?:one|two|three|five|seven|ten|fourteen|fifteen|twenty|thirty|forty-five|sixty|ninety|one hundred|one hundred and twenty|one hundred and eighty|three hundred and sixty-five|\d+)\s*(?:\(\d+\))?\s*(?:business\s+days|calendar\s+days|days|hours|weeks|months|years)\b',
            re.IGNORECASE
        )
        
        # Payment terms: Net 15, Net 30, Net 45, Net 60, Net 90
        self.payment_terms_regex = re.compile(
            r'\b(?:Net\s*(?:15|30|45|60|90|120)|within\s+\d+\s+(?:business\s+)?days\s+of\s+(?:invoice|receipt)|upon\s+receipt|quarterly|monthly|annually|in\s+advance)\b',
            re.IGNORECASE
        )

        # Party definitions: [Company Name, Inc.], a [Delaware corporation] ("Provider")
        self.party_bracket_regex = re.compile(
            r'([A-Z][A-Za-z0-9\s\,\.\&\-]+?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited|Pty\s+Ltd|PLC|LLP|AG|GmbH|Co\.|S\.A\.|B\.V\.|Pte\.\s*Ltd\.|S\.r\.l\.|K\.K\.))(?:\s*,\s*a\s+[A-Za-z\s]+(?:corporation|company|entity|partnership))?\s*(?:\([\"“\']([A-Za-z\s]+)[\"”\']\))?',
            re.IGNORECASE
        )

    def extract_entities(self, full_text: str) -> Dict[str, Any]:
        """
        Extract structured legal entities from contract text.
        """
        entities = {
            "parties": self.extract_parties(full_text),
            "effective_date": self.extract_effective_date(full_text),
            "expiration_date": self.extract_expiration_date(full_text),
            "agreement_date": self.extract_agreement_date(full_text),
            "governing_law": self.extract_governing_law(full_text),
            "monetary_values": self.extract_monetary_values(full_text),
            "notice_periods": self.extract_notice_periods(full_text),
            "payment_terms": self.extract_payment_terms(full_text),
            "all_extracted_count": 0
        }

        total_count = (
            len(entities["parties"]) +
            (1 if entities["effective_date"] else 0) +
            (1 if entities["expiration_date"] else 0) +
            (1 if entities["governing_law"] else 0) +
            len(entities["monetary_values"]) +
            len(entities["notice_periods"]) +
            len(entities["payment_terms"])
        )
        entities["all_extracted_count"] = total_count
        return entities

    def extract_parties(self, text: str) -> List[Dict[str, Any]]:
        """Extract contracting parties, roles, and corporate types from preamble/recitals."""
        preamble = text[:3000] # Usually in the first 3000 chars
        parties = []
        seen_names = set()

        # Look for "by and between ... and ..."
        matches = self.party_bracket_regex.finditer(preamble)
        for m in matches:
            raw_name = m.group(1).strip()
            # Clean up trailing punctuation
            raw_name = re.sub(r'[\,\.\s]+$', '', raw_name)
            role = m.group(2) if m.group(2) else None
            
            if len(raw_name) > 3 and raw_name.lower() not in seen_names:
                seen_names.add(raw_name.lower())
                
                # Check for role in nearby context if not captured
                if not role:
                    context = preamble[max(0, m.start() - 30):min(len(preamble), m.end() + 50)]
                    for r in PARTY_ROLES:
                        if re.search(rf'[\"“\']{r}[\"”\']', context, re.IGNORECASE):
                            role = r
                            break

                parties.append({
                    "name": raw_name,
                    "role": role or "Contracting Party",
                    "char_start": m.start(),
                    "char_end": m.end(),
                    "confidence": 0.92 if role else 0.85
                })

        return parties[:4] # Limit to principal parties

    def extract_effective_date(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract Effective Date."""
        match = re.search(r'(?:effective\s+as\s+of|effective\s+date\s*(?:is|shall\s+be)?\s*[\:\-]?\s*)([A-Za-z0-9\s\,\-]+?\d{4})', text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            date_match = self.date_regex.search(date_str)
            if date_match:
                return {
                    "value": date_match.group(0),
                    "context": match.group(0),
                    "confidence": 0.95
                }
        
        # Fallback to first date found in preamble
        dates = self.date_regex.findall(text[:2000])
        if dates:
            return {"value": dates[0], "context": "Preamble Date", "confidence": 0.75}
        return None

    def extract_expiration_date(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract Expiration Date or fixed Term end date."""
        match = re.search(r'(?:expir(?:e|es|ing|ation)|terminat(?:e|es|ing|ion)|end(?:s|ing)?)\s+(?:date\s+)?(?:on|is|shall\s+be)?\s*[\:\-]?\s*([A-Za-z0-9\s\,\-]+?\d{4})', text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            date_match = self.date_regex.search(date_str)
            if date_match:
                return {
                    "value": date_match.group(0),
                    "context": match.group(0),
                    "confidence": 0.92
                }
        return None

    def extract_agreement_date(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract Agreement Execution Date."""
        match = re.search(r'(?:dated\s+as\s+of|entered\s+into\s+on\s+this)\s+([A-Za-z0-9\s\,\-]+?\d{4})', text[:2000], re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            date_match = self.date_regex.search(date_str)
            if date_match:
                return {
                    "value": date_match.group(0),
                    "confidence": 0.90
                }
        return None

    def extract_governing_law(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract governing jurisdiction and applicable law."""
        # Find governing law paragraph or sentence
        law_match = re.search(r'(?:governed\s+by(?:\s+the\s+laws\s+of)?|laws\s+of\s+(?:the\s+state\s+of|the\s+country\s+of)?|jurisdiction\s+of|exclusive\s+jurisdiction\s+of)\s+([A-Za-z\s\,\.]+)', text, re.IGNORECASE)
        found_jurisdiction = None
        
        # 1. Search inside explicit governing law clause context first
        if law_match:
            clause_context = law_match.group(0)
            for state in JURISDICTIONS:
                if re.search(rf'\b{re.escape(state)}\b', clause_context, re.IGNORECASE):
                    found_jurisdiction = state
                    break

        # 2. Fallback to searching across text
        if not found_jurisdiction:
            for state in JURISDICTIONS:
                if re.search(rf'\b{re.escape(state)}\b', text, re.IGNORECASE):
                    found_jurisdiction = state
                    break

        if found_jurisdiction:
            return {
                "jurisdiction": found_jurisdiction,
                "confidence": 0.95,
                "clause_snippet": law_match.group(0).strip() if law_match else f"Laws of {found_jurisdiction}"
            }
        return None

    def extract_monetary_values(self, text: str) -> List[Dict[str, Any]]:
        """Extract monetary caps, subscription fees, and liability amounts."""
        values = []
        seen = set()
        for m in self.money_regex.finditer(text):
            val = m.group(0).strip()
            if val not in seen:
                seen.add(val)
                # Look at context around amount
                start_idx = max(0, m.start() - 40)
                end_idx = min(len(text), m.end() + 40)
                snippet = text[start_idx:end_idx].replace('\n', ' ')
                
                category = "Fee / Payment"
                if re.search(r'liability|cap|damages|aggregate', snippet, re.IGNORECASE):
                    category = "Liability Cap"
                elif re.search(r'minimum|guarantee|take-or-pay', snippet, re.IGNORECASE):
                    category = "Minimum Commitment"
                elif re.search(r'penalty|liquidated', snippet, re.IGNORECASE):
                    category = "Liquidated Penalty"

                values.append({
                    "amount": val,
                    "type": category,
                    "context": snippet.strip(),
                    "char_start": m.start(),
                    "char_end": m.end()
                })
        return values[:10]

    def extract_notice_periods(self, text: str) -> List[Dict[str, Any]]:
        """Extract notice periods (for termination, non-renewal, cure, audit)."""
        periods = []
        seen = set()
        for m in self.notice_period_regex.finditer(text):
            val = m.group(0).strip()
            if val not in seen and len(val) > 2:
                seen.add(val)
                start_idx = max(0, m.start() - 40)
                end_idx = min(len(text), m.end() + 40)
                snippet = text[start_idx:end_idx].replace('\n', ' ')
                
                purpose = "General Notice"
                if re.search(r'renewal|non-renewal|renew', snippet, re.IGNORECASE):
                    purpose = "Renewal / Non-Renewal Notice"
                elif re.search(r'terminate|convenience|without\s+cause', snippet, re.IGNORECASE):
                    purpose = "Termination for Convenience"
                elif re.search(r'cure|breach|default', snippet, re.IGNORECASE):
                    purpose = "Cure Period"
                elif re.search(r'audit|inspect', snippet, re.IGNORECASE):
                    purpose = "Audit Notice"

                periods.append({
                    "duration": val,
                    "purpose": purpose,
                    "context": snippet.strip(),
                    "char_start": m.start(),
                    "char_end": m.end()
                })
        return periods[:8]

    def extract_payment_terms(self, text: str) -> List[str]:
        """Extract payment schedule terms."""
        terms = set()
        for m in self.payment_terms_regex.finditer(text):
            terms.add(m.group(0).strip())
        return list(terms)[:5]

# Global singleton
ner_engine = LegalNER()
