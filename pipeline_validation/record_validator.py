import re
from typing import Dict, Any, List

from pipeline_extraction.utils.safe_parsing import safe_float

HEADER_LIKE_KEYWORDS = [
    'ITEM', 'DESCRIPTION', 'DESCRIPCION', 'QTY', 'QUANTITY', 'UNITS', 'UNIT PRICE',
    'PRICE', 'TOTAL', 'AMOUNT', 'CURRENCY', 'SUBTOTAL', 'LINE', 'ITEM DESCRIPTION'
]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ''
    return ' '.join(str(value).strip().split())


def _is_numeric_string(value: str) -> bool:
    normalized = re.sub(r'[^0-9]', '', value)
    return bool(normalized) and normalized == value.replace(' ', '')


def _is_header_like(value: str) -> bool:
    if not value:
        return False
    text = _normalize_text(value).upper()
    if text in HEADER_LIKE_KEYWORDS:
        return True
    if any(text.startswith(keyword + ' ') for keyword in HEADER_LIKE_KEYWORDS):
        return True
    if text.isupper() and len(text.split()) <= 3 and any(keyword in text for keyword in HEADER_LIKE_KEYWORDS):
        return True
    return False


def _is_simple_quantity(value: str) -> bool:
    candidate = _normalize_text(value)
    if not candidate:
        return False
    if re.fullmatch(r'0*\d+', candidate) is None:
        return False
    numeric = safe_float(candidate)
    return numeric > 0 and float(int(numeric)) == numeric


def validate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a single extracted record according to procurement rules."""
    description = _normalize_text(record.get('item_description', ''))
    quantity = _normalize_text(record.get('quantity', ''))
    unit_price = _normalize_text(record.get('unit_price', ''))
    total_amount = _normalize_text(record.get('total_amount', ''))

    errors: List[str] = []
    warnings: List[str] = []

    # Description validation
    if description:
        if _is_numeric_string(description):
            errors.append('Description is numeric-only.')
        elif _is_header_like(description):
            errors.append('Description appears header-like.')

    # Quantity validation
    if quantity:
        if not _is_simple_quantity(quantity):
            errors.append('Quantity is not a simple integer like 1 or 01.')

    # Price/total consistency
    if unit_price and total_amount:
        price_value = safe_float(unit_price)
        total_value = safe_float(total_amount)
        if price_value > 0 and total_value > 0 and price_value > total_value:
            errors.append('Unit price is greater than total amount.')

    classification = 'VALID' if not errors else 'INVALID'

    return {
        'classification': classification,
        'errors': errors,
        'warnings': warnings,
        'description': description,
        'quantity': quantity,
        'unit_price': unit_price,
        'total_amount': total_amount
    }
