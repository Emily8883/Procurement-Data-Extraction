import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pdfplumber
from .document_context_builder import build_document_context
from .table_schema_inference import infer_table_schema, map_row_cells, is_header_row
from .row_alignment_corrector import correct_row_alignment

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    OCR_AVAILABLE = False

SUPPLIER_KEYWORDS = ['supplier', 'vendor', 'from']
INVOICE_PATTERNS = [
    r'\binvoice(?:\s*no\.?|\s*number|\s*#)?\s*[:\-]?\s*([A-Z0-9\-\/]+)',
    r'\bpo(?:\s*no\.?|\s*number|\s*#)?\s*[:\-]?\s*([A-Z0-9\-\/]+)',
    r'\bpurchase order\s*[:\-]?\s*([A-Z0-9\-\/]+)',
    r'\border\s*number\s*[:\-]?\s*([A-Z0-9\-\/]+)',
    r'\bref(?:erence)?\s*[:\-]?\s*([A-Z0-9\-\/]+)'
]
TOTAL_PATTERNS = [
    r'\bgrand total\b',
    r'\bamount due\b',
    r'\bamount payable\b',
    r'\btotal amount\b',
    r'\btotal\b',
    r'\bbalance due\b'
]
CURRENCY_SYMBOLS = ['£', '$', '€']
CURRENCY_KEYWORDS = ['usd', 'gbp', 'eur', 'cad', 'aud', 'mxn', 'cop', 'ars']


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ''
    return ' '.join(str(value).strip().split())


def _is_scanned_page(page) -> bool:
    text = page.extract_text() or ''
    if len(text.strip()) < 80:
        return True
    words = text.split()
    return len(words) < 30


def _ocr_page_text(page) -> str:
    if not OCR_AVAILABLE or pytesseract is None:
        return page.extract_text() or ''

    try:
        image = page.to_image(resolution=300)
        pil_image = getattr(image, 'original', None)
        if pil_image is None:
            pil_image = image
        ocr_text = pytesseract.image_to_string(pil_image)
        return ocr_text or ''
    except Exception:
        return page.extract_text() or ''


def _extract_top_page_text(page) -> str:
    try:
        words = page.extract_words()
        if words:
            top_limit = page.height * 0.20
            header_words = [w['text'] for w in words if w.get('top', 0) <= top_limit]
            return ' '.join(header_words)
    except Exception:
        pass

    text = page.extract_text() or ''
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return ' '.join(lines[:min(10, len(lines))])


def _extract_by_keywords(text: str, keywords: List[str]) -> Optional[str]:
    lower = text.lower()
    for keyword in keywords:
        if keyword in lower:
            patterns = [
                rf'{keyword}\s*[:\-]?\s*([A-Za-z0-9\-\/\s&,]+)',
                rf'{keyword}\s*[:\-]?\s*([A-Za-z0-9\-\/]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    candidate = _normalize_text(match.group(1))
                    if candidate:
                        return candidate
    return None


def _extract_invoice_number(text: str) -> str:
    for pattern in INVOICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _normalize_text(match.group(1))
    return ''


def _extract_currency(text: str) -> str:
    for symbol in CURRENCY_SYMBOLS:
        if symbol in text:
            return symbol
    for keyword in CURRENCY_KEYWORDS:
        if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
            return keyword.upper()
    return ''


def _extract_amount(text: str) -> str:
    match = re.search(r'([£$€]?\s*[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)', text)
    return _normalize_text(match.group(1)) if match else ''


def _extract_unit_price(text: str) -> str:
    match = re.search(r'([£$€]?\s*[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)\s*(?:per|/|each|ea\b)', text, re.IGNORECASE)
    if match:
        return _normalize_text(match.group(1))
    return ''


def _extract_quantity(text: str) -> str:
    match = re.search(r'\b([0-9]+(?:[.,][0-9]+)?)\b', text)
    return _normalize_text(match.group(1)) if match else ''


def _clean_cell(cell: Any) -> str:
    return _normalize_text(str(cell)) if cell is not None else ''


def _normalize_row(row: List[Any], target_len: int) -> List[str]:
    cleaned = [_clean_cell(cell) for cell in row]
    if len(cleaned) == target_len:
        return cleaned
    if len(cleaned) < target_len:
        return cleaned + [''] * (target_len - len(cleaned))
    return cleaned[:target_len-1] + [' '.join(cleaned[target_len-1:])]


def _merge_broken_rows(rows: List[List[str]], header_count: int) -> List[List[str]]:
    merged_rows: List[List[str]] = []
    for row in rows:
        if not any(cell.strip() for cell in row):
            continue
        if len(row) < header_count and merged_rows:
            previous = merged_rows[-1]
            previous = [
                _normalize_text(prev + ' ' + row[idx]) if idx < len(row) and row[idx].strip() else prev
                for idx, prev in enumerate(previous)
            ]
            merged_rows[-1] = previous
            continue
        if row[0].strip() == '' and merged_rows:
            previous = merged_rows[-1]
            previous[-1] = _normalize_text(previous[-1] + ' ' + ' '.join(row))
            merged_rows[-1] = previous
            continue
        merged_rows.append(_normalize_row(row, header_count))
    return merged_rows


def _extract_table_rows(page) -> List[List[str]]:
    extracted = []
    try:
        tables = page.extract_tables()
    except Exception:
        return extracted

    if not tables:
        return extracted

    for table in tables:
        if not table:
            continue
        header = [_clean_cell(cell) for cell in table[0]]
        header_count = max(len(header), 1)
        content_rows = [
            [_clean_cell(cell) for cell in row]
            for row in table[1:]
            if row and any(_clean_cell(cell) for cell in row)
        ]
        if not content_rows:
            continue

        merged_rows = _merge_broken_rows(content_rows, header_count)
        for row in merged_rows:
            extracted.append(row)
    return extracted


def _extract_text_rows(page_text: str) -> List[str]:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    candidates: List[str] = []
    for line in lines:
        normalized = line.lower()
        if any(keyword in normalized for keyword in ['qty', 'quantity', 'unit price', 'amount', 'total', 'description', '$', '£', '€', 'usd', 'gbp', 'eur']):
            candidates.append(line)
        elif re.search(r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\b', line) and len(line) > 20:
            candidates.append(line)
    return candidates


def _pick_description(row: List[str]) -> str:
    if not row:
        return ''
    text_cells = [cell for cell in row if cell and not re.search(r'^[£$€]?\s*\d', cell)]
    if text_cells:
        return max(text_cells, key=len)
    return row[0]


def _pick_price(row: List[str]) -> str:
    for cell in reversed(row):
        if re.search(r'[£$€]|\b(?:usd|gbp|eur)\b', cell, re.IGNORECASE):
            return cell
        if re.search(r'^[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?$', cell):
            return cell
    return ''


def _parse_mapped_table_record(mapped: Dict[str, str], context: Dict[str, Any], source_page: int, pdf_name: str, row: List[str]) -> Dict[str, Any]:
    description = mapped.get('description', '')
    quantity = mapped.get('quantity', '')
    unit_price = mapped.get('unit_price', '')
    total_amount = mapped.get('total_amount', '')
    currency = mapped.get('currency', '') or context.get('currency', '')

    record = {
        'pdf_name': pdf_name,
        'document_name': pdf_name,
        'source_page': source_page,
        'supplier_name': context.get('supplier_name', ''),
        'invoice_or_po_number': context.get('invoice_or_po_number', ''),
        'document_type': context.get('document_type', ''),
        'item_description': description,
        'quantity': quantity,
        'unit_price': unit_price,
        'total_amount': total_amount,
        'currency': currency,
        'raw_row_text': ' | '.join(row),
        'row_cells': row
    }
    return record


def _parse_text_record(line: str, context: Dict[str, Any], page_text: str, page_header: str, source_page: int, pdf_name: str) -> Dict[str, Any]:
    quantity = _extract_quantity(line)
    unit_price = _extract_unit_price(line)
    total_amount = _extract_amount(line)
    currency = _extract_currency(line) or context.get('currency', '')

    record = {
        'pdf_name': pdf_name,
        'document_name': pdf_name,
        'source_page': source_page,
        'supplier_name': context.get('supplier_name', ''),
        'invoice_or_po_number': context.get('invoice_or_po_number', ''),
        'document_type': context.get('document_type', ''),
        'item_description': _normalize_text(line),
        'quantity': quantity,
        'unit_price': unit_price,
        'total_amount': total_amount,
        'currency': currency,
        'raw_row_text': line,
        'row_cells': [line]
    }
    return record


def default_safe_schema() -> Dict[str, Any]:
    """Return a safe default schema when inference fails.
    Maps columns in expected order: description, quantity, unit_price, total_amount.
    """
    return {
        'col_index_map': {
            'description': 0,
            'quantity': 1,
            'unit_price': 2,
            'total_amount': 3
        }
    }


def extract_procurement_data_hybrid(pdf_path: str) -> List[Dict[str, Any]]:
    pdf_path = Path(pdf_path)
    records: List[Dict[str, Any]] = []
    context = build_document_context(str(pdf_path))

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            is_scanned = _is_scanned_page(page)
            page_text = page.extract_text() or ''
            if is_scanned:
                page_text = _ocr_page_text(page)

            page_header = _extract_top_page_text(page)
            table_rows = _extract_table_rows(page)

            if table_rows:
                try:
                    schema = infer_table_schema(table_rows)
                except Exception as e:
                    logging.warning(f"Schema inference failed for page {page_num} of {pdf_path.name}: {e}. Using default schema.")
                    schema = default_safe_schema()
                
                for row in table_rows:
                    if is_header_row(row):
                        continue
                    # Use row-level alignment correction instead of simple schema mapping
                    mapped = correct_row_alignment(row, schema, context)
                    if not mapped.get('description') and not mapped.get('quantity') and not mapped.get('unit_price'):
                        continue
                    records.append(_parse_mapped_table_record(mapped, context, page_num, pdf_path.name, row))
            else:
                text_rows = _extract_text_rows(page_text)
                if text_rows:
                    for line in text_rows:
                        records.append(_parse_text_record(line, context, page_text, page_header, page_num, pdf_path.name))

    return records
