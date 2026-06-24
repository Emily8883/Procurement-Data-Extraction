"""
Clean and standardize procurement dataset.

Includes:
- Supplier name normalization
- Quantity normalization to numeric values
- Currency detection and standardization
- OCR error detection and fixing (with context awareness)
- Preservation of original raw values
"""

import json
import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


class ProcurementDataCleaner:
    """Clean and standardize procurement dataset."""
    
    # Common OCR errors mapping (only fixed when context confirms)
    OCR_CORRECTIONS = {
        r'\b0(\d)': r'O\1',  # 0 at start of word -> O
        r'(\w)0(\w)': r'\1O\2',  # 0 between letters -> O
        r'\bl(\d)': r'1\1',  # lowercase L followed by digit -> 1
        r'(\w)l(\s|$)': r'\g<1>1\2',  # lowercase L at end -> 1
    }
    
    # Currency patterns with standardization
    CURRENCY_MAP = {
        'EUR': [r'€|EUR|EURO|€URO', 'Euro'],
        'USD': [r'\$|USD|DÓLAR|DOLARES|DOLAR', 'US Dollar'],
        'GBP': [r'£|GBP|LIBRA|LIBRAS', 'British Pound'],
        'MXN': [r'MXN|PESO MX|PESOS', 'Mexican Peso'],
        'COP': [r'COP|PESO CO|PESOS', 'Colombian Peso'],
        'ARS': [r'ARS|PESO AR|PESOS', 'Argentine Peso'],
    }
    
    # Supplier name variations
    SUPPLIER_VARIATIONS = {
        'ACME': ['ACME', 'ACME INC', 'ACME CORP'],
        'SIEMENS': ['SIEMENS', 'SIEMENS AG', 'SIEMENS GMBH'],
        'PHILIPS': ['PHILIPS', 'PHILIPS LIGHTING', 'PHILIPS ELECTRONICS'],
        'BOSCH': ['BOSCH', 'BOSCH GMBH', 'ROBERT BOSCH'],
    }
    
    def __init__(self, normalized_json_path: str, raw_csv_path: str = None):
        """
        Initialize the cleaner.
        
        Args:
            normalized_json_path: Path to the normalized JSON file
            raw_csv_path: Path to the raw CSV file for reference
        """
        self.normalized_json_path = normalized_json_path
        self.raw_csv_path = raw_csv_path
        self.records = []
        self.raw_df = None
        self.cleaned_records = []
    
    def load_data(self):
        """Load normalized JSON and raw CSV data."""
        with open(self.normalized_json_path, 'r', encoding='utf-8') as f:
            self.records = json.load(f)
        print(f"Loaded {len(self.records)} records from {self.normalized_json_path}")
        
        if self.raw_csv_path and Path(self.raw_csv_path).exists():
            self.raw_df = pd.read_csv(self.raw_csv_path)
            print(f"Loaded raw CSV with {len(self.raw_df)} rows")
    
    def extract_supplier_from_description(self, description: str) -> Optional[str]:
        """Try to extract supplier name from description."""
        if not description:
            return None
        
        desc_upper = description.upper()
        
        # Check for known supplier patterns
        for supplier_norm, variations in self.SUPPLIER_VARIATIONS.items():
            for variant in variations:
                if variant.upper() in desc_upper:
                    return supplier_norm
        
        # Look for "Suministrado por", "Proveedor", etc.
        supplier_patterns = [
            r'Suministrado por[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s&,.]+?)(?:\n|$)',
            r'Proveedor[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s&,.]+?)(?:\n|$)',
            r'Fabricante[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s&,.]+?)(?:\n|$)',
            r'Marca[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s&,.]+?)(?:\n|$)',
        ]
        
        for pattern in supplier_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                supplier = match.group(1).strip()
                if supplier:
                    return supplier
        
        return None
    
    def detect_ocr_errors(self, text: str, context: str = '') -> str:
        """
        Detect and fix likely OCR errors.
        Only fixes errors where context strongly suggests the correction.
        """
        if not text:
            return text
        
        corrections_made = []
        corrected = text
        
        # 0 vs O: Fix if surrounded by letters (likely "O" in acronyms or words)
        # Example: "S0LUTION" -> "SOLUTION", but keep "100" as is
        def fix_zero_oh(match):
            before = match.group(1) if match.group(1) else ''
            zero = match.group(2)
            after = match.group(3) if match.group(3) else ''
            
            # If surrounded by letters, likely OCR error
            if before and before[-1].isalpha() and after and after[0].isalpha():
                corrections_made.append(f"0->O: {before}{zero}{after}")
                return f"{before}O{after}"
            return match.group(0)
        
        corrected = re.sub(r'([A-Za-z])?0([A-Za-z])', fix_zero_oh, corrected)
        
        # l (lowercase L) vs 1 (digit): Fix in obvious contexts
        # Example: "l00" -> "100" (but only if very obvious)
        if re.search(r'l{2,}', corrected):  # Multiple lowercase L's likely OCR error
            corrected = re.sub(r'l+', '1', corrected)
            corrections_made.append("ll->1: Multiple lowercase L's")
        
        return corrected
    
    def normalize_quantity(self, quantity: Any, unit: str = '') -> Tuple[Optional[float], Optional[str]]:
        """
        Normalize quantity to numeric value.
        
        Returns:
            Tuple of (normalized_quantity, quantity_notes)
        """
        if quantity is None or (isinstance(quantity, float) and pd.isna(quantity)):
            return None, None
        
        try:
            # Convert to float
            qty_float = float(quantity)
            
            # Check for suspicious values
            notes = []
            if qty_float == 0:
                notes.append("quantity_is_zero")
            elif qty_float > 1000000:
                notes.append("quantity_unusually_high")
            elif qty_float < 0:
                notes.append("quantity_negative")
            
            return qty_float, '|'.join(notes) if notes else None
        except (ValueError, TypeError):
            return None, "failed_numeric_conversion"
    
    def detect_currency(self, text: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detect currency from text.
        
        Returns:
            Tuple of (currency_code, currency_name, raw_match)
        """
        if not text:
            return None, None, None
        
        text_upper = str(text).upper()
        
        for currency_code, (pattern, currency_name) in self.CURRENCY_MAP.items():
            match = re.search(pattern, text_upper, re.IGNORECASE)
            if match:
                return currency_code, currency_name, match.group(0)
        
        return None, None, None
    
    def clean_text(self, text: Optional[str], fix_ocr: bool = False) -> Optional[str]:
        """
        Clean and normalize text.
        
        Args:
            text: Text to clean
            fix_ocr: Whether to apply OCR error fixes
        
        Returns:
            Cleaned text
        """
        if text is None or (isinstance(text, float) and pd.isna(text)):
            return None
        
        text = str(text).strip()
        
        if not text:
            return None
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix OCR errors if requested and context allows
        if fix_ocr:
            text = self.detect_ocr_errors(text)
        
        return text
    
    def normalize_supplier_name(self, supplier: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Normalize supplier name.
        
        Returns:
            Tuple of (normalized_name, standardized_name)
        """
        if not supplier:
            return None, None
        
        supplier = self.clean_text(supplier)
        if not supplier:
            return None, None
        
        original = supplier
        supplier_upper = supplier.upper()
        
        # Check for known variations
        for standard_name, variations in self.SUPPLIER_VARIATIONS.items():
            for variant in variations:
                if variant.upper() == supplier_upper:
                    return original, standard_name
        
        return original, None
    
    def clean_record(self, record: Dict[str, Any], raw_row: pd.Series = None) -> Dict[str, Any]:
        """
        Clean and standardize a single record.
        
        Args:
            record: The record to clean (from normalized JSON)
            raw_row: Optional corresponding raw CSV row for context
        
        Returns:
            Cleaned record with raw_value fields
        """
        cleaned = {}
        
        # Document name (no cleaning needed typically)
        cleaned["document_name"] = record.get("document_name")
        cleaned["raw_value:document_name"] = record.get("document_name")
        
        # Supplier name
        raw_supplier = record.get("supplier_name")
        if raw_supplier:
            norm_supplier, std_supplier = self.normalize_supplier_name(raw_supplier)
            cleaned["supplier_name"] = std_supplier or norm_supplier
        else:
            # Try to extract from description
            desc = record.get("item_description")
            extracted_supplier = self.extract_supplier_from_description(desc)
            norm_supplier, std_supplier = self.normalize_supplier_name(extracted_supplier)
            cleaned["supplier_name"] = std_supplier or norm_supplier
        
        cleaned["raw_value:supplier_name"] = raw_supplier
        
        # Item description
        raw_description = record.get("item_description")
        cleaned_description = self.clean_text(raw_description, fix_ocr=True)
        cleaned["item_description"] = cleaned_description
        cleaned["raw_value:item_description"] = raw_description
        
        # Quantity
        raw_quantity = record.get("quantity")
        unit = record.get("unit_of_measurement")
        norm_quantity, qty_notes = self.normalize_quantity(raw_quantity, unit)
        cleaned["quantity"] = norm_quantity
        cleaned["raw_value:quantity"] = raw_quantity
        if qty_notes:
            cleaned["quantity_notes"] = qty_notes
        
        # Unit price (preserved as-is but raw value stored)
        raw_unit_price = record.get("unit_price")
        cleaned["unit_price"] = raw_unit_price
        cleaned["raw_value:unit_price"] = raw_unit_price
        
        # Total price (preserved as-is but raw value stored)
        raw_total_price = record.get("total_price")
        cleaned["total_price"] = raw_total_price
        cleaned["raw_value:total_price"] = raw_total_price
        
        # Currency detection
        raw_currency = record.get("currency")
        # Try to detect from description if not found
        currency_code, currency_name, raw_match = self.detect_currency(cleaned_description)
        cleaned["currency"] = currency_code
        cleaned["currency_name"] = currency_name
        cleaned["raw_value:currency"] = raw_currency
        if raw_match:
            cleaned["currency_raw_match"] = raw_match
        
        # Delivery date
        raw_delivery_date = record.get("delivery_date")
        cleaned["delivery_date"] = self.clean_text(raw_delivery_date)
        cleaned["raw_value:delivery_date"] = raw_delivery_date
        
        # Purchase order number
        raw_po = record.get("purchase_order_number")
        cleaned["purchase_order_number"] = self.clean_text(raw_po)
        cleaned["raw_value:purchase_order_number"] = raw_po
        
        # Unit of measurement
        raw_unit = record.get("unit_of_measurement")
        cleaned["unit_of_measurement"] = self.clean_text(raw_unit)
        cleaned["raw_value:unit_of_measurement"] = raw_unit
        
        # Technical specifications
        raw_specs = record.get("technical_specifications")
        cleaned["technical_specifications"] = self.clean_text(raw_specs)
        cleaned["raw_value:technical_specifications"] = raw_specs
        
        return cleaned
    
    def clean_all(self) -> List[Dict[str, Any]]:
        """Clean all records."""
        self.cleaned_records = []
        
        for idx, record in enumerate(self.records):
            # Get corresponding raw row if available
            raw_row = None
            if self.raw_df is not None and idx < len(self.raw_df):
                raw_row = self.raw_df.iloc[idx]
            
            cleaned = self.clean_record(record, raw_row)
            self.cleaned_records.append(cleaned)
        
        print(f"Cleaned {len(self.cleaned_records)} records")
        return self.cleaned_records
    
    def save_cleaned_json(self, output_path: str = None) -> Path:
        """Save cleaned records to JSON file."""
        if not output_path:
            output_path = Path(self.normalized_json_path).parent / "cleaned_procurement.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.cleaned_records, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(self.cleaned_records)} cleaned records to {output_path}")
        return output_path
    
    def generate_cleaning_report(self) -> Dict[str, Any]:
        """Generate a report on cleaning operations."""
        report = {
            "total_records_processed": len(self.cleaned_records),
            "suppliers": {
                "found": len([r for r in self.cleaned_records if r.get("supplier_name")]),
                "unique": len(set(r.get("supplier_name") for r in self.cleaned_records if r.get("supplier_name"))),
                "null_count": len([r for r in self.cleaned_records if not r.get("supplier_name")]),
            },
            "quantities": {
                "numeric_values": len([r for r in self.cleaned_records if r.get("quantity") is not None]),
                "null_values": len([r for r in self.cleaned_records if r.get("quantity") is None]),
                "with_notes": len([r for r in self.cleaned_records if r.get("quantity_notes")]),
            },
            "currencies": {
                "detected": len([r for r in self.cleaned_records if r.get("currency")]),
                "unique": list(set(r.get("currency") for r in self.cleaned_records if r.get("currency"))),
                "null_count": len([r for r in self.cleaned_records if not r.get("currency")]),
            },
            "descriptions": {
                "cleaned": len([r for r in self.cleaned_records if r.get("item_description")]),
                "null_count": len([r for r in self.cleaned_records if not r.get("item_description")]),
            },
            "purchase_orders": {
                "found": len([r for r in self.cleaned_records if r.get("purchase_order_number")]),
                "null_count": len([r for r in self.cleaned_records if not r.get("purchase_order_number")]),
            },
        }
        
        return report


def main():
    """Main execution function."""
    script_dir = Path(__file__).parent
    normalized_json = script_dir / "output" / "normalized_procurement.json"
    raw_csv = script_dir / "output" / "raw_extracted.csv"
    cleaned_json = script_dir / "output" / "cleaned_procurement.json"
    
    if not normalized_json.exists():
        print(f"Error: Normalized JSON not found at {normalized_json}")
        return
    
    # Initialize cleaner
    cleaner = ProcurementDataCleaner(
        normalized_json_path=str(normalized_json),
        raw_csv_path=str(raw_csv) if raw_csv.exists() else None
    )
    
    # Load data
    cleaner.load_data()
    
    # Clean all records
    cleaner.clean_all()
    
    # Save cleaned data
    cleaner.save_cleaned_json(str(cleaned_json))
    
    # Generate and display report
    report = cleaner.generate_cleaning_report()
    print("\n=== Cleaning Report ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    print(f"\nCleaned output saved to: {cleaned_json}")


if __name__ == "__main__":
    main()
