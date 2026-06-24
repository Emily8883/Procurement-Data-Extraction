import re
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

import pdfplumber

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    OCR_AVAILABLE = False

# Configure logging for document context extraction
logger = logging.getLogger(__name__)

# Supplier name patterns (strict)
SUPPLIER_PATTERNS = [
    r'\b(?:SUPPLIED?\s+BY|SUPPLIER|VENDOR|FROM)\b\s*[:\-]?\s*([A-Z][A-Z0-9\s&.,\-]{3,100})',
    r'\b(?:COMPANY|FIRM|FIRM NAME)\b\s*[:\-]?\s*([A-Z][A-Z0-9\s&.,\-]{3,100})',
]

# Strict invoice/PO patterns - avoid partial matches
INVOICE_PATTERNS = [
    r'\bINV[-_]?([0-9A-Z]{4,15})\b',        # INV-XXXX
    r'\bPO[-_]?([0-9A-Z]{4,15})\b',         # PO-XXXX
    r'\bOC[-_]?([0-9A-Z]{4,15})\b',         # OC-XXXX (order code)
    r'\bINVOICE\s*(?:NO\.?|NUMBER)[-_\s]?([0-9A-Z]{4,15})\b',
    r'\bPURCHASE\s*ORDER\s*(?:NO\.?|NUMBER)[-_\s]?([0-9A-Z]{4,15})\b',
    r'\bORDER\s*NO\.?[-_\s]?([0-9A-Z]{4,15})\b',
    r'\bREF(?:ERENCE)?\s*(?:NO\.?|NUMBER)[-_\s]?([0-9A-Z]{4,15})\b',
]

# Currency symbols
CURRENCY_SYMBOLS = {
    '$': 'USD',
    '£': 'GBP',
    '€': 'EUR',
    '¥': 'JPY',
    'S/': 'PEN'  # Peruvian Nuevo Sol
}

# Currency codes (expanded)
CURRENCY_CODES = [
    'USD', 'GBP', 'EUR', 'CAD', 'AUD', 'MXN', 'COP', 'ARS',  # Original
    'PEN', 'BRL', 'INR', 'CNY', 'JPY', 'CHF', 'SEK', 'NOK',  # Additional
    'DKK', 'NZD', 'ZAR', 'HKD', 'SGD', 'THB', 'MYR', 'PHP', 'IDR', 'VND'
]

# Document type patterns
DOCUMENT_TYPE_PATTERNS = {
    'invoice': [r'\binvoice\b', r'\bamount due\b', r'\btotal due\b', r'\bamount payable\b'],
    'po': [r'\bpurchase order\b', r'\bpo number\b', r'\bpo\b', r'\border no\.?\b'],
    'tender': [r'\btender\b', r'\bbid\b', r'\bproposal\b', r'\brfq\b']
}


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ''
    return ' '.join(str(value).strip().split())


@dataclass
class DocumentContext:
    supplier_name: str
    currency: str
    invoice_or_po_number: str
    document_type: str
    is_scanned: bool
    document_text: str
    header_text: str


def _ocr_page_text(page) -> str:
    if not OCR_AVAILABLE or pytesseract is None:
        return page.extract_text() or ''
    try:
        image = page.to_image(resolution=300)
        pil_image = getattr(image, 'original', None)
        if pil_image is None:
            pil_image = image
        return pytesseract.image_to_string(pil_image) or ''
    except Exception:
        return page.extract_text() or ''


def _extract_page_text(page, ocr: bool = False) -> str:
    if ocr:
        return _ocr_page_text(page)
    return page.extract_text() or ''


BOILERPLATE_PHRASES = [
    'TERMINO DE REFERENCIA',
    'TERMS OF REFERENCE',
    'STATEMENT OF WORK',
    'REQUEST FOR QUOTATION',
    'RFP',
    'RFQ',
    'INSTRUCTIONS TO BIDDERS',
    'TERMS AND CONDITIONS',
    'SCOPE OF WORK'
]


def _is_title_phrase(line: str) -> bool:
    upper_line = line.upper()
    if any(phrase in upper_line for phrase in BOILERPLATE_PHRASES):
        return True
    title_keywords = ['TERMS', 'REFERENCIA', 'SCOPE', 'REQUEST', 'BID', 'TENDER', 'STATEMENT', 'INSTRUCTIONS', 'CONDITIONS']
    if line.isupper() and len(line.split()) <= 6 and any(keyword in upper_line for keyword in title_keywords):
        return True
    return False


def extract_header_text_block(page, num_lines: int = 8) -> str:
    """Extract the top N lines of page text while removing boilerplate phrases."""
    text = page.extract_text() or ''
    if not text and OCR_AVAILABLE:
        text = _ocr_page_text(page)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    top_lines = lines[:num_lines]
    filtered = [line for line in top_lines if not _is_title_phrase(line)]

    # Prefer all-caps multi-word organization-style lines
    org_lines = [line for line in filtered if line.isupper() and len(line.split()) >= 2]
    if org_lines:
        return ' '.join(org_lines)

    if filtered:
        return ' '.join(filtered)
    return ' '.join(top_lines)


def _extract_header_text(page) -> str:
    try:
        words = page.extract_words()
        if not words:
            raise ValueError
        top_limit = page.height * 0.20
        header_words = [w['text'] for w in words if w.get('top', 0) <= top_limit]
        if header_words:
            return ' '.join(header_words)
    except Exception:
        pass
    text = page.extract_text() or ''
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return ' '.join(lines[:min(10, len(lines))])


def _find_supplier_name(text: str, debug: bool = False) -> str:
    """Extract supplier name from document text.
    
    Strategy:
    1. Check explicit patterns (SUPPLIER:, VENDOR:, etc.)
    2. Extract from header (top 20% of first page)
    3. Look for uppercase org names in first 10 lines
    
    Args:
        text: Document text to search
        debug: Enable debug logging
    
    Returns:
        Supplier name or empty string
    """
    # Try explicit patterns first (highest confidence)
    for pattern in SUPPLIER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            supplier = _normalize_text(match.group(1))
            if len(supplier) >= 4:
                logger.debug(f"Found supplier via pattern: {supplier}")
                return supplier
    
    # Try uppercase organization names from first 10 lines, avoiding title phrases when possible
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fallback_title = ''
    for line in lines[:10]:
        if line.isupper() and len(line) >= 4 and 3 <= len(line.split()) <= 10:
            if _is_title_phrase(line):
                fallback_title = fallback_title or line
                continue
            normalized = _normalize_text(line)
            logger.debug(f"Found supplier via uppercase name: {normalized}")
            return normalized

    if fallback_title:
        normalized = _normalize_text(fallback_title)
        logger.debug(f"Falling back to title-style supplier candidate: {normalized}")
        return normalized

    logger.debug("No supplier name found in document")
    return ''


def _find_currency(text: str, debug: bool = False) -> str:
    """Extract currency from document text.
    
    Strategy:
    1. Check for currency symbols ($, £, €, ¥, S/)
    2. Check for currency codes (USD, GBP, EUR, etc.)
    
    Args:
        text: Document text to search
        debug: Enable debug logging
    
    Returns:
        Currency symbol or code
    """
    # Check for currency symbols
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            logger.debug(f"Found currency symbol: {symbol} ({code})")
            return code
    
    # Check for currency codes (word boundaries)
    upper_text = text.upper()
    for code in CURRENCY_CODES:
        if re.search(rf'\b{code}\b', upper_text):
            logger.debug(f"Found currency code: {code}")
            return code
    
    logger.debug("No currency found in document")
    return ''


def _find_invoice_number(text: str, debug: bool = False) -> str:
    """Extract invoice or PO number from document.
    
    Strategy:
    1. Use strict patterns only: INV-XXXX, PO-XXXX, OC-XXXX, etc.
    2. Minimum 4 characters to avoid single-letter matches
    3. Only matches with clear prefix (avoid partial matches)
    
    Args:
        text: Document text to search
        debug: Enable debug logging
    
    Returns:
        Invoice/PO number or empty string
    """
    upper_text = text.upper()
    
    # Try strict patterns in order of preference
    for pattern in INVOICE_PATTERNS:
        matches = re.finditer(pattern, upper_text, re.IGNORECASE)
        for match in matches:
            # Extract the number part (group 1 if capture group exists, else whole match)
            if match.groups():
                candidate = _normalize_text(match.group(1))
            else:
                candidate = _normalize_text(match.group(0))
            
            # Validate: must be at least 4 characters, not just a letter
            if len(candidate) >= 4 and not re.match(r'^[A-Z]$', candidate):
                logger.debug(f"Found invoice/PO number via pattern: {candidate}")
                return candidate
    
    logger.debug("No invoice/PO number found with strict patterns")
    return ''


def _infer_document_type(text: str, debug: bool = False) -> str:
    """Infer document type (invoice/po/tender/unknown).
    
    Args:
        text: Document text to search
        debug: Enable debug logging
    
    Returns:
        Document type: 'invoice', 'po', 'tender', or 'unknown'
    """
    lower_text = text.lower()
    
    for doc_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lower_text):
                logger.debug(f"Detected document type as '{doc_type}' via pattern: {pattern}")
                return doc_type
    
    logger.debug("Document type undetermined, defaulting to 'unknown'")
    return 'unknown'


def build_document_context(pdf_path: str, debug: bool = False) -> Dict[str, Any]:
    """Extract document-level metadata from PDF.
    
    Document-level aggregation only - no row-level logic.
    
    Extracts:
    - supplier_name: From header or uppercase org names in first 10 lines
    - currency: From symbols or codes detected anywhere in document
    - invoice_or_po_number: Strict pattern matching (INV-, PO-, OC-, etc.)
    - document_type: Classification as invoice/po/tender/unknown
    
    Args:
        pdf_path: Path to PDF file
        debug: Enable debug logging
    
    Returns:
        Dict with extracted metadata and context
    """
    pdf_path = Path(pdf_path)
    
    if debug:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    
    logger.info(f"Building document context from: {pdf_path.name}")
    
    collected_texts: List[str] = []
    header_texts: List[str] = []
    is_scanned = False
    
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ''
                
                # Detect scanned pages (low text density)
                if len(text.strip()) < 80 or len(text.split()) < 30:
                    is_scanned = True
                    logger.debug(f"Page {page_num} detected as scanned (low text density)")
                    text = _ocr_page_text(page)
                
                collected_texts.append(text)
                header_texts.append(_extract_header_text(page))
    
    except Exception as e:
        logger.warning(f"Error opening PDF {pdf_path.name}: {e}")
        return {
            'supplier_name': '',
            'currency': '',
            'invoice_or_po_number': '',
            'document_type': 'unknown',
            'is_scanned': False,
            'document_text': '',
            'header_text': ''
        }
    
    # Aggregate all text
    document_text = ' '.join([t for t in collected_texts if t])
    header_text = ' '.join([h for h in header_texts if h])
    
    # Extract fields with priority to header for supplier name
    supplier_name = _find_supplier_name(header_text, debug=debug)
    if not supplier_name:
        supplier_name = _find_supplier_name(document_text, debug=debug)
    
    currency = _find_currency(document_text, debug=debug)
    invoice_or_po_number = _find_invoice_number(document_text, debug=debug)
    document_type = _infer_document_type(document_text, debug=debug)
    
    context = DocumentContext(
        supplier_name=supplier_name,
        currency=currency,
        invoice_or_po_number=invoice_or_po_number,
        document_type=document_type,
        is_scanned=is_scanned,
        document_text=document_text,
        header_text=header_text
    )
    
    logger.info(f"Document context extracted: supplier={supplier_name}, currency={currency}, invoice={invoice_or_po_number}, type={document_type}")
    
    return asdict(context)
