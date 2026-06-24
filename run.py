import pdfplumber
import pandas as pd
import re
from pathlib import Path

# Regex patterns for Spanish procurement documents
PATTERNS = {
    'item_code': r'(?:S\d{6,12}|[A-Z]{3}\d{3,10})',
    'quantity_num': r'(\d+(?:[.,]\d{1,3})*)',
    'unit': r'(?:u|un|unidad|unidades|pz|pza|piezas|ud|uds|u\.|kg|g|mg|gramo|tonelada|ton|t|l|ml|litro|m³|m|cm|mm|km|m²|cm²|hectárea|ha|caja|cajas|pack|paquete|lote|rollo|juego|set|kit|hora|horas|h|día|días|servicio|servicios|in|inch)',
}


def extract_from_tables(page):
    """Try to extract items from table structures in page."""
    items = []
    tables = page.extract_tables()
    
    if not tables:
        return items
    
    for table in tables:
        if not table or len(table) < 2:
            continue
        
        # Try to identify header row and data rows
        for row_idx, row in enumerate(table):
            if not row:
                continue
            
            # Convert row to clean strings
            row_text = [str(cell).strip() if cell else '' for cell in row]
            row_str = ' | '.join(row_text)
            
            # Look for lines with both description-like text and numbers
            has_qty = any(re.search(r'\d+(?:[.,]\d+)?', cell) for cell in row_text)
            has_description = any(len(cell) > 5 and sum(c.isalpha() for c in cell) > 3 for cell in row_text)
            
            if has_qty and has_description:
                items.append({
                    'raw_row': row_text,
                    'row_text': row_str,
                    'cols_count': len(row_text)
                })
    
    return items


def parse_table_item(item_dict):
    """Parse a table row into procurement item fields."""
    row = item_dict['raw_row']
    
    # Try to identify columns
    item_id = ''
    description = ''
    quantity = None
    unit = ''
    
    # Look through columns for different components
    for i, cell in enumerate(row):
        if not cell or len(cell) < 2:
            continue
        
        # Check for item code (usually starts with letter or specific pattern)
        if re.match(r'^[A-Z]\d{6,}', cell) or re.match(r'^[A-Z]{3}\d+', cell):
            if not item_id:
                item_id = cell
        
        # Check for quantity
        qty_match = re.search(r'^(\d+(?:[.,]\d+)?)(?:\s|$)', cell)
        if qty_match and not quantity:
            quantity = float(qty_match.group(1).replace(',', '.'))
        
        # Check for unit
        unit_match = re.search(PATTERNS['unit'], cell, re.IGNORECASE)
        if unit_match and not unit:
            unit = unit_match.group(0)
        
        # Long text is likely description
        if len(cell) > 10 and sum(c.isalpha() for c in cell) > 5:
            if not description:
                description = cell
    
    return {
        'item_id': item_id,
        'description': description,
        'quantity': quantity,
        'unit': unit
    }


def extract_item_sections(text):
    """
    Extract sections that look like procurement items.
    Looks for patterns like numbered items with descriptions and quantities.
    """
    items = []
    
    # Split by common item delimiters
    # Look for patterns: number + description + quantity + unit
    pattern = r'(\d{1,4})\s+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\(\)\.\-]{10,200}?)\s+(\d+(?:[.,]\d+)?)\s+(' + PATTERNS['unit'] + r')'
    
    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
    for match in matches:
        item_id, description, quantity, unit = match.groups()
        description = ' '.join(description.split())
        
        if len(description) > 8:
            items.append({
                'item_id': item_id,
                'description': description,
                'quantity': float(quantity.replace(',', '.')),
                'unit': unit.lower()
            })
    
    return items


def extract_specifications_from_context(text, line_start):
    """Extract specification details from context around a line."""
    specs = []
    
    # Look for specification keywords
    spec_keywords = ['especificación', 'característica', 'dimensión', 'material', 'voltaje', 
                     'capacidad', 'potencia', 'marca', 'modelo', 'color', 'grosor', 'peso',
                     'rendimiento', 'altura', 'ancho', 'profundidad', 'diámetro']
    
    for keyword in spec_keywords:
        pattern = rf'{keyword}[:\s]+([^\n.]+)'
        match = re.search(pattern, text[line_start:line_start+500], re.IGNORECASE)
        if match:
            value = match.group(1).strip()[:80]
            if value and len(value) > 2:
                specs.append(f"{keyword}: {value}")
    
    return ' | '.join(specs[:3]) if specs else ''


def extract_procurement_items_from_pdf(pdf_path):
    """Extract procurement items from PDF with mixed strategies."""
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        pdf_name = Path(pdf_path).name
        
        for page_num, page in enumerate(pdf.pages, 1):
            # Strategy 1: Extract from tables (most reliable)
            table_items = extract_from_tables(page)
            for item_dict in table_items:
                parsed = parse_table_item(item_dict)
                
                if parsed['description'] and parsed['quantity'] is not None:
                    specs = extract_specifications_from_context(
                        item_dict['row_text'], 0
                    )
                    
                    items.append({
                        'pdf_name': pdf_name,
                        'item_id': parsed['item_id'],
                        'original_description': parsed['description'][:200],
                        'quantity': parsed['quantity'],
                        'unit': parsed['unit'],
                        'technical_specifications': specs
                    })
            
            # Strategy 2: Extract from formatted text (for documents without tables)
            text = page.extract_text()
            if text:
                text_items = extract_item_sections(text)
                for item in text_items:
                    # Only add if not already captured from tables
                    already_exists = any(
                        i['original_description'] == item['description']
                        for i in items
                    )
                    
                    if not already_exists:
                        specs = extract_specifications_from_context(
                            text, text.find(item['description'])
                        )
                        items.append({
                            'pdf_name': pdf_name,
                            'item_id': '',
                            'original_description': item['description'],
                            'quantity': item['quantity'],
                            'unit': item['unit'],
                            'technical_specifications': specs
                        })
    
    return items


def extract_from_pdfs(pdf_folder='pdfs'):
    """Extract procurement data from all PDFs in folder."""
    
    all_items = []
    pdf_folder = Path(pdf_folder)
    
    print(f"Reading PDFs from: {pdf_folder}")
    print("=" * 80)
    
    for pdf_file in sorted(pdf_folder.glob("*.pdf")):
        print(f"Processing: {pdf_file.name}")
        
        try:
            items = extract_procurement_items_from_pdf(pdf_file)
            all_items.extend(items)
            print(f"  ✓ Extracted {len(items)} items")
        
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    return all_items


# Main execution
if __name__ == "__main__":
    print("Spanish Procurement Document Extractor (Enhanced v2)")
    print("=" * 80)
    print()
    
    # Extract procurement items from all PDFs
    items = extract_from_pdfs('pdfs')
    
    # Create DataFrame
    df = pd.DataFrame(items)
    
    print()
    print("=" * 80)
    print(f"EXTRACTION SUMMARY")
    print("=" * 80)
    print(f"Total items extracted: {len(df)}")
    if len(df) > 0:
        print(f"Total PDFs processed: {df['pdf_name'].nunique()}")
        print(f"Items with quantity > 0: {len(df[df['quantity'] > 0])}")
        print(f"Items with item_id: {len(df[df['item_id'] != ''])}")
        print(f"Items with specifications: {len(df[df['technical_specifications'] != ''])}")
    print()
    
    # Display first 10 rows
    print("FIRST 10 ROWS:")
    print("=" * 80)
    if len(df) > 0:
        # Display with better formatting
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_colwidth', None)
        pd.set_option('display.width', None)
        print(df.head(10).to_string(index=False))
    else:
        print("No items extracted")
    
    print()
    print("=" * 80)
    
    # Show data types and summary statistics
    if len(df) > 0:
        print("\nDataFrame Info:")
        print(df.info())
        
        print("\nQuantity Statistics:")
        print(df[['quantity']].describe())
        
        print("\nItems by PDF:")
        print(df.groupby('pdf_name').size())
        
        # Show sample items with all details
        print("\n" + "=" * 80)
        print("DETAILED SAMPLE ITEMS:")
        print("=" * 80)
        for idx, row in df.head(5).iterrows():
            print(f"\n[Item {idx + 1}]")
            print(f"  PDF File: {row['pdf_name']}")
            print(f"  Item ID: {row['item_id'] if row['item_id'] else 'N/A'}")
            print(f"  Description: {row['original_description']}")
            print(f"  Quantity: {row['quantity']}")
            print(f"  Unit: {row['unit']}")
            if row['technical_specifications']:
                print(f"  Specs: {row['technical_specifications']}")
        
        # Export to CSV and Excel
        print("\n" + "=" * 80)
        print("EXPORTING DATA")
        print("=" * 80)
        
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        
        csv_file = output_dir / 'raw_extracted.csv'
        xlsx_file = output_dir / 'raw_extracted.xlsx'
        
        # Save to CSV
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"✓ Saved to: {csv_file}")
        
        # Save to Excel
        df.to_excel(xlsx_file, index=False, sheet_name='Procurement Items')
        print(f"✓ Saved to: {xlsx_file}")
        
        print(f"\nTotal records exported: {len(df)}")
        
        print("\nSample with specifications:")
        df_with_specs = df[df['technical_specifications'] != '']
        if len(df_with_specs) > 0:
            print(df_with_specs[['pdf_name', 'original_description', 'technical_specifications']].head(5).to_string(index=False))
        else:
            print("No items with specifications found")