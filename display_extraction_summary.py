#!/usr/bin/env python3
"""
Display formatted summary of extracted procurement data.
Shows the structured JSON output with proper formatting.
"""

import json
from pathlib import Path


def display_extraction_summary():
    """Display formatted extraction results."""
    
    script_dir = Path(__file__).parent / "output"
    json_file = script_dir / "extracted_procurement.json"
    
    if not json_file.exists():
        print(f"File not found: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*80)
    print("PROCUREMENT DATA EXTRACTION - STRUCTURED JSON OUTPUT")
    print("="*80)
    
    for idx, record in enumerate(data, 1):
        print(f"\n{'─'*80}")
        print(f"DOCUMENT {idx}: {record['document_name']}")
        print('─'*80)
        
        print(f"\nDocument Type: {record.get('document_type', 'N/A').upper()}")
        print(f"Extraction Method: {record.get('extraction_method', 'N/A').upper()}")
        print(f"Confidence Score: {record.get('confidence_score', 0)}%")
        
        print(f"\n📋 PROCUREMENT FIELDS:")
        print(f"  • Supplier: {record.get('supplier') or '(missing)'}")
        print(f"  • Invoice/PO: {record.get('invoice_or_po_number') or '(missing)'}")
        print(f"  • Issue Date: {record.get('issue_date') or '(missing)'}")
        print(f"  • Currency: {record.get('currency') or '(missing)'}")
        print(f"  • Subtotal: {record.get('subtotal') or '(missing)'}")
        print(f"  • Tax: {record.get('tax') or '(missing)'}")
        print(f"  • Total Amount: {record.get('total_amount') or '(missing)'}")
        
        line_items = record.get('line_items', [])
        print(f"\n📦 LINE ITEMS ({len(line_items)} found):")
        
        if line_items:
            for item_idx, item in enumerate(line_items[:3], 1):  # Show first 3
                print(f"\n  Item {item_idx}:")
                print(f"    Description: {item.get('description', '(empty)')[:80]}")
                print(f"    Quantity: {item.get('quantity', '(empty)')}")
                print(f"    Unit Price: {item.get('unit_price', '(empty)')}")
                print(f"    Total Price: {item.get('total_price', '(empty)')}")
            
            if len(line_items) > 3:
                print(f"\n  ... and {len(line_items) - 3} more items")
        
        missing = record.get('missing_fields', [])
        print(f"\n⚠️  MISSING FIELDS ({len(missing)}):")
        if missing:
            for field in missing:
                print(f"  • {field}")
        else:
            print("  (None - all fields extracted)")
        
        # Show error if present
        if 'error' in record:
            print(f"\n❌ ERROR: {record['error']}")
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("PIPELINE SUMMARY")
    print('='*80)
    
    total = len(data)
    text_docs = len([d for d in data if d.get('document_type') == 'text'])
    scanned_docs = len([d for d in data if d.get('document_type') == 'scanned'])
    with_errors = len([d for d in data if 'error' in d])
    
    avg_confidence = sum(d.get('confidence_score', 0) for d in data) / total if total > 0 else 0
    total_missing = sum(len(d.get('missing_fields', [])) for d in data)
    total_line_items = sum(len(d.get('line_items', [])) for d in data)
    
    print(f"\nTotal Documents: {total}")
    print(f"  • Text-based: {text_docs}")
    print(f"  • Scanned (OCR): {scanned_docs}")
    print(f"  • With Errors: {with_errors}")
    
    print(f"\nAverage Confidence Score: {avg_confidence:.1f}%")
    print(f"Total Missing Fields (all docs): {total_missing}")
    print(f"Total Line Items Extracted: {total_line_items}")
    
    print(f"\n{'='*80}")
    print(f"✅ Extraction Complete!")
    print(f"📁 JSON Output: {json_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    display_extraction_summary()
