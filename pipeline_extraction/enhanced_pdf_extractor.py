import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import pdfplumber

SUPPLIER_KEYWORDS = ['supplier', 'vendor', 'from']
INVOICE_KEYWORDS = ['invoice', 'po', 'purchase order', 'order', 'ref']
TOTAL_KEYWORDS = ['total', 'grand total', 'amount due', 'balance due', 'net amount']
CURRENCY_SYMBOLS = ['£', '$', '€']


def _normalize_text(text: str) -> str:
    return ' '.join(text.strip().split()) if isinstance(text, str) else ''


def _extract_field_by_keywords(text: str, keywords: List[str]) -> Optional[str]:
    normalized = text.lower()
    for keyword in keywords:
        if keyword in normalized:
            pattern = rf'{keyword}[:\s]*([A-Za-z0-9\-\./\s&,]+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = _normalize_text(match.group(1))
                if value:
                    return value
    return None


def _extract_currency(text: str) -> Optional[str]:
    for symbol in CURRENCY_SYMBOLS:
        if symbol in text:
            return symbol
    currency_match = re.search(r'\b(USD|GBP|EUR|EUR|CAD|AUD|MXN|COP|ARS)\b', text, re.IGNORECASE)
    if currency_match:
        return currency_match.group(1).upper()
    return None


def _extract_invoice_number(text: str) -> Optional[str]:
    patterns = [
        r'\b(?:invoice(?:\s*no\.?|\s*number|\s*#)?\s*[:\-]?\s*)([A-Z0-9\-\/]+)',
        r'\b(?:po(?:\s*no\.?|\s*number|\s*#)?\s*[:\-]?\s*)([A-Z0-9\-\/]+)',
        r'\b(?:order\s*number\s*[:\-]?\s*)([A-Z0-9\-\/]+)',
        r'\b(?:ref(?:erence)?\s*[:\-]?\s*)([A-Z0-9\-\/]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _normalize_text(match.group(1))
    return None


def _extract_amount(text: str) -> Optional[str]:
    match = re.search(r'([£$€]?\s*[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)', text)
    if match:
        return match.group(1).strip()
    return None


def _extract_quantity(text: str) -> Optional[str]:
    match = re.search(r'\b([0-9]+(?:[.,][0-9]+)?)\b', text)
    if match:
        return match.group(1)
    return None


def _extract_unit_price(text: str) -> Optional[str]:
    match = re.search(r'([£$€]?\s*[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)\s*(?:per|/|each|ea\b)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _merge_multiline_row(cells: List[str]) -> str:
    return ' '.join([_normalize_text(cell) for cell in cells if cell])


def _extract_table_rows(page) -> List[Dict[str, Any]]:
    items = []
    tables = page.extract_tables()
    if not tables:
        return items

    for table in tables:
        headers = [(_normalize_text(cell or '')).lower() for cell in table[0]] if table else []
        for row in table[1:]:
            row_text = _merge_multiline_row([str(cell) for cell in row])
            if not row_text:
                continue
            items.append({'row_text': row_text, 'cells': [str(cell or '') for cell in row]})
    return items


def _extract_text_items(page) -> List[Dict[str, Any]]:
    text = page.extract_text() or ''
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items = []

    for line in lines:
        if any(keyword in line.lower() for keyword in ['qty', 'quantity', 'unit price', 'total', 'amount']):
            items.append({'row_text': line, 'cells': [line]})

    return items


def _parse_procurement_record(row: Dict[str, Any], source_page: int) -> Dict[str, Any]:
    text = row['row_text']
    record = {
        'supplier_name': _extract_field_by_keywords(text, SUPPLIER_KEYWORDS) or '',
        'invoice_or_po_number': _extract_invoice_number(text) or '',
        'item_description': '',
        'quantity': _extract_quantity(text) or '',
        'unit_price': _extract_unit_price(text) or '',
        'total_amount': _extract_amount(text) or '',
        'currency': _extract_currency(text) or '',
        'source_page': source_page
    }

    if any(keyword in text.lower() for keyword in ['item', 'description', 'product', 'goods', 'service']):
        record['item_description'] = text
    elif 'qty' in text.lower() or 'quantity' in text.lower():
        record['item_description'] = text
    else:
        record['item_description'] = text

    return record


def extract_procurement_data(pdf_path: str) -> List[Dict[str, Any]]:
    pdf_path = Path(pdf_path)
    records: List[Dict[str, Any]] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            table_rows = _extract_table_rows(page)
            if table_rows:
                for row in table_rows:
                    records.append(_parse_procurement_record(row, page_number))
                continue

            text_items = _extract_text_items(page)
            for row in text_items:
                records.append(_parse_procurement_record(row, page_number))

    return records
