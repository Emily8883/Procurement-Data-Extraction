import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

HEADER_LABELS = ['DESCRIPCIÓN', 'CANT', 'CANT.', 'QTY', 'QUANTITY', 'UNIT PRICE', 'PRICE', 'TOTAL', 'AMOUNT', 'ITEM', 'ÍTEM', 'MEDIDA', 'DESCRIPTION', 'UNIT', 'CURRENCY']
CURRENCY_SYMBOLS = ['$', '£', '€', '¥']
CURRENCY_CODES = ['USD', 'GBP', 'EUR', 'CAD', 'AUD', 'MXN', 'COP', 'ARS']
PRICE_REGEX = re.compile(r'[£$€¥]?\s*[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?')
INT_REGEX = re.compile(r'^[0-9]+$')
NUMERIC_REGEX = re.compile(r'^[0-9]+(?:[.,][0-9]+)?$')


def _normalize_cell(cell: str) -> str:
    return ' '.join(cell.strip().split()) if isinstance(cell, str) else ''


def is_header_row(row: List[str]) -> bool:
    if not row:
        return False
    label_count = 0
    total_cells = len(row)
    for cell in row:
        value = cell.strip().upper()
        if any(label in value for label in HEADER_LABELS):
            label_count += 1
        elif value.isupper() and len(value) <= 20 and len(value.split()) <= 3 and not NUMERIC_REGEX.match(value):
            label_count += 1
    return label_count >= max(1, int(total_cells * 0.4))


def _has_currency(cell: str) -> bool:
    value = cell.upper()
    if any(symbol in cell for symbol in CURRENCY_SYMBOLS):
        return True
    return any(code in value for code in CURRENCY_CODES)


def _is_price(cell: str) -> bool:
    if not cell:
        return False
    value = _normalize_cell(cell)
    if _has_currency(value):
        return True
    return bool(PRICE_REGEX.search(value))


def _is_quantity(cell: str) -> bool:
    if not cell:
        return False
    value = _normalize_cell(cell).replace(',', '').replace('.', '')
    return bool(INT_REGEX.match(value)) and len(value) <= 5


def _text_score(cell: str) -> int:
    return len(cell.strip())


def _safe_parse_numeric(value: str) -> float:
    """Safely parse a numeric value and skip malformed OCR numbers."""
    if not value:
        return 0.0

    original = value
    cleaned = re.sub(r'[^0-9.,]', '', value)
    if not cleaned:
        return 0.0

    # Extract candidate numeric tokens
    tokens = re.findall(r'\d+(?:[.,]\d+)*', cleaned)
    for token in tokens:
        if re.search(r'[.,]{2,}', token):
            continue
        
        if token.count('.') > 1 and token.count(',') == 0:
            continue
        
        normalized = token
        try:
            if '.' in token and ',' in token:
                last_dot = token.rfind('.')
                last_comma = token.rfind(',')
                if last_dot > last_comma:
                    normalized = token.replace(',', '')
                else:
                    normalized = token.replace('.', '').replace(',', '.')
            elif token.count(',') > 1 and token.count('.') == 0:
                parts = token.split(',')
                if all(len(part) == 3 for part in parts[1:]):
                    normalized = ''.join(parts[:-1]) + '.' + parts[-1]
                else:
                    continue
            else:
                normalized = token.replace(',', '.')

            if normalized.count('.') > 1:
                continue

            return float(normalized)
        except Exception:
            continue

    if re.search(r'[0-9]', cleaned):
        logger.warning(f"Skipped malformed numeric value: '{original}' cleaned='{cleaned}'")
    return 0.0


def _is_ocr_garbage(cell: str) -> bool:
    """Detect OCR garbage: repeated digits, overly long numeric strings."""
    if not cell:
        return False
    normalized = _normalize_cell(cell)
    if not normalized:
        return False
    
    # Check for overly long numeric strings (> 15 chars of digits/separators)
    numeric_only = re.sub(r'[^0-9.,]', '', normalized)
    if len(numeric_only) > 15:
        return True
    
    # Check for repeated digit patterns like "111111" or "3.2.1.3.2.1"
    # Pattern: same digit/pattern repeating 4+ times
    if re.search(r'(\d)\1{3,}', numeric_only):
        return True
    if re.search(r'([0-9]\.[0-9]){4,}', normalized):
        return True
    
    return False


def infer_table_schema(rows: List[List[str]]) -> Dict[str, Any]:
    """Infer table schema with defensive checks. Never crashes; returns safe defaults."""
    try:
        # Validate input
        if not rows or not isinstance(rows, list):
            return {'col_index_map': {}}
        
        # Filter out header rows and malformed rows
        filtered = []
        for row in rows:
            # Skip rows that are not lists or are empty
            if not isinstance(row, (list, tuple)) or not row:
                continue
            # Skip rows where all cells are malformed (not strings)
            if not any(isinstance(cell, str) for cell in row):
                continue
            if not is_header_row(row):
                filtered.append(row)
        
        if not filtered:
            filtered = [row for row in rows if isinstance(row, (list, tuple)) and len(row) > 0]
        if not filtered:
            return {'col_index_map': {}}

        col_count = max((len(row) for row in filtered), default=0)
        if col_count == 0:
            return {'col_index_map': {}}

        stats = [{
            'price_count': 0,
            'quantity_count': 0,
            'currency_count': 0,
            'text_length': 0,
            'numeric_count': 0,
            'max_price_value': 0.0,
            'row_count': 0
        } for _ in range(col_count)]

        for row in filtered:
            # Skip malformed rows during stats computation
            if not isinstance(row, (list, tuple)):
                continue
            
            for idx in range(col_count):
                try:
                    cell = row[idx] if idx < len(row) else ''
                    # Skip garbage values
                    if _is_ocr_garbage(cell):
                        continue
                    
                    normalized = _normalize_cell(cell)
                    stats[idx]['text_length'] += len(normalized)
                    
                    if _is_price(normalized):
                        stats[idx]['price_count'] += 1
                        stats[idx]['currency_count'] += 1 if _has_currency(normalized) else 0
                        value = _safe_parse_numeric(normalized) if re.search(r'[0-9]', normalized) else 0.0
                        stats[idx]['max_price_value'] = max(stats[idx]['max_price_value'], value)
                    if _is_quantity(normalized):
                        stats[idx]['quantity_count'] += 1
                    if NUMERIC_REGEX.match(normalized):
                        stats[idx]['numeric_count'] += 1
                    stats[idx]['row_count'] += 1
                except Exception:
                    # Skip cells that cause errors during analysis
                    continue

        # Find best columns with error handling
        try:
            description_index = max(range(col_count), key=lambda i: (stats[i]['text_length'], -stats[i]['numeric_count']))
            quantity_index = max(range(col_count), key=lambda i: (stats[i]['quantity_count'], -stats[i]['price_count'], -stats[i]['text_length']))
            unit_price_index = max(range(col_count), key=lambda i: (stats[i]['price_count'], stats[i]['currency_count'], -stats[i]['numeric_count']))
            total_amount_index = max(range(col_count), key=lambda i: (stats[i]['max_price_value'], stats[i]['price_count'], stats[i]['currency_count']))
        except Exception:
            # If column selection fails, return empty map
            return {'col_index_map': {}}

        # Resolve conflicts
        if quantity_index == description_index:
            quantity_index = next((i for i in range(col_count) if i != description_index and stats[i]['quantity_count'] > 0), quantity_index)
        if unit_price_index == description_index:
            unit_price_index = next((i for i in range(col_count) if i != description_index and stats[i]['price_count'] > 0), unit_price_index)
        if total_amount_index == description_index:
            total_amount_index = next((i for i in range(col_count) if i != description_index and stats[i]['price_count'] > 0), total_amount_index)

        if unit_price_index == total_amount_index:
            total_amount_index = next((i for i in range(col_count) if i != unit_price_index and stats[i]['price_count'] > 0), total_amount_index)

        # Build result
        col_index_map = {}
        if stats[description_index]['text_length'] > 0:
            col_index_map['description'] = description_index
        if stats[quantity_index]['quantity_count'] > 0:
            col_index_map['quantity'] = quantity_index
        if stats[unit_price_index]['price_count'] > 0:
            col_index_map['unit_price'] = unit_price_index
        if stats[total_amount_index]['price_count'] > 0:
            col_index_map['total_amount'] = total_amount_index

        return {'col_index_map': col_index_map}
    
    except Exception:
        # Final fallback: return empty schema to prevent crash
        return {'col_index_map': {}}


def map_row_cells(row: List[str], schema: Dict[str, Any]) -> Dict[str, str]:
    field_map = {'description': '', 'quantity': '', 'unit_price': '', 'total_amount': '', 'currency': ''}
    index_map = schema.get('col_index_map', {})

    if 'description' in index_map and index_map['description'] < len(row):
        field_map['description'] = _normalize_cell(row[index_map['description']])
    if 'quantity' in index_map and index_map['quantity'] < len(row):
        field_map['quantity'] = _normalize_cell(row[index_map['quantity']])
    if 'unit_price' in index_map and index_map['unit_price'] < len(row):
        field_map['unit_price'] = _normalize_cell(row[index_map['unit_price']])
    if 'total_amount' in index_map and index_map['total_amount'] < len(row):
        field_map['total_amount'] = _normalize_cell(row[index_map['total_amount']])

    if not field_map['currency']:
        for cell in row:
            if _has_currency(cell):
                field_map['currency'] = _normalize_cell(cell)
                break

    if not field_map['description']:
        candidates = [cell for cell in row if not _is_price(cell) and not _is_quantity(cell)]
        if candidates:
            field_map['description'] = max(candidates, key=lambda x: len(x))

    return field_map
