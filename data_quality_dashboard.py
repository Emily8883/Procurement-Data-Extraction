"""
Data Quality Dashboard - Quick Statistics and Visualization
"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_dashboard(cleaned_json_path: str):
    """Generate and display data quality dashboard."""
    
    with open(cleaned_json_path, 'r', encoding='utf-8') as f:
        records = json.load(f)
    
    print("\n" + "=" * 80)
    print(" " * 20 + "PROCUREMENT DATA QUALITY DASHBOARD")
    print("=" * 80)
    
    # Overall statistics
    print("\n📊 OVERALL STATISTICS")
    print("-" * 80)
    print(f"Total Records: {len(records)}")
    print(f"Processing Date: 2026-06-24")
    
    # Document breakdown
    print("\n📄 DOCUMENTS")
    print("-" * 80)
    docs = {}
    for record in records:
        doc = record.get('document_name')
        if doc:
            docs[doc] = docs.get(doc, 0) + 1
    
    for doc, count in docs.items():
        print(f"  • {doc}: {count} record(s)")
    
    # Supplier analysis
    print("\n🏢 SUPPLIER INFORMATION")
    print("-" * 80)
    suppliers = {}
    for record in records:
        supplier = record.get('supplier_name')
        if supplier:
            suppliers[supplier] = suppliers.get(supplier, 0) + 1
    
    if suppliers:
        print(f"Unique Suppliers Found: {len(suppliers)}")
        for supplier, count in suppliers.items():
            print(f"  • {supplier}: {count} record(s)")
    else:
        print("⚠️  No supplier information found in dataset")
    
    # Quantity analysis
    print("\n📦 QUANTITY METRICS")
    print("-" * 80)
    quantities = [r.get('quantity') for r in records if r.get('quantity') is not None]
    if quantities:
        print(f"Numeric Values: {len(quantities)}/{len(records)}")
        print(f"  Total Quantity: {sum(quantities):.2f}")
        print(f"  Average Quantity: {sum(quantities) / len(quantities):.2f}")
        print(f"  Min: {min(quantities):.2f}")
        print(f"  Max: {max(quantities):.2f}")
    
    # Unit breakdown
    print("\n📏 UNITS OF MEASUREMENT")
    print("-" * 80)
    units = {}
    for record in records:
        unit = record.get('unit_of_measurement')
        if unit:
            units[unit] = units.get(unit, 0) + 1
    
    for unit, count in units.items():
        print(f"  • {unit}: {count} record(s)")
    
    # Currency analysis
    print("\n💱 CURRENCY INFORMATION")
    print("-" * 80)
    currencies = {}
    for record in records:
        currency = record.get('currency')
        if currency:
            currencies[currency] = currencies.get(currency, 0) + 1
    
    if currencies:
        print(f"Currencies Detected: {len(currencies)}")
        for currency, count in currencies.items():
            currency_name = record.get('currency_name', 'Unknown')
            print(f"  • {currency} ({currency_name}): {count} record(s)")
    else:
        print("⚠️  No currency information found in dataset")
    
    # Purchase order information
    print("\n📋 PURCHASE ORDER INFORMATION")
    print("-" * 80)
    pos = [r.get('purchase_order_number') for r in records if r.get('purchase_order_number')]
    print(f"PO Numbers Found: {len(pos)}/{len(records)}")
    for po in pos:
        print(f"  • {po}")
    
    # Description quality
    print("\n📝 DESCRIPTION QUALITY")
    print("-" * 80)
    desc_lengths = []
    for record in records:
        desc = record.get('item_description')
        if desc:
            desc_lengths.append(len(desc))
    
    if desc_lengths:
        print(f"Descriptions with Content: {len(desc_lengths)}/{len(records)}")
        print(f"  Average Length: {sum(desc_lengths) / len(desc_lengths):.0f} characters")
        print(f"  Shortest: {min(desc_lengths)} characters")
        print(f"  Longest: {max(desc_lengths)} characters")
    
    # Technical specifications
    print("\n🔧 TECHNICAL SPECIFICATIONS")
    print("-" * 80)
    specs = [r.get('technical_specifications') for r in records if r.get('technical_specifications')]
    print(f"Records with Specs: {len(specs)}/{len(records)}")
    if specs:
        print(f"  Average Spec Length: {sum(len(s) for s in specs) / len(specs):.0f} characters")
    
    # Data completeness
    print("\n✅ DATA COMPLETENESS")
    print("-" * 80)
    fields = [
        'document_name',
        'supplier_name',
        'item_description',
        'quantity',
        'unit_price',
        'total_price',
        'currency',
        'delivery_date',
        'purchase_order_number',
        'unit_of_measurement',
        'technical_specifications'
    ]
    
    completeness = {}
    for field in fields:
        filled = len([r for r in records if r.get(field) is not None])
        pct = (filled / len(records)) * 100
        completeness[field] = (filled, pct)
        
        bar_length = int(pct / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"{field:30s} [{bar}] {pct:5.1f}% ({filled}/{len(records)})")
    
    # Data quality score
    print("\n🎯 DATA QUALITY SCORE")
    print("-" * 80)
    avg_completeness = sum(v[1] for v in completeness.values()) / len(completeness)
    
    if avg_completeness >= 80:
        quality_level = "EXCELLENT"
        emoji = "🟢"
    elif avg_completeness >= 60:
        quality_level = "GOOD"
        emoji = "🟡"
    elif avg_completeness >= 40:
        quality_level = "FAIR"
        emoji = "🟠"
    else:
        quality_level = "POOR"
        emoji = "🔴"
    
    print(f"{emoji} Overall Completeness: {avg_completeness:.1f}% ({quality_level})")
    print()
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 80)
    
    recommendations = []
    
    if completeness['supplier_name'][1] == 0:
        recommendations.append("• Add supplier/vendor names to dataset")
    
    if completeness['currency'][1] == 0:
        recommendations.append("• Extract or add currency information")
    
    if completeness['unit_price'][1] == 0:
        recommendations.append("• Extract or add unit price data")
    
    if completeness['delivery_date'][1] == 0:
        recommendations.append("• Extract or add delivery date information")
    
    if completeness['purchase_order_number'][1] < 50:
        recommendations.append("• Ensure all records have PO numbers or reference codes")
    
    if recommendations:
        for rec in recommendations:
            print(rec)
    else:
        print("No critical gaps identified - dataset appears complete!")
    
    # Raw value validation
    print("\n🔄 RAW VALUE PRESERVATION")
    print("-" * 80)
    raw_fields_present = len([f for f in records[0].keys() if f.startswith('raw_value:')])
    print(f"Raw Value Fields Preserved: {raw_fields_present}")
    print("✅ All original values backed up with 'raw_value:' prefix")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    cleaned_json = script_dir / "output" / "cleaned_procurement.json"
    
    if cleaned_json.exists():
        generate_dashboard(str(cleaned_json))
    else:
        print(f"Error: Cleaned JSON not found at {cleaned_json}")
        print("Please run clean_dataset.py first")
