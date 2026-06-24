import os
from typing import Union, Optional

# Debug mode: enable debug prints if DEBUG_PARSING env var is set
DEBUG_MODE = os.getenv('DEBUG_PARSING', '').lower() in ('1', 'true', 'yes')


def safe_float(value: Union[str, int, float, None]) -> float:
    """
    Safely convert a value to float, handling corrupted OCR data and various formats.
    
    Accepts string, int, float, or None. Removes all non-numeric characters except
    "." and "," (decimal/thousands separators). Detects and rejects corrupted values
    with multiple separators. Never raises exceptions; returns 0.0 on failure.
    
    Examples:
        >>> safe_float("120.50")
        120.5
        >>> safe_float("45,000.00")
        45000.0
        >>> safe_float("$ 120.50")
        120.5
        >>> safe_float("1.234.567,89")  # EU format
        1234567.89
        >>> safe_float("112.202202.300300.3.2.1")  # Corrupted
        0.0
        >>> safe_float(None)
        0.0
    
    Args:
        value: string, int, float, or None to convert
    
    Returns:
        float: Converted value, or 0.0 if parsing fails or value is corrupted
    """
    # Handle None
    if value is None:
        return 0.0
    
    # If already a numeric type, try direct conversion
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    # Convert to string and strip whitespace
    text = str(value).strip()
    if not text:
        return 0.0
    
    # Keep only digits, dots, and commas
    cleaned = ''.join(c for c in text if c.isdigit() or c in '.,')
    
    if not cleaned or cleaned in '.,':
        return 0.0
    
    # Count separators
    dot_count = cleaned.count('.')
    comma_count = cleaned.count(',')
    total_separators = dot_count + comma_count
    
    # Detect corruption: more than 2 separators indicates malformed data
    # Valid formats: "120.50" (1), "45,000.00" (2), "1.234.567,89" (2)
    # Corrupted: "112.202202.300300.3.2.1" (many)
    if total_separators > 2:
        if DEBUG_MODE:
            print(f"[safe_float] CORRUPTED (too many separators): original='{value}' cleaned='{cleaned}'")
        return 0.0
    
    try:
        if total_separators == 0:
            # No separators - just digits
            return float(cleaned)
        
        if total_separators == 1:
            # Single separator - could be decimal or thousands
            sep_index = max(cleaned.find('.'), cleaned.find(','))
            digits_after = len(cleaned) - sep_index - 1
            
            if digits_after <= 2:
                # Likely a decimal separator (0-2 digits after = decimal)
                normalized = cleaned.replace(',', '.') if ',' in cleaned else cleaned
                return float(normalized)
            else:
                # Likely a thousands separator (more digits after = thousands)
                normalized = cleaned.replace(',', '').replace('.', '')
                return float(normalized)
        
        if total_separators == 2:
            # Two separators: last one is decimal, first is thousands
            last_dot_pos = cleaned.rfind('.')
            last_comma_pos = cleaned.rfind(',')
            last_sep_pos = max(last_dot_pos, last_comma_pos)
            
            # Determine which is the decimal separator (the last one)
            decimal_sep = '.' if last_dot_pos > last_comma_pos else ','
            thousands_sep = ',' if decimal_sep == '.' else '.'
            
            # Normalize: remove thousands sep, convert decimal sep to "."
            normalized = cleaned.replace(thousands_sep, '').replace(decimal_sep, '.')
            return float(normalized)
        
        # Fallback (shouldn't reach here)
        return float(cleaned.replace(',', '').replace('.', ''))
    
    except (ValueError, TypeError) as e:
        if DEBUG_MODE:
            print(f"[safe_float] ERROR: original='{value}' cleaned='{cleaned}' error={e}")
        return 0.0
