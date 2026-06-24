"""
Spanish Procurement Document Regex Patterns
============================================

Regex patterns to extract Item ID, Description, Quantity, and Unit
from Spanish procurement documents.
"""

import re

class SpanishProcurementPatterns:
    """
    Patterns for extracting procurement data from Spanish documents.
    Common Spanish procurement formats include:
    - Government procurement (compras públicas)
    - Budget documents
    - Purchase orders (órdenes de compra)
    - Invoices (facturas)
    """
    
    # ==================== ITEM ID PATTERNS ====================
    # Pattern 1: Alphanumeric code (e.g., "REF-001", "ART-2024-001")
    ITEM_ID_ALPHANUMERIC = r'(?:REF|ART|COD|CÓDIGO|ID|Código|Artículo)[:\s-]+([A-Z0-9\-]{3,20})'
    
    # Pattern 2: Just numeric ID (e.g., "001", "10234")
    ITEM_ID_NUMERIC = r'(?:^|\n)[\s]*(\d{3,10})[\s]+(?=[A-Z]|$)'
    
    # Pattern 3: Numeric with format pattern (e.g., "2024-0001-A")
    ITEM_ID_FORMATTED = r'(\d{4}[-/]\d{4}[-/][A-Z0-9])'
    
    # Pattern 4: SKU format (e.g., "SKU-001-XX")
    ITEM_ID_SKU = r'(?:SKU|EAN|UPC)[:\s-]+([A-Z0-9\-]{5,25})'
    
    
    # ==================== DESCRIPTION PATTERNS ====================
    # Pattern 1: Description after item ID (flexible)
    # Captures text that follows numeric ID up to quantity
    DESCRIPTION_AFTER_ID = r'(?:^|[\n])[\s]*\d+[\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.]+?)(?=[\s]*\d+(?:\s*(?:u|un|unid|Ud|pcs|kg|l|ml|m|m²|m³))?[\s]*$)'
    
    # Pattern 2: Description with bullet or numbering
    DESCRIPTION_BULLETED = r'(?:[-•*]|\d+\.|o\))\s+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)(?:\s+\d+(?:\s+(?:u|un|unid|Ud|kg|l|m))?)?$'
    
    # Pattern 3: Description between "Descripción" label and quantity
    DESCRIPTION_LABELED = r'(?:Descripción|DESCRIPCIÓN|Concepto|CONCEPTO)[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)(?:\n|$|[0-9])'
    
    # Pattern 4: Clean extraction (remove extra whitespace)
    DESCRIPTION_CLEANUP = r'\s+'
    
    
    # ==================== QUANTITY PATTERNS ====================
    # Pattern 1: Quantity with decimal separator (both . and ,)
    QUANTITY_DECIMAL = r'(?:^|[\s])((?:\d+[.,]\d+|\d+))(?:\s*(?:u|un|unid|Ud|pcs|kg|l|ml|m|m²|m³|ud\.|uds\.))?'
    
    # Pattern 2: Quantity in parentheses or brackets
    QUANTITY_BRACKETED = r'[(\[](\d+(?:[.,]\d+)?)[)\]]'
    
    # Pattern 3: Quantity with "Cantidad" or "Qty" label
    QUANTITY_LABELED = r'(?:Cantidad|CANTIDAD|Qty|QTY|Cant\.)[:\s]+(\d+(?:[.,]\d+)?)'
    
    # Pattern 4: Quantity before unit (more specific)
    QUANTITY_BEFORE_UNIT = r'(\d+(?:[.,]\d+)?)\s+(?:u|un|unid|Ud|pcs|pz|kg|g|l|ml|m|m²|m³|ud\.|uds\.)'
    
    
    # ==================== UNIT PATTERNS ====================
    # Spanish and common international units
    UNIT_PATTERNS = {
        'piece': r'(?:u|un|unidad|unidades|pz|pza|piezas|ud|uds|u\.)',
        'weight': r'(?:kg|g|mg|gr|gramo|kilogramo|tonelada|ton|t)',
        'volume': r'(?:l|ml|litro|mililitro|m³|litros)',
        'length': r'(?:m|cm|mm|metro|centímetro|milímetro|km)',
        'area': r'(?:m²|cm²|hectárea|ha)',
        'box': r'(?:caja|cajas|cj|cx)',
        'pack': r'(?:pack|paquete|lote)',
        'roll': r'(?:rollo|rollos)',
        'set': r'(?:juego|set|kit)',
        'hour': r'(?:hora|horas|h)',
        'day': r'(?:día|días)',
        'service': r'(?:servicio|servicios)',
    }
    
    # Combined unit pattern - matches any unit
    UNIT_COMBINED = r'(?:u|un|unidad|unidades|pz|pza|piezas|ud|uds|u\.|kg|g|mg|gr|gramo|kilogramo|tonelada|ton|t|l|ml|litro|mililitro|m³|litros|m|cm|mm|metro|centímetro|milímetro|km|m²|cm²|hectárea|ha|caja|cajas|cj|cx|pack|paquete|lote|rollo|rollos|juego|set|kit|hora|horas|h|día|días|servicio|servicios)'
    
    # Unit immediately after quantity
    UNIT_AFTER_QUANTITY = r'\d+(?:[.,]\d+)?\s+(' + UNIT_COMBINED + r')'
    
    
    # ==================== COMPLETE LINE PATTERNS ====================
    # Pattern to extract complete line: ID | Description | Quantity | Unit
    # Format: ID | DESCRIPTION | QTY | UNIT
    COMPLETE_LINE_PIPE = r'(\d+)\s*\|\s*([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)\s*\|\s*(\d+(?:[.,]\d+)?)\s*\|\s*(' + UNIT_COMBINED + r')'
    
    # Pattern for tab-separated format
    COMPLETE_LINE_TAB = r'(\d+)\t+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)\t+(\d+(?:[.,]\d+)?)\t+(' + UNIT_COMBINED + r')'
    
    # Pattern for space-separated format (most common in scanned documents)
    COMPLETE_LINE_SPACE = r'^(\d{1,5})\s+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]{5,100}?)\s+(\d+(?:[.,]\d+)?)\s+(' + UNIT_COMBINED + r')$'
    
    # Pattern for line with optional item code
    COMPLETE_LINE_WITH_CODE = r'(?:REF|ART|COD)[:\s-]+([A-Z0-9\-]+)\s+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]+?)\s+(\d+(?:[.,]\d+)?)\s+(' + UNIT_COMBINED + r')'


class ProcurementExtractor:
    """Utility class to extract procurement data using the patterns."""
    
    def __init__(self):
        self.patterns = SpanishProcurementPatterns()
    
    def extract_quantity(self, text):
        """Extract quantity and convert to float."""
        match = re.search(self.patterns.QUANTITY_LABELED, text, re.IGNORECASE)
        if match:
            qty_str = match.group(1).replace(',', '.')
            return float(qty_str)
        return None
    
    def extract_unit(self, text):
        """Extract unit of measurement."""
        match = re.search(self.patterns.UNIT_AFTER_QUANTITY, text, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return None
    
    def extract_item_id(self, text):
        """Extract item ID from text."""
        # Try different patterns
        for pattern in [
            self.patterns.ITEM_ID_ALPHANUMERIC,
            self.patterns.ITEM_ID_SKU,
            self.patterns.ITEM_ID_FORMATTED,
            self.patterns.ITEM_ID_NUMERIC,
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def extract_complete_items(self, text):
        """
        Extract complete item information from text.
        Returns list of dicts with item_id, description, quantity, unit.
        """
        items = []
        
        # Split by lines and process
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try different line patterns
            patterns_to_try = [
                (self.patterns.COMPLETE_LINE_PIPE, ['id', 'description', 'quantity', 'unit']),
                (self.patterns.COMPLETE_LINE_TAB, ['id', 'description', 'quantity', 'unit']),
                (self.patterns.COMPLETE_LINE_SPACE, ['id', 'description', 'quantity', 'unit']),
                (self.patterns.COMPLETE_LINE_WITH_CODE, ['id', 'description', 'quantity', 'unit']),
            ]
            
            for pattern, field_names in patterns_to_try:
                match = re.search(pattern, line, re.MULTILINE | re.IGNORECASE)
                if match:
                    item = {}
                    for i, field_name in enumerate(field_names):
                        value = match.group(i + 1)
                        if field_name == 'quantity':
                            value = float(value.replace(',', '.'))
                        elif field_name == 'description':
                            value = ' '.join(value.split())  # Normalize whitespace
                        item[field_name] = value
                    items.append(item)
                    break
        
        return items


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    # Example 1: Spanish procurement document text
    example_text = """
    1   Papel bond A4 80 gramos    500   u
    2   Tóner HP LaserJet negro    10    Ud
    REF-2024-003   Lápices de color variados    24    pz
    """
    
    extractor = ProcurementExtractor()
    
    print("=" * 60)
    print("SPANISH PROCUREMENT DOCUMENT EXTRACTOR")
    print("=" * 60)
    
    print("\nExample extraction:")
    items = extractor.extract_complete_items(example_text)
    
    for i, item in enumerate(items, 1):
        print(f"\nItem {i}:")
        for key, value in item.items():
            print(f"  {key}: {value}")
    
    # Example 2: Individual pattern testing
    print("\n" + "=" * 60)
    print("PATTERN TESTING")
    print("=" * 60)
    
    test_line = "REF-001 Papel bond A4 80 gramos 500 u"
    print(f"\nTest line: {test_line}")
    
    item_id = extractor.extract_item_id(test_line)
    print(f"Item ID found: {item_id}")
    
    quantity = extractor.extract_quantity(test_line)
    print(f"Quantity found: {quantity}")
    
    unit = extractor.extract_unit(test_line)
    print(f"Unit found: {unit}")
