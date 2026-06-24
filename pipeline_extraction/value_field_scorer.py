import re
from typing import List, Dict, Any, Tuple, Optional
from .utils.safe_parsing import safe_float

CURRENCY_SYMBOLS = ['$', '£', '€', '¥']
CURRENCY_CODES = ['USD', 'GBP', 'EUR', 'CAD', 'AUD', 'MXN', 'COP', 'ARS', 'JPY', 'CNY', 'INR', 'BRL']


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


def _is_integer(cell: str) -> bool:
    """Check if value is integer (no decimal places)."""
    numeric_only = re.sub(r'[^0-9.,]', '', _normalize_cell(cell))
    # Remove thousands separators, check if has decimal separator
    if ',' in numeric_only and '.' in numeric_only:
        # Could be EU format (1.234,56) or US format (1,234.56)
        # Check which is last - that's the decimal separator
        last_dot = numeric_only.rfind('.')
        last_comma = numeric_only.rfind(',')
        if last_comma > last_dot:
            # EU format - comma is decimal
            return numeric_only.count(',') <= 1 and len(numeric_only.split(',')[1]) == 0
        else:
            # US format - dot is decimal
            return numeric_only.count('.') <= 1 and len(numeric_only.split('.')[1]) == 0
    elif '.' in numeric_only:
        parts = numeric_only.split('.')
        return len(parts) == 2 and len(parts[1]) == 0
    elif ',' in numeric_only:
        parts = numeric_only.split(',')
        return len(parts) == 2 and len(parts[1]) == 0
    return True


def _has_currency(cell: str) -> bool:
    """Check if cell contains currency symbol or code."""
    upper_cell = cell.upper()
    if any(sym in cell for sym in CURRENCY_SYMBOLS):
        return True
    return any(code in upper_cell for code in CURRENCY_CODES)


def _text_length(cell: str) -> int:
    """Get non-numeric text length of cell."""
    normalized = _normalize_cell(cell)
    # Remove numeric characters
    text_only = re.sub(r'[0-9.,]', '', normalized)
    return len(text_only.strip())


def score_quantity_candidate(
    cell: str,
    row_cells: List[str],
    all_numeric_values: List[float]
) -> float:
    """
    Score how likely this cell is a quantity value.
    
    High score: smallest numeric value in row, integer format, 1-5 digits
    Low score: text, very large numbers, prices with currency, no numeric content
    
    Args:
        cell: Cell to score
        row_cells: All cells in row for context
        all_numeric_values: All numeric values in row (for comparison)
    
    Returns:
        Score 0.0-1.0
    """
    normalized = _normalize_cell(cell)
    if not normalized:
        return 0.0
    
    numeric_value = _extract_numeric_value(cell)
    if numeric_value <= 0:
        return 0.0
    
    # If has currency symbol, likely not quantity
    if _has_currency(cell):
        return 0.1
    
    # Get numeric values for comparison
    numeric_values = [v for v in all_numeric_values if v > 0]
    if not numeric_values:
        return 0.0
    
    min_value = min(numeric_values)
    max_value = max(numeric_values)
    
    score = 0.0
    
    # Strong signal: is the smallest value
    if abs(numeric_value - min_value) < 0.01:
        score += 0.8
    # Medium signal: is smaller than average
    elif numeric_value < sum(numeric_values) / len(numeric_values):
        score += 0.4
    # Weak signal: normal value
    else:
        score += 0.1
    
    # Integer bonus
    if _is_integer(cell):
        score += 0.2
    
    # Length of numeric string - quantities are typically short (1-5 digits)
    numeric_str = re.sub(r'[^0-9]', '', normalized)
    if len(numeric_str) <= 5:
        score += 0.1
    elif len(numeric_str) > 8:
        score -= 0.3
    
    # Value range check: quantities typically < 1000
    if numeric_value > 10000:
        score -= 0.4
    
    return min(1.0, max(0.0, score))


def score_unit_price_candidate(
    cell: str,
    row_cells: List[str],
    all_numeric_values: List[float]
) -> float:
    """
    Score how likely this cell is a unit price.
    
    High score: decimal values, mid-range, currency symbols, reasonable price range
    Low score: very small, very large, numeric-only without decimal
    
    Args:
        cell: Cell to score
        row_cells: All cells in row for context
        all_numeric_values: All numeric values in row
    
    Returns:
        Score 0.0-1.0
    """
    normalized = _normalize_cell(cell)
    if not normalized:
        return 0.0
    
    numeric_value = _extract_numeric_value(cell)
    if numeric_value <= 0:
        return 0.0
    
    numeric_values = [v for v in all_numeric_values if v > 0]
    if not numeric_values:
        return 0.0
    
    min_value = min(numeric_values)
    max_value = max(numeric_values)
    
    score = 0.0
    
    # Strong signal: has currency
    if _has_currency(cell):
        score += 0.7
    
    # Medium signal: has decimal point (likely price)
    if '.' in normalized or ',' in normalized:
        # Check if it's a price-like decimal (not too many places)
        decimal_part = re.search(r'[.,](\d+)', normalized)
        if decimal_part and len(decimal_part.group(1)) == 2:  # Two decimal places
            score += 0.6
        elif decimal_part and len(decimal_part.group(1)) <= 4:
            score += 0.3
    else:
        # No decimal point
        score -= 0.2
    
    # Value range: prices typically in mid-range
    # Not the smallest (that's quantity) and not the largest (that's total)
    avg_value = sum(numeric_values) / len(numeric_values)
    
    if numeric_value < min_value * 5 and numeric_value > min_value * 0.5:
        # In reasonable range compared to smallest
        score += 0.3
    elif numeric_value < max_value:
        # Less than max (good)
        score += 0.2
    elif numeric_value == max_value:
        # Is the max (bad for unit price)
        score -= 0.3
    
    # Reasonable price range check (0.01 to 100000)
    if 0.01 <= numeric_value <= 100000:
        score += 0.2
    elif numeric_value > 100000:
        score -= 0.4
    
    return min(1.0, max(0.0, score))


def score_total_amount_candidate(
    cell: str,
    row_cells: List[str],
    all_numeric_values: List[float]
) -> float:
    """
    Score how likely this cell is a total amount.
    
    High score: largest numeric value in row, currency symbols
    Low score: small values, numeric-only without context
    
    Args:
        cell: Cell to score
        row_cells: All cells in row
        all_numeric_values: All numeric values in row
    
    Returns:
        Score 0.0-1.0
    """
    normalized = _normalize_cell(cell)
    if not normalized:
        return 0.0
    
    numeric_value = _extract_numeric_value(cell)
    if numeric_value <= 0:
        return 0.0
    
    numeric_values = [v for v in all_numeric_values if v > 0]
    if not numeric_values:
        return 0.0
    
    max_value = max(numeric_values)
    min_value = min(numeric_values)
    
    score = 0.0
    
    # Strong signal: is the largest value
    if abs(numeric_value - max_value) < max_value * 0.01 or numeric_value >= max_value * 0.99:
        score += 0.9
    # Medium signal: close to max
    elif numeric_value >= max_value * 0.8:
        score += 0.5
    # Low signal: in middle
    elif numeric_value >= max_value * 0.5:
        score += 0.2
    # Very low: small value
    else:
        score -= 0.3
    
    # Currency indicator
    if _has_currency(cell):
        score += 0.4
    
    # Decimal point (prices have decimals)
    if '.' in normalized or ',' in normalized:
        score += 0.2
    
    return min(1.0, max(0.0, score))


def score_description_candidate(
    cell: str,
    row_cells: List[str]
) -> float:
    """
    Score how likely this cell is an item description.
    
    High score: longest text, multiple words, no numeric-only content
    Low score: numeric only, very short, currency symbols
    
    Args:
        cell: Cell to score
        row_cells: All cells in row
    
    Returns:
        Score 0.0-1.0
    """
    normalized = _normalize_cell(cell)
    if not normalized:
        return 0.0
    
    # Numeric-only is definitely not description
    if _is_numeric_only(cell):
        return 0.0
    
    # Get max text length in row for normalization
    max_text_len = max((_text_length(c) for c in row_cells), default=0)
    if max_text_len == 0:
        return 0.0
    
    text_len = _text_length(cell)
    
    score = 0.0
    
    # Primary signal: text length
    if text_len > 0:
        text_ratio = text_len / max(max_text_len, 1)
        score += text_ratio * 0.8  # Up to 0.8 based on length
    
    # Word count signal
    words = normalized.split()
    if len(words) >= 3:
        score += 0.2
    elif len(words) == 2:
        score += 0.1
    
    # Penalty for currency symbols
    if _has_currency(cell):
        score -= 0.3
    
    # Penalty for mostly numbers
    numeric_chars = len(re.sub(r'[^0-9.,]', '', normalized))
    total_chars = len(normalized)
    if total_chars > 0 and numeric_chars / total_chars > 0.5:
        score -= 0.4
    
    return min(1.0, max(0.0, score))


def score_row_fields(
    row_cells: List[str],
    debug: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Score each cell in row for each field type.
    
    Returns scoring breakdown showing why each cell was ranked for each field.
    
    Args:
        row_cells: List of cell values
        debug: Enable debug output
    
    Returns:
        Dict with field names as keys, containing:
        - 'best_index': Index of best candidate
        - 'best_score': Score of best candidate
        - 'scores': List of scores for all cells
    """
    if not row_cells:
        return {}
    
    # Extract numeric values for all cells
    numeric_values = [_extract_numeric_value(cell) for cell in row_cells]
    
    results = {}
    
    # Score for quantity
    qty_scores = [
        score_quantity_candidate(cell, row_cells, numeric_values)
        for cell in row_cells
    ]
    qty_best_idx = max(range(len(qty_scores)), key=lambda i: qty_scores[i]) if qty_scores else -1
    results['quantity'] = {
        'best_index': qty_best_idx,
        'best_score': qty_scores[qty_best_idx] if qty_best_idx >= 0 else 0.0,
        'scores': qty_scores
    }
    
    # Score for unit_price
    price_scores = [
        score_unit_price_candidate(cell, row_cells, numeric_values)
        for cell in row_cells
    ]
    price_best_idx = max(range(len(price_scores)), key=lambda i: price_scores[i]) if price_scores else -1
    results['unit_price'] = {
        'best_index': price_best_idx,
        'best_score': price_scores[price_best_idx] if price_best_idx >= 0 else 0.0,
        'scores': price_scores
    }
    
    # Score for total_amount
    total_scores = [
        score_total_amount_candidate(cell, row_cells, numeric_values)
        for cell in row_cells
    ]
    total_best_idx = max(range(len(total_scores)), key=lambda i: total_scores[i]) if total_scores else -1
    results['total_amount'] = {
        'best_index': total_best_idx,
        'best_score': total_scores[total_best_idx] if total_best_idx >= 0 else 0.0,
        'scores': total_scores
    }
    
    # Score for description
    desc_scores = [
        score_description_candidate(cell, row_cells)
        for cell in row_cells
    ]
    desc_best_idx = max(range(len(desc_scores)), key=lambda i: desc_scores[i]) if desc_scores else -1
    results['description'] = {
        'best_index': desc_best_idx,
        'best_score': desc_scores[desc_best_idx] if desc_best_idx >= 0 else 0.0,
        'scores': desc_scores
    }
    
    if debug:
        print(f"\n[SCORE DEBUG] Row cells: {row_cells}")
        print(f"  Numeric values: {numeric_values}")
        for field, data in results.items():
            best_idx = data['best_index']
            best_score = data['best_score']
            best_cell = row_cells[best_idx] if best_idx >= 0 else 'NONE'
            print(f"  {field}: best_idx={best_idx} score={best_score:.3f} cell='{best_cell}'")
    
    return results


def resolve_field_conflicts(
    scoring_results: Dict[str, Dict[str, Any]],
    row_cells: List[str],
    debug: bool = False
) -> Dict[str, str]:
    """
    Resolve conflicts where multiple fields map to same column.
    
    Priority: description > quantity > unit_price > total_amount
    
    Args:
        scoring_results: Output from score_row_fields()
        row_cells: Original row cells
        debug: Enable debug output
    
    Returns:
        Dict mapping field name to cell value
    """
    # Build priority order
    field_order = ['description', 'quantity', 'unit_price', 'total_amount']
    
    # Get best index for each field
    field_indices = {
        field: scoring_results[field]['best_index']
        for field in field_order
    }
    
    used_indices = set()
    final_mapping = {}
    
    for field in field_order:
        best_idx = field_indices[field]
        
        # If best index not used, assign it
        if best_idx >= 0 and best_idx not in used_indices:
            final_mapping[field] = row_cells[best_idx]
            used_indices.add(best_idx)
            if debug:
                print(f"  {field} -> column {best_idx} (score {scoring_results[field]['best_score']:.3f})")
        else:
            # Find alternative
            scores = scoring_results[field]['scores']
            alternative_idx = -1
            for idx in sorted(range(len(scores)), key=lambda i: scores[i], reverse=True):
                if idx not in used_indices:
                    alternative_idx = idx
                    break
            
            if alternative_idx >= 0:
                final_mapping[field] = row_cells[alternative_idx]
                used_indices.add(alternative_idx)
                if debug:
                    print(f"  {field} -> column {alternative_idx} (alternative, score {scores[alternative_idx]:.3f})")
            else:
                final_mapping[field] = ''
                if debug:
                    print(f"  {field} -> NONE (no available column)")
    
    return final_mapping


def extract_currency_from_row(row_cells: List[str], document_currency: str = '') -> str:
    """Extract currency from row cells or fall back to document currency."""
    for cell in row_cells:
        upper_cell = cell.upper()
        for symbol in CURRENCY_SYMBOLS:
            if symbol in cell:
                return symbol
        for code in CURRENCY_CODES:
            if code in upper_cell:
                return code
    
    return document_currency


def score_and_extract_fields(
    row_cells: List[str],
    document_context: Dict[str, Any],
    debug: bool = False
) -> Dict[str, Any]:
    """
    Score all fields in row and extract best values.
    
    Final normalization layer - validates all field values against expected types.
    
    Args:
        row_cells: List of cell values from table row
        document_context: Document-level context (supplier, currency, etc.)
        debug: Enable debug output
    
    Returns:
        Dict with extracted and validated fields:
        - description: Longest text, non-numeric
        - quantity: Smallest numeric value, integer
        - unit_price: Mid-range numeric value with decimal
        - total_amount: Largest numeric value
        - currency: Document or row-detected currency
    """
    # Score all fields
    scoring_results = score_row_fields(row_cells, debug=debug)
    
    # Resolve conflicts
    field_values = resolve_field_conflicts(scoring_results, row_cells, debug=debug)
    
    # Validate and normalize results
    result = {
        'description': _normalize_cell(field_values.get('description', '')),
        'quantity': _normalize_cell(field_values.get('quantity', '')),
        'unit_price': _normalize_cell(field_values.get('unit_price', '')),
        'total_amount': _normalize_cell(field_values.get('total_amount', '')),
    }
    
    # Validation rules
    
    # Description must not be numeric-only
    if result['description'] and _is_numeric_only(result['description']):
        result['description'] = ''
    
    # Quantity must be numeric
    if result['quantity']:
        qty_val = _extract_numeric_value(result['quantity'])
        if qty_val > 0:
            result['quantity'] = str(int(qty_val))
        else:
            result['quantity'] = ''
    
    # Unit price must be numeric
    if result['unit_price']:
        price_val = _extract_numeric_value(result['unit_price'])
        if price_val > 0:
            result['unit_price'] = str(price_val)
        else:
            result['unit_price'] = ''
    
    # Total amount must be numeric
    if result['total_amount']:
        total_val = _extract_numeric_value(result['total_amount'])
        if total_val > 0:
            result['total_amount'] = str(total_val)
        else:
            result['total_amount'] = ''
    
    # Ensure quantity and unit_price are different
    if result['quantity'] and result['unit_price']:
        qty = safe_float(result['quantity'])
        price = safe_float(result['unit_price'])
        if abs(qty - price) < 0.01:  # Same value
            if qty < price:
                result['unit_price'] = ''
            else:
                result['quantity'] = ''
    
    # Total amount should be >= unit_price (if both present)
    if result['total_amount'] and result['unit_price']:
        total = safe_float(result['total_amount'])
        price = safe_float(result['unit_price'])
        if total > 0 and price > 0 and total < price:
            # Swap them
            result['total_amount'], result['unit_price'] = result['unit_price'], result['total_amount']
    
    # Extract currency
    row_currency = extract_currency_from_row(row_cells, document_context.get('currency', ''))
    result['currency'] = row_currency or document_context.get('currency', '')
    
    if debug:
        print(f"  Final extracted: {result}")
    
    return result
