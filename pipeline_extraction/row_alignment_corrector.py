import re
from typing import List, Dict, Any, Tuple, Optional
from .utils.safe_parsing import safe_float

CURRENCY_SYMBOLS = ['$', '£', '€', '¥']
CURRENCY_CODES = ['USD', 'GBP', 'EUR', 'CAD', 'AUD', 'MXN', 'COP', 'ARS', 'JPY', 'CNY']
QUANTITY_KEYWORDS = ['qty', 'quantity', 'cant', 'cant.', 'amount', 'units']
PRICE_KEYWORDS = ['unit price', 'price', 'unit', 'per']
TOTAL_KEYWORDS = ['total', 'amount', 'subtotal']


def _normalize_cell(cell: str) -> str:
    """Normalize cell content."""
    if not isinstance(cell, str):
        cell = str(cell) if cell is not None else ''
    return ' '.join(cell.strip().split())


def _extract_numeric_value(cell: str) -> float:
    """Extract numeric value from cell, return 0.0 if not numeric."""
    normalized = _normalize_cell(cell)
    numeric_only = re.sub(r'[^0-9.,]', '', normalized)
    return safe_float(numeric_only) if numeric_only else 0.0


def _is_numeric_only(cell: str) -> bool:
    """Check if cell contains only digits and separators (no text)."""
    normalized = _normalize_cell(cell)
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[$£€¥\s]', '', normalized)
    # Check if what remains is only digits and separators
    return bool(re.match(r'^[0-9.,]+$', cleaned)) and len(cleaned) > 0


def _text_length(cell: str) -> int:
    """Get text length of cell."""
    normalized = _normalize_cell(cell)
    return len(normalized)


def _has_currency(cell: str) -> bool:
    """Check if cell contains currency symbol or code."""
    upper_cell = cell.upper()
    if any(sym in cell for sym in CURRENCY_SYMBOLS):
        return True
    return any(code in upper_cell for code in CURRENCY_CODES)


def _score_as_quantity(cell: str) -> float:
    """Score how likely this cell is a quantity value.
    
    High score: short integers (1-5 digits), no decimals, no text.
    Low score: text, very large numbers, prices with currency.
    """
    normalized = _normalize_cell(cell)
    if not normalized or _text_length(cell) > 10:
        return 0.0
    
    numeric_value = _extract_numeric_value(cell)
    if numeric_value <= 0:
        return 0.0
    
    # Currency symbols/codes indicate this is likely a price, not quantity
    if _has_currency(cell):
        return 0.0
    
    # Quantity is typically 1-5 digits
    numeric_str = re.sub(r'[^0-9]', '', normalized)
    if len(numeric_str) > 5:
        return 0.1  # Low score for very large numbers
    
    # Integer quantities only (no decimals)
    if '.' in numeric_str or ',' in numeric_str:
        return 0.2  # Lower score for decimals in quantity
    
    return 1.0  # Perfect match


def _score_as_unit_price(cell: str) -> float:
    """Score how likely this cell is a unit price.
    
    High score: decimal values with 2-4 digits before decimal, currency symbols/codes.
    Low score: text, very small integers, very large numbers.
    """
    normalized = _normalize_cell(cell)
    if not normalized:
        return 0.0
    
    numeric_value = _extract_numeric_value(cell)
    if numeric_value <= 0:
        return 0.0
    
    # Currency indicator is a strong signal
    if _has_currency(cell):
        return 0.9
    
    # Price patterns: 2-3 digit before decimal with decimal places
    if re.search(r'^[0-9]{1,4}[.,][0-9]{2}$', normalized.replace('$', '').replace('£', '').replace('€', '').strip()):
        return 0.95
    
    # Decimal values in reasonable price range (0.01 to 999999.99)
    if 0.01 <= numeric_value <= 999999.99:
        # Decimal point suggests pricing
        if '.' in normalized or ',' in normalized:
            return 0.8
        return 0.5
    
    return 0.0


def _score_as_total_amount(cell: str, row_cells: List[str]) -> float:
    """Score how likely this cell is a total amount.
    
    High score: largest numeric value in row, especially with currency.
    Low score: small values, text only.
    """
    normalized = _normalize_cell(cell)
    if not normalized:
        return 0.0
    
    numeric_value = _extract_numeric_value(cell)
    if numeric_value <= 0:
        return 0.0
    
    # Currency indicator is strong signal
    if _has_currency(cell):
        return 0.9
    
    # Find max numeric value in row
    max_value = max((_extract_numeric_value(c) for c in row_cells), default=0.0)
    
    # If this is the largest value, high score
    if numeric_value >= max_value * 0.99:  # Allow 1% variance for floating point
        return 0.95
    
    # If it's reasonably large (at least 10% of max), decent score
    if numeric_value >= max_value * 0.1:
        return 0.6
    
    return 0.0


def _score_as_description(cell: str) -> float:
    """Score how likely this cell is an item description.
    
    High score: longest text, multiple words, no numeric-only content.
    Low score: numeric only, very short.
    """
    normalized = _normalize_cell(cell)
    if not normalized:
        return 0.0
    
    # Numeric-only is not description
    if _is_numeric_only(cell):
        return 0.0
    
    # Single character or very short is unlikely
    if len(normalized) < 2:
        return 0.1
    
    # Words indicate description
    word_count = len(normalized.split())
    if word_count >= 2:
        return 0.9
    
    # Single word with text is possible description
    if len(normalized) >= 5:
        return 0.7
    
    return 0.5


def _extract_currency_from_cell(cell: str) -> str:
    """Extract currency symbol or code from cell."""
    upper_cell = cell.upper()
    
    for symbol in CURRENCY_SYMBOLS:
        if symbol in cell:
            return symbol
    
    for code in CURRENCY_CODES:
        if code in upper_cell:
            return code
    
    return ''


def _extract_currency_from_row(row_cells: List[str], document_currency: str = '') -> str:
    """Extract currency from row, falling back to document currency."""
    # Check each cell for currency
    for cell in row_cells:
        cell_currency = _extract_currency_from_cell(cell)
        if cell_currency:
            return cell_currency
    
    # Fall back to document currency
    return document_currency


def correct_row_alignment(
    row_cells: List[str],
    schema: Dict[str, Any],
    document_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform row-level heuristic correction of field alignment.
    
    Takes schema from table_schema_inference and validates/corrects it per row.
    Uses heuristic scoring to ensure:
    - quantity is numeric/short integer
    - unit_price is decimal-like value
    - total_amount is largest numeric value
    - item_description is longest text
    
    Falls back to heuristic scoring if schema confidence is low.
    
    Args:
        row_cells: List of cell values from the row
        schema: Column mapping from infer_table_schema
        document_context: Document-level context (supplier, currency, etc.)
    
    Returns:
        Corrected mapping with description, quantity, unit_price, total_amount, currency
    """
    if not row_cells:
        return {
            'description': '',
            'quantity': '',
            'unit_price': '',
            'total_amount': '',
            'currency': document_context.get('currency', '')
        }
    
    col_index_map = schema.get('col_index_map', {})
    
    # Build heuristic scores for each column
    scores = {
        'description': [],
        'quantity': [],
        'unit_price': [],
        'total_amount': []
    }
    
    for idx, cell in enumerate(row_cells):
        scores['description'].append((_score_as_description(cell), idx))
        scores['quantity'].append((_score_as_quantity(cell), idx))
        scores['unit_price'].append((_score_as_unit_price(cell), idx))
        scores['total_amount'].append((_score_as_total_amount(cell, row_cells), idx))
    
    # Sort by score descending, get best index for each field
    heuristic_map = {
        'description': max(scores['description'], default=(0.0, -1))[1],
        'quantity': max(scores['quantity'], default=(0.0, -1))[1],
        'unit_price': max(scores['unit_price'], default=(0.0, -1))[1],
        'total_amount': max(scores['total_amount'], default=(0.0, -1))[1]
    }
    
    # Resolve conflicts: ensure no two fields map to same column
    used_indices = set()
    final_map = {}
    
    # Priority: description > quantity > unit_price > total_amount
    for field in ['description', 'quantity', 'unit_price', 'total_amount']:
        heur_idx = heuristic_map[field]
        schema_idx = col_index_map.get(field, -1)
        
        # If schema and heuristic agree and not used, use it
        if schema_idx >= 0 and schema_idx == heur_idx and schema_idx not in used_indices:
            final_map[field] = schema_idx
            used_indices.add(schema_idx)
        # If heuristic has good score and not used, prefer it
        elif heur_idx >= 0 and scores[field][heur_idx][0] >= 0.7 and heur_idx not in used_indices:
            final_map[field] = heur_idx
            used_indices.add(heur_idx)
        # Otherwise, use schema if available
        elif schema_idx >= 0 and schema_idx not in used_indices:
            final_map[field] = schema_idx
            used_indices.add(schema_idx)
        # Last resort: use heuristic index
        elif heur_idx >= 0 and heur_idx not in used_indices:
            final_map[field] = heur_idx
            used_indices.add(heur_idx)
    
    # Extract values using corrected mapping
    result = {
        'description': _normalize_cell(row_cells[final_map['description']]) if final_map.get('description', -1) >= 0 else '',
        'quantity': _normalize_cell(row_cells[final_map['quantity']]) if final_map.get('quantity', -1) >= 0 else '',
        'unit_price': _normalize_cell(row_cells[final_map['unit_price']]) if final_map.get('unit_price', -1) >= 0 else '',
        'total_amount': _normalize_cell(row_cells[final_map['total_amount']]) if final_map.get('total_amount', -1) >= 0 else '',
    }
    
    # Validate and clean results
    
    # Quantity must be numeric
    if result['quantity'] and not _is_numeric_only(result['quantity']):
        qty_value = _extract_numeric_value(result['quantity'])
        result['quantity'] = str(int(qty_value)) if qty_value > 0 else ''
    
    # Unit price must be numeric
    if result['unit_price'] and not _is_numeric_only(result['unit_price']):
        price_value = _extract_numeric_value(result['unit_price'])
        result['unit_price'] = str(price_value) if price_value > 0 else ''
    
    # Total amount must be numeric
    if result['total_amount'] and not _is_numeric_only(result['total_amount']):
        total_value = _extract_numeric_value(result['total_amount'])
        result['total_amount'] = str(total_value) if total_value > 0 else ''
    
    # Ensure description never contains only numbers
    if result['description'] and _is_numeric_only(result['description']):
        result['description'] = ''
    
    # Ensure quantity and unit_price are different
    if result['quantity'] and result['unit_price'] and result['quantity'] == result['unit_price']:
        qty_val = safe_float(result['quantity'])
        price_val = safe_float(result['unit_price'])
        if qty_val < price_val:
            # Quantity is smaller, keep it
            result['unit_price'] = ''
        else:
            # Price is smaller or equal, keep it as price
            result['quantity'] = ''
    
    # Total amount should be largest
    qty_val = safe_float(result['quantity'])
    price_val = safe_float(result['unit_price'])
    total_val = safe_float(result['total_amount'])
    
    if total_val > 0 and qty_val > total_val and price_val == 0:
        # Likely quantity is actually total
        result['total_amount'] = result['quantity']
        result['quantity'] = ''
    
    # Extract currency
    row_currency = _extract_currency_from_row(row_cells, document_context.get('currency', ''))
    result['currency'] = row_currency or document_context.get('currency', '')
    
    return result
