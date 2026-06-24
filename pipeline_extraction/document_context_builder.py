import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import pdfplumber

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    OCR_AVAILABLE = False

SUPPLIER_PATTERNS = [
    r'\b(?:supplier|vendor|from)\b\s*[:\-]?\s*([A-Z0-9\s&.,\-]{4,100})',
    r'\b(?:supplier|vendor|from)\b\s*[:\-]?\s*"?([A-Z0-9\s&.,\-]{4,100})"?'
]
INVOICE_PATTERNS = [
    r'\bINV[-_\s]?[0-9A-Z]{3,}\b',
    r'\bPO[-_\s]?[0-9A-Z]{3,}\b',
    r'\bINVOICE[-_\s]?[0-9A-Z]{3,}\b',
    r'\bPURCHASE\s*ORDER[-_\s]?[0-9A-Z]{3,}\b',
    r'\bORDER\s*NUMBER[-_\s]?[0-9A-Z]{3,}\b',
    r'\bREF(?:ERENCE)?[-_\s]?[0-9A-Z]{3,}\b',
    r'\b[0-9]{4,}[A-Z0-9\-]*\b'
]
CURRENCY_SYMBOLS = ['$', '£', '€', '¥']
CURRENCY_CODES = ['USD', 'GBP', 'EUR', 'CAD', 'AUD', 'MXN', 'COP', 'ARS']
DOCUMENT_TYPE_PATTERNS = {
    'invoice': [r'\binvoice\b', r'\bamount due\b', r'\btotal due\b'],
    'po': [r'\bpurchase order\b', r'\bpo number\b', r'\bpo\b'],
    'tender': [r'\btender\b', r'\bbid\b', r'\bproposal\b']
}


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ''
    return ' '.join(str(value).strip().split())


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


def _find_supplier_name(text: str) -> str:
    candidate = ''
    for pattern in SUPPLIER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            supplier = _normalize_text(match.group(1))
            if len(supplier) >= 4:
                return supplier
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:10]:
        if line.isupper() and len(line) >= 4 and len(line.split()) <= 10:
            return _normalize_text(line)
    return ''


def _find_currency(text: str) -> str:
    for symbol in CURRENCY_SYMBOLS:
        if symbol in text:
            return symbol
    for code in CURRENCY_CODES:
        if re.search(rf'\b{code}\b', text, re.IGNORECASE):
            return code
    return ''


def _find_invoice_number(text: str) -> str:
    text = text.upper()
    for pattern in INVOICE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for candidate in matches:
            candidate = _normalize_text(candidate)
            if len(candidate) >= 4 and not re.fullmatch(r'[A-Z]$', candidate):
                return candidate
    return ''


def _infer_document_type(text: str) -> str:
    lower_text = text.lower()
    for doc_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lower_text):
                return doc_type
    return 'invoice'


def build_document_context(pdf_path: str) -> Dict[str, Any]:
    pdf_path = Path(pdf_path)
    collected_texts: List[str] = []
    header_texts: List[str] = []
    is_scanned = False

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            if len(text.strip()) < 80 or len(text.split()) < 30:
                is_scanned = True
                text = _ocr_page_text(page)
            collected_texts.append(text)
            header_texts.append(_extract_header_text(page))

    document_text = ' '.join([t for t in collected_texts if t])
    header_text = ' '.join([h for h in header_texts if h])

    supplier_name = _find_supplier_name(header_text) or _find_supplier_name(document_text)
    currency = _find_currency(document_text)
    invoice_or_po_number = _find_invoice_number(document_text)
    document_type = _infer_document_type(document_text)

    return {
        'supplier_name': supplier_name,
        'currency': currency,
        'invoice_or_po_number': invoice_or_po_number,
        'document_type': document_type,
        'is_scanned': is_scanned,
        'document_text': document_text,
        'header_text': header_text
    }
