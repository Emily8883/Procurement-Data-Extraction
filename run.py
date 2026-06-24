import json
import sys
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


def extract_from_pdfs(pdf_folder='pdfs', debug: bool = False):
    """Extract procurement data from all PDFs in folder."""
    
    all_items = []
    pdf_folder = Path(pdf_folder)
    
    print(f"Reading PDFs from: {pdf_folder}")
    print("=" * 80)
    
    for pdf_file in sorted(pdf_folder.glob("*.pdf")):
        print(f"Processing: {pdf_file.name}")
        
        try:
            items = extract_procurement_data_hybrid(str(pdf_file), debug=debug)
            all_items.extend(items)
            print(f"  ✓ Extracted {len(items)} items")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            print("  PDF failed but pipeline continues")
            continue
    
    return all_items


# New pipeline orchestration: extraction -> normalization -> matching -> export
from supplier_matching import SupplierMatcher
from price_estimation import PriceEstimator
from pipeline_extraction.hybrid_procurement_extractor import extract_procurement_data_hybrid
from pipeline_validation.data_quality_validator import validate_pipeline_output
from pipeline_validation.extraction_diagnostics import generate_extraction_diagnostics


def normalize_item(raw_item: dict) -> dict:
    """Normalize a raw extracted item into the final schema."""
    # Final schema fields:
    # document_name, line_item_id, item_id, original_description, normalized_description,
    # quantity, unit, unit_price, total_price, currency, technical_specifications,
    # supplier_match_id, supplier_name, supplier_confidence, supplier_match_source,
    # price_confidence, extraction_confidence

    normalized = {
        'document_name': raw_item.get('pdf_name', '') or raw_item.get('document_name', ''),
        'line_item_id': raw_item.get('item_id', '') or '',
        'item_id': raw_item.get('item_id', '') or '',
        'original_description': raw_item.get('item_description', '') or raw_item.get('original_description', '')[:1000],
        'normalized_description': ' '.join((raw_item.get('item_description', '') or raw_item.get('original_description', '')).split())[:1000],
        'quantity': raw_item.get('quantity') if raw_item.get('quantity') is not None else 0,
        'unit': raw_item.get('unit', ''),
        'unit_price': raw_item.get('unit_price'),
        'total_price': raw_item.get('total_amount') or raw_item.get('total_price'),
        'total_amount': raw_item.get('total_amount'),
        'invoice_or_po_number': raw_item.get('invoice_or_po_number', ''),
        'currency': raw_item.get('currency'),
        'technical_specifications': raw_item.get('technical_specifications', ''),
        'supplier_match_id': None,
        'supplier_name': raw_item.get('supplier_name'),
        'supplier_confidence': 0,
        'supplier_match_source': None,
        'price_confidence': 0,
        'extraction_confidence': raw_item.get('extraction_confidence', None) if isinstance(raw_item.get('extraction_confidence', None), (int, float)) else None,
        'source_page': raw_item.get('source_page')
    }

    return normalized


def export_results(final_items: list, output_dir: Path = Path('output')) -> None:
    """Export final items to JSON and Excel."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / 'output.json'
    xlsx_path = output_dir / 'output.xlsx'

    # Write JSON
    import json
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(final_items, f, ensure_ascii=False, indent=2)

    # Write Excel via pandas
    df_final = pd.DataFrame(final_items)
    # Ensure consistent column order for readability
    cols = [
        'document_name', 'line_item_id', 'item_id', 'original_description', 'normalized_description',
        'quantity', 'unit', 'unit_price', 'total_price', 'currency', 'technical_specifications',
        'supplier_match_id', 'supplier_name', 'supplier_confidence', 'supplier_match_source',
        'price_confidence', 'extraction_confidence'
    ]
    # Keep only available cols
    cols = [c for c in cols if c in df_final.columns]
    df_final = df_final[cols]
    df_final.to_excel(xlsx_path, index=False, sheet_name='Procurement')

    print(f"✓ Exported JSON: {json_path}")
    print(f"✓ Exported Excel: {xlsx_path}")


def run_pipeline(pdf_folder: str = 'pdfs', debug: bool = False) -> list:
    print('\nStarting full extraction pipeline')
    print('=' * 60)

    # 1) Extraction (existing extractor)
    extracted = extract_from_pdfs(pdf_folder, debug=debug)
    print(f"Extracted raw items: {len(extracted)}")

    if debug:
        print('\nDEBUG MODE: Extraction output per PDF')
        for pdf_file in sorted(Path(pdf_folder).glob('*.pdf')):
            records = extract_procurement_data_hybrid(str(pdf_file), debug=True)
            print(f"\nPDF: {pdf_file.name}")
            print(f"  Total extracted records: {len(records)}")
            for sample in records[:2]:
                print('  Sample record:')
                print(json.dumps(sample, ensure_ascii=False, indent=2))
            print('  ...')

            diagnostics = generate_extraction_diagnostics(str(pdf_file), records)
            print('  Diagnostic summary:')
            print(f"    issue: {diagnostics['issue']}")
            print(f"    missing supplier_name: {diagnostics['missing_supplier_name_pct']}%")
            print(f"    missing unit_price: {diagnostics['missing_unit_price_pct']}%")
            print(f"    missing currency: {diagnostics['missing_currency_pct']}%")
            print(f"    missing invoice_or_po_number: {diagnostics['missing_invoice_or_po_number_pct']}%")
            print(f"    tables found: {diagnostics['tables_found']} (pages {diagnostics['pages_with_tables']}/{diagnostics['total_pages']})")

    # 2) Normalization
    normalized = [normalize_item(it) for it in extracted]
    print(f"Normalized items: {len(normalized)}")

    # 3) Supplier matching (placeholder interface)
    matcher = SupplierMatcher()
    priceer = PriceEstimator()

    final_items = []
    for item in normalized:
        # Match supplier (placeholder)
        match = matcher.match_supplier(item['normalized_description'])
        if match:
            item['supplier_match_id'] = match.get('match_id')
            item['supplier_name'] = match.get('name')
            item['supplier_confidence'] = match.get('confidence', 0)
            item['supplier_match_source'] = match.get('source')

        # Price estimation placeholder
        price_est = priceer.estimate_price(item['normalized_description'])
        if price_est:
            item['unit_price'] = price_est.get('unit_price')
            item['total_price'] = price_est.get('total_price')
            item['currency'] = price_est.get('currency')
            item['price_confidence'] = price_est.get('confidence', 0)

        final_items.append(item)

    # 4) Export
    export_results(final_items, output_dir=Path('output'))

    # 5) Data quality validation
    validation_report = validate_pipeline_output(final_items)
    print('\nData Quality Validation Summary:')
    print(f"  Total records: {validation_report['total_records']}")
    print(f"  Valid records: {validation_report['valid_records']}")
    print(f"  Partial records: {validation_report['partial_records']}")
    print(f"  Invalid records: {validation_report['invalid_records']}")
    print(f"  Completeness score: {validation_report['completeness_score']:.2f}")
    print('  Missing fields summary:')
    for field, count in validation_report['missing_fields_summary'].items():
        print(f"    - {field}: {count}")

    return final_items


if __name__ == '__main__':
    debug_mode = '--debug' in sys.argv or '-d' in sys.argv
    final = run_pipeline('pdfs', debug=debug_mode)
    print('\nPipeline complete. Items processed:', len(final))