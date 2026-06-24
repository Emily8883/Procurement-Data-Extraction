"""
Normalize extracted procurement data into structured JSON format.
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


class ProcurementDataNormalizer:
    """Normalize extracted procurement CSV data into structured JSON."""
    
    def __init__(self, csv_path: str, output_path: str = None):
        """
        Initialize the normalizer.
        
        Args:
            csv_path: Path to the extracted CSV file
            output_path: Path to save the JSON output (optional)
        """
        self.csv_path = csv_path
        self.output_path = output_path or Path(csv_path).parent / "normalized_procurement.json"
        self.df = None
        self.records = []
    
    def load_csv(self) -> pd.DataFrame:
        """Load the CSV file."""
        self.df = pd.read_csv(self.csv_path)
        print(f"Loaded {len(self.df)} records from {self.csv_path}")
        return self.df
    
    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text fields."""
        if pd.isna(text) or text is None:
            return None
        
        # Convert to string and strip whitespace
        text = str(text).strip()
        
        if not text:
            return None
        
        # Remove extra newlines and spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def extract_currency(self, text: Optional[str]) -> Optional[str]:
        """Try to extract currency from text."""
        if not text:
            return None
        
        text = str(text).upper()
        
        # Common currency patterns
        currency_patterns = {
            'EUR': r'\€|EUR|EURO',
            'USD': r'\$|USD|DÓLAR',
            'GBP': r'£|GBP|LIBRA',
            'MXN': r'MXN|PESO',
            'COP': r'COP|PESO',
            'ARS': r'ARS|PESO',
        }
        
        for currency, pattern in currency_patterns.items():
            if re.search(pattern, text):
                return currency
        
        return None
    
    def extract_date(self, text: Optional[str]) -> Optional[str]:
        """Try to extract date from text."""
        if not text:
            return None
        
        text = str(text)
        
        # Common date patterns (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}\s+(?:de\s+)?(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_price(self, text: Optional[str]) -> Optional[float]:
        """Try to extract price from text."""
        if not text:
            return None
        
        text = str(text)
        
        # Look for price patterns (currency symbols or amount formats)
        price_patterns = [
            r'[\$€£]?\s*(\d+(?:[.,]\d{2})?)',
            r'(\d+(?:[.,]\d{2})?)\s*(?:EUR|USD|GBP|MXN|COP|€|\$|£)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1)
                # Normalize decimal separator
                price_str = price_str.replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        return None
    
    def normalize_record(self, row: pd.Series, index: int) -> Dict[str, Any]:
        """
        Normalize a single CSV row into the required JSON structure.
        
        Args:
            row: A pandas Series representing one row
            index: The row index
        
        Returns:
            Dictionary with normalized procurement data
        """
        # Clean and extract fields
        document_name = self.clean_text(row.get('pdf_name'))
        item_description = self.clean_text(row.get('original_description'))
        quantity = row.get('quantity')
        unit = self.clean_text(row.get('unit'))
        technical_specs = self.clean_text(row.get('technical_specifications'))
        purchase_order_number = self.clean_text(row.get('item_id'))
        
        # Convert quantity to float if possible
        if pd.notna(quantity):
            try:
                quantity = float(quantity)
            except (ValueError, TypeError):
                quantity = None
        else:
            quantity = None
        
        # Try to extract additional fields from description
        supplier_name = None
        currency = None
        unit_price = None
        total_price = None
        delivery_date = None
        
        if item_description:
            currency = self.extract_currency(item_description)
            delivery_date = self.extract_date(item_description)
            # Price extraction disabled unless explicitly present
            # unit_price = self.extract_price(item_description)
        
        # Combine unit with description if present
        full_description = item_description
        if unit:
            full_description = f"{item_description} ({unit})" if item_description else unit
        
        # Build normalized record
        record = {
            "document_name": document_name,
            "supplier_name": supplier_name,
            "item_description": item_description,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "currency": currency,
            "delivery_date": delivery_date,
            "purchase_order_number": purchase_order_number,
        }
        
        # Add optional metadata
        record["unit_of_measurement"] = unit
        record["technical_specifications"] = technical_specs
        
        return record
    
    def normalize_all(self) -> List[Dict[str, Any]]:
        """Normalize all records in the CSV."""
        if self.df is None:
            self.load_csv()
        
        self.records = []
        for idx, (_, row) in enumerate(self.df.iterrows()):
            record = self.normalize_record(row, idx)
            self.records.append(record)
        
        print(f"Normalized {len(self.records)} records")
        return self.records
    
    def save_json(self, pretty: bool = True) -> Path:
        """
        Save normalized records to JSON file.
        
        Args:
            pretty: Whether to prettify the JSON output
        
        Returns:
            Path to the saved file
        """
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
            else:
                json.dump(self.records, f, ensure_ascii=False)
        
        print(f"Saved {len(self.records)} normalized records to {output_path}")
        return output_path
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the normalized data."""
        if not self.records:
            return {}
        
        summary = {
            "total_records": len(self.records),
            "documents": list(set(r["document_name"] for r in self.records if r["document_name"])),
            "suppliers": list(set(r["supplier_name"] for r in self.records if r["supplier_name"])),
            "currencies": list(set(r["currency"] for r in self.records if r["currency"])),
            "fields_with_null_values": {},
        }
        
        # Count null values for each field
        for field in self.records[0].keys():
            null_count = sum(1 for r in self.records if r[field] is None)
            if null_count > 0:
                summary["fields_with_null_values"][field] = null_count
        
        return summary


def main():
    """Main execution function."""
    script_dir = Path(__file__).parent
    csv_path = script_dir / "output" / "raw_extracted.csv"
    json_path = script_dir / "output" / "normalized_procurement.json"
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return
    
    # Initialize normalizer
    normalizer = ProcurementDataNormalizer(
        csv_path=str(csv_path),
        output_path=str(json_path)
    )
    
    # Normalize all records
    normalizer.normalize_all()
    
    # Save to JSON
    normalizer.save_json(pretty=True)
    
    # Print summary
    summary = normalizer.get_summary()
    print("\n=== Normalization Summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    print(f"\nOutput saved to: {json_path}")


if __name__ == "__main__":
    main()
