"""
Integration Example: Using Spanish Procurement Regex with PDF Extraction

This script shows how to integrate the Spanish procurement regex patterns
with your existing PDF extraction setup (run.py).
"""

import pdfplumber
import re
from pathlib import Path
import json
from spanish_procurement_regex import ProcurementExtractor

# Initialize extractor
extractor = ProcurementExtractor()

def extract_procurement_data_from_pdf(pdf_path):
    """Extract procurement line items from a PDF file."""
    
    items = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Extract text from page
            text = page.extract_text()
            
            if not text:
                # Try with layout if plain extraction fails
                text = page.extract_text(layout=True)
            
            if text:
                # Try to extract items from this page
                page_items = extractor.extract_complete_items(text)
                
                for item in page_items:
                    item['page'] = page_num
                    items.append(item)
    
    return items


def extract_from_multiple_pdfs(pdf_folder):
    """Extract procurement data from all PDFs in a folder."""
    
    all_data = {}
    pdf_folder = Path(pdf_folder)
    
    for pdf_file in pdf_folder.glob("*.pdf"):
        print(f"Processing: {pdf_file.name}")
        
        try:
            items = extract_procurement_data_from_pdf(pdf_file)
            all_data[pdf_file.name] = {
                'total_items': len(items),
                'items': items
            }
            print(f"  ✓ Extracted {len(items)} items")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    return all_data


def save_extraction_results(data, output_file='output/procurement_extraction.json'):
    """Save extraction results to JSON file."""
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Results saved to: {output_file}")


def generate_summary_report(data):
    """Generate a summary report of extracted data."""
    
    total_pdfs = len(data)
    total_items = sum(doc['total_items'] for doc in data.values())
    
    print("\n" + "=" * 60)
    print("PROCUREMENT EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total PDFs processed: {total_pdfs}")
    print(f"Total items extracted: {total_items}")
    
    print("\n" + "-" * 60)
    print("Details by PDF:")
    print("-" * 60)
    
    for pdf_name, pdf_data in data.items():
        print(f"\n{pdf_name}:")
        print(f"  Items: {pdf_data['total_items']}")
        
        if pdf_data['items']:
            print("  Sample items:")
            for item in pdf_data['items'][:3]:  # Show first 3
                print(f"    - {item['description']}: {item['quantity']} {item['unit']}")


def export_to_csv(data, output_file='output/procurement_data.csv'):
    """Export extraction results to CSV format."""
    
    import csv
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['pdf_file', 'item_id', 'description', 'quantity', 'unit', 'page']
        )
        writer.writeheader()
        
        for pdf_name, pdf_data in data.items():
            for item in pdf_data['items']:
                row = {
                    'pdf_file': pdf_name,
                    'item_id': item.get('id', ''),
                    'description': item.get('description', ''),
                    'quantity': item.get('quantity', ''),
                    'unit': item.get('unit', ''),
                    'page': item.get('page', '')
                }
                writer.writerow(row)
    
    print(f"CSV exported to: {output_file}")


# ==================== ADVANCED USAGE ====================

def extract_with_fallback(text):
    """
    Try to extract items with fallback strategies.
    Useful for OCR'd text that might not match exactly.
    """
    
    # Strategy 1: Try complete line patterns
    items = extractor.extract_complete_items(text)
    if items:
        return items
    
    # Strategy 2: Manual extraction for difficult cases
    items = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        
        # Try to extract components manually
        item_id = extractor.extract_item_id(line)
        quantity = extractor.extract_quantity(line)
        unit = extractor.extract_unit(line)
        
        if quantity or item_id:
            # Likely a valid item line
            item = {
                'id': item_id or 'UNKNOWN',
                'description': line,  # Use full line as fallback
                'quantity': quantity or 1,
                'unit': unit or 'u'
            }
            items.append(item)
    
    return items


def validate_extraction(item):
    """Validate extracted item for missing or suspicious data."""
    
    issues = []
    
    if not item.get('id'):
        issues.append('Missing item ID')
    
    if not item.get('description') or len(item['description']) < 3:
        issues.append('Invalid description')
    
    if not item.get('quantity') or item['quantity'] <= 0:
        issues.append('Invalid quantity')
    
    if not item.get('unit'):
        issues.append('Missing unit')
    
    return {
        'is_valid': len(issues) == 0,
        'issues': issues
    }


# ==================== MAIN EXECUTION ====================

if __name__ == "__main__":
    print("Spanish Procurement PDF Extractor")
    print("=" * 60)
    
    # Extract from all PDFs
    pdf_folder = "pdfs"
    print(f"Scanning folder: {pdf_folder}\n")
    
    data = extract_from_multiple_pdfs(pdf_folder)
    
    # Generate report
    generate_summary_report(data)
    
    # Save results
    print("\nSaving results...")
    save_extraction_results(data)
    export_to_csv(data)
    
    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)
    
    # Example of validation
    print("\nValidating first item (if available):")
    for pdf_data in data.values():
        if pdf_data['items']:
            first_item = pdf_data['items'][0]
            validation = validate_extraction(first_item)
            
            print(f"Item: {first_item}")
            print(f"Valid: {validation['is_valid']}")
            if validation['issues']:
                print(f"Issues: {', '.join(validation['issues'])}")
            break
