import io
import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import pypdf
import docx

from app.core.ocr import extract_text_from_image

logger = logging.getLogger(__name__)

# Common legal section patterns
HEADER_PATTERNS = [
    re.compile(r'^(ARTICLE\s+[IVXLCDM0-9]+[\.\:\-]?\s*.*)$', re.IGNORECASE),
    re.compile(r'^(SECTION\s+[0-9]+(\.[0-9]+)*[\.\:\-]?\s*.*)$', re.IGNORECASE),
    re.compile(r'^([0-9]+(?:\.[0-9]+)*[\.\:\-\)]\s*.*)$', re.IGNORECASE),
    re.compile(r'^(RECITALS|WHEREAS|OPERATIVE PROVISIONS|SCHEDULE\s+[A-Z0-9]|EXHIBIT\s+[A-Z0-9]|ANNEX\s+[A-Z0-9])$', re.IGNORECASE),
    re.compile(r'^([A-Za-z\s]{4,40}\s*\:)$')
]

class DocumentSegment:
    def __init__(
        self,
        segment_id: int,
        heading: str,
        section_number: Optional[str],
        text: str,
        char_start: int,
        char_end: int,
        page_number: int = 1
    ):
        self.id = segment_id
        self.heading = heading
        self.section_number = section_number
        self.text = text
        self.char_start = char_start
        self.char_end = char_end
        self.page_number = page_number

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "heading": self.heading,
            "section_number": self.section_number,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "page_number": self.page_number,
            "char_count": len(self.text),
            "word_count": len(self.text.split())
        }

class DocumentParser:
    @staticmethod
    def normalize_text(text: str) -> str:
        """Clean quotes, dashes, spacing and carriage returns."""
        if not text:
            return ""
        # Replace smart quotes & dashes
        text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
        text = text.replace('—', '-').replace('–', '-').replace('…', '...')
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Replace multiple horizontal spaces but preserve single newlines
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    @classmethod
    def parse_pdf(cls, file_bytes: bytes) -> Dict[str, Any]:
        """Extract text and metadata from PDF bytes."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            full_text = ""
            pages_data = []
            char_offset = 0

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_text = cls.normalize_text(page_text)
                if not page_text and i == 0:
                    # Scanned PDF fallback
                    ocr_text = extract_text_from_image(file_bytes)
                    if ocr_text:
                        page_text = ocr_text
                
                start = char_offset
                full_text += page_text + "\n\n"
                char_offset = len(full_text)
                pages_data.append({
                    "page_number": i + 1,
                    "text": page_text,
                    "char_start": start,
                    "char_end": char_offset
                })

            return {
                "format": "pdf",
                "page_count": len(reader.pages),
                "full_text": full_text.strip(),
                "pages": pages_data
            }
        except Exception as e:
            logger.error("Error parsing PDF: %s", str(e))
            raise ValueError(f"Failed to parse PDF document: {str(e)}")

    @classmethod
    def parse_docx(cls, file_bytes: bytes) -> Dict[str, Any]:
        """Extract text and metadata from DOCX bytes."""
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [cls.normalize_text(p.text) for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)
            return {
                "format": "docx",
                "page_count": max(1, len(paragraphs) // 5),
                "full_text": full_text.strip(),
                "pages": [{"page_number": 1, "text": full_text, "char_start": 0, "char_end": len(full_text)}]
            }
        except Exception as e:
            logger.error("Error parsing DOCX: %s", str(e))
            raise ValueError(f"Failed to parse DOCX document: {str(e)}")

    @classmethod
    def parse_text(cls, text_str: str) -> Dict[str, Any]:
        """Parse raw plain text string."""
        normalized = cls.normalize_text(text_str)
        return {
            "format": "text",
            "page_count": max(1, len(normalized) // 3000),
            "full_text": normalized,
            "pages": [{"page_number": 1, "text": normalized, "char_start": 0, "char_end": len(normalized)}]
        }

    @classmethod
    def parse_file(cls, filename: str, content_bytes: bytes) -> Dict[str, Any]:
        """Router to parse file based on extension."""
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            parsed = cls.parse_pdf(content_bytes)
        elif ext in [".docx", ".doc"]:
            parsed = cls.parse_docx(content_bytes)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"]:
            ocr_text = extract_text_from_image(content_bytes)
            parsed = cls.parse_text(ocr_text)
            parsed["format"] = "image_ocr"
        else:
            # Assume plain text / markdown
            try:
                text = content_bytes.decode('utf-8', errors='replace')
            except Exception:
                text = str(content_bytes)
            parsed = cls.parse_text(text)

        # Generate structural segments
        segments = cls.segment_clauses(parsed["full_text"])
        parsed["segments"] = [s.to_dict() for s in segments]
        parsed["total_segments"] = len(segments)
        parsed["filename"] = filename
        return parsed

    @classmethod
    def segment_clauses(cls, full_text: str) -> List[DocumentSegment]:
        """
        Segment contract into logical clauses and numbered articles.
        Preserves offsets and hierarchical numbering.
        """
        if not full_text.strip():
            return []

        raw_blocks = re.split(r'\n{2,}', full_text)

        # If text is single-newline formatted but contains numbered sections/headers, split along headers
        if len(raw_blocks) <= 1 and '\n' in full_text:
            lines = full_text.split('\n')
            assembled_blocks = []
            current_block = []
            for line in lines:
                sline = line.strip()
                is_hdr = any(p.match(sline) for p in HEADER_PATTERNS)
                if is_hdr and current_block:
                    assembled_blocks.append('\n'.join(current_block))
                    current_block = [line]
                else:
                    current_block.append(line)
            if current_block:
                assembled_blocks.append('\n'.join(current_block))
            if len(assembled_blocks) > 1:
                raw_blocks = assembled_blocks

        segments: List[DocumentSegment] = []
        current_offset = 0
        seg_id = 1
        
        current_heading = "General Terms"
        current_section = None

        for block in raw_blocks:
            cleaned_block = block.strip()
            if not cleaned_block:
                continue

            # Calculate actual char start & end in full_text
            block_start = full_text.find(cleaned_block, current_offset)
            if block_start == -1:
                block_start = current_offset
            block_end = block_start + len(cleaned_block)
            current_offset = block_end

            # Check if this block is or starts with a section header
            first_line = cleaned_block.split('\n')[0].strip()
            is_header = False
            for pattern in HEADER_PATTERNS:
                match = pattern.match(first_line)
                if match:
                    is_header = True
                    current_heading = first_line
                    # Extract section number if present
                    sec_match = re.search(r'^(ARTICLE\s+[IVXLCDM0-9]+|SECTION\s+[0-9]+(\.[0-9]+)*|[0-9]+(\.[0-9]+)*)', first_line, re.IGNORECASE)
                    if sec_match:
                        current_section = sec_match.group(0)
                    break

            # Calculate approximate page number (approx 3000 chars per page)
            approx_page = max(1, (block_start // 3000) + 1)

            segment = DocumentSegment(
                segment_id=seg_id,
                heading=current_heading,
                section_number=current_section,
                text=cleaned_block,
                char_start=block_start,
                char_end=block_end,
                page_number=approx_page
            )
            segments.append(segment)
            seg_id += 1

        return segments
