"""
Procurement Data Extraction Pipeline

Extracts procurement-related fields from PDFs using:
- TEXT PARSER for text-based documents
- OCR ENGINE for scanned documents

Returns structured JSON with all required fields and missing field tracking.
"""

import json
import re
import pdfplumber
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Try to import OCR capability
try:
    import pytesseract
    from PIL import Image
    import pdf2image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class ProcurementExtractor:
    """Extract procurement data from PDFs."""
    
    # Regex patterns for procurement data
    PATTERNS = {
        'invoice_po': [
            r'(?:Invoice|INVOICE|Factura|FACTURA)[\s#:]*([A-Z0-9\-]{4,20})',
            r'(?:PO|P\.O|ORDER)[\s#:]*([A-Z0-9\-]{4,20})',
            r'(?:Número|Ref|Reference)[\s#:]*([A-Z0-9\-]{4,20})',
        ],
        'date': [
            r'(?:Date|Fecha|Issue Date|Fecha de emisión)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ],
        'supplier': [
            r'(?:Supplier|Proveedor|Vendor|From)[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\.&]{5,50}?)(?:\n|,|$)',
            r'(?:Company|Empresa|Organization)[:\s]+([A-Za-záéíóúñüAÉÍÓÚÑÜ\s,\.&]{5,50}?)(?:\n|,|$)',
        ],
        'currency': [
            r'(?:Currency|Moneda)[:\s]*([A-Z]{3})',
            r'[\s\(]([A-Z]{3})[\s\)]',
            r'(USD|EUR|GBP|MXN|COP|ARS)',
        ],
        'price': [
            r'(?:Total|TOTAL|Subtotal|SUBTOTAL)[:\s]*\$?[\s]*([\d,\.]+)',
            r'([\d,\.]+)(?:\s*(?:USD|EUR|GBP|MXN|COP|ARS))?(?:\s*$)',
        ],
        'quantity': [
            r'(?:Qty|Quantity|Cantidad)[:\s]*([\d,\.]+)',
            r'([\d,\.]+)(?:\s*(?:u|un|pcs|kg|m))',
        ],
        'tax': [
            r'(?:Tax|VAT|IVA|Impuesto)[:\s]*\$?[\s]*([\d,\.]+)',
        ],
    }
    
    def __init__(self, classifications_json: str, pdf_folder: str = "pdfs"):
        """
        Initialize the extractor.
        
        Args:
            classifications_json: Path to document classifications
            pdf_folder: Path to PDF folder
        """
        self.classifications_file = Path(classifications_json)
        self.pdf_folder = Path(pdf_folder)
        self.classifications = {}
        self.extracted_data = []
        self.load_classifications()
    
    def load_classifications(self):
        """Load document classifications."""
        if not self.classifications_file.exists():
            print(f"Warning: Classifications file not found at {self.classifications_file}")
            return
        
        with open(self.classifications_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for doc in data:
                self.classifications[doc["document_name"]] = {
                    "document_type": doc["document_type"],
                    "extraction_method": doc["extraction_method"],
                }
        
        print(f"Loaded classifications for {len(self.classifications)} documents")
    
    def extract_text_based(self, pdf_path: Path) -> str:
        """Extract text from text-based PDF."""
        print(f"\n📄 Processing TEXT document: {pdf_path.name}")
        
        full_text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text += f"\n--- PAGE {page_num} ---\n{text}"
                    
                    # Also try to extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            full_text += "\n--- TABLE ---\n"
                            for row in table:
                                full_text += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
            
            return full_text
        except Exception as e:
            print(f"  Error extracting text: {e}")
            return ""
    
    def extract_ocr_based(self, pdf_path: Path) -> str:
        """Extract text from scanned PDF using OCR."""
        print(f"\n🖼️  Processing SCANNED document: {pdf_path.name}")
        
        if not OCR_AVAILABLE:
            print("  ⚠️  OCR not available. Please install: pytesseract, pdf2image, Tesseract-OCR")
            return ""
        
        full_text = ""
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path)
            
            for page_num, image in enumerate(images, 1):
                print(f"  Processing page {page_num}/{len(images)}...")
                # OCR the image
                text = pytesseract.image_to_string(image, lang='spa+eng')
                full_text += f"\n--- PAGE {page_num} (OCR) ---\n{text}"
            
            return full_text
        except Exception as e:
            print(f"  Error during OCR: {e}")
            return ""
    
    def extract_field(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract a field using multiple regex patterns."""
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else match.group(0).strip()
                    # Additional validation
                    if value and len(value) >= 2 and len(value) <= 200:
                        return value
            except Exception as e:
                continue
        return None
    
    def extract_all_prices(self, text: str) -> Tuple[List[float], Optional[float], Optional[float], Optional[float]]:
        """Extract all price-related values from text."""
        prices = []
        
        # Extract all numeric values that could be prices (more conservative)
        price_pattern = r'(?:[\$€£]|USD|EUR|GBP)[\s]*([\d,\.]+(?:[\d,\.]{0,3})?)'
        matches = re.findall(price_pattern, text)
        
        for match in matches:
            try:
                # Clean and convert - only if it looks like a valid price
                value_str = match.replace(',', '').replace(' ', '')
                if value_str and value_str.count('.') <= 1:  # Max one decimal point
                    value = float(value_str)
                    if 0 < value < 10000000:  # Reasonable price range
                        prices.append(value)
            except (ValueError, AttributeError):
                continue
        
        # Try to identify subtotal, tax, and total (more specific patterns)
        subtotal = None
        tax = None
        total_amount = None
        
        try:
            subtotal_match = re.search(
                r'(?:Subtotal|Sub-total|Sub Total|SUBTOTAL)[:\s]*[\$€£]?[\s]*([\d,\.]+)',
                text, re.IGNORECASE
            )
            if subtotal_match:
                value_str = subtotal_match.group(1).replace(',', '').replace(' ', '')
                if value_str and value_str.count('.') <= 1:
                    subtotal = float(value_str)
        except (ValueError, AttributeError):
            pass
        
        try:
            tax_match = re.search(
                r'(?:Tax|VAT|IVA|Impuesto)[:\s]*[\$€£]?[\s]*([\d,\.]+)',
                text, re.IGNORECASE
            )
            if tax_match:
                value_str = tax_match.group(1).replace(',', '').replace(' ', '')
                if value_str and value_str.count('.') <= 1:
                    tax = float(value_str)
        except (ValueError, AttributeError):
            pass
        
        try:
            total_match = re.search(
                r'(?:Total Amount|TOTAL|Total Due|Monto Total)[:\s]*[\$€£]?[\s]*([\d,\.]+)',
                text, re.IGNORECASE
            )
            if total_match:
                value_str = total_match.group(1).replace(',', '').replace(' ', '')
                if value_str and value_str.count('.') <= 1:
                    total_amount = float(value_str)
        except (ValueError, AttributeError):
            pass
        
        return prices, subtotal, tax, total_amount
    
    def extract_line_items(self, text: str) -> List[Dict[str, str]]:
        """Extract line items from text."""
        line_items = []
        
        # Pattern for line items: description + quantity + unit price + total
        # This is simplified and may need enhancement for specific formats
        lines = text.split('\n')
        
        current_item = None
        for line in lines:
            # Skip empty lines, headers, page markers, and short lines
            if not line.strip() or len(line) < 10:
                continue
            
            # Skip obvious metadata lines
            if any(skip in line.upper() for skip in ['PAGE', 'INVOICE', 'FACTURA', 'DATE:', 'FECHA:', '---']):
                continue
            
            # Look for lines with both text and numbers (likely line items)
            # More conservative: require meaningful text + numbers
            text_match = re.search(r'[a-zA-Z]{5,}', line)  # At least 5 letters
            number_match = re.search(r'[\d,\.]{2,}', line)  # At least 2 digit chars
            
            if text_match and number_match:
                # Try to extract quantity and price
                qty_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:u|un|pcs|kg|m|ud)?(?:\s|$)', line)
                price_match = re.search(r'[\$€£]?\s*(\d+[.,]\d{2})', line)
                
                # Only add if we have meaningful content
                if qty_match or price_match:
                    item = {
                        "description": line.strip()[:150],  # Limit description length
                        "quantity": qty_match.group(1) if qty_match else "",
                        "unit_price": price_match.group(1) if price_match else "",
                        "total_price": ""
                    }
                    line_items.append(item)
        
        # Return only unique items and limit to reasonable count
        unique_items = []
        seen_descriptions = set()
        for item in line_items:
            desc_lower = item['description'].lower()
            if desc_lower not in seen_descriptions:
                seen_descriptions.add(desc_lower)
                unique_items.append(item)
        
        return unique_items[:15]  # Limit to 15 items
    
    def calculate_confidence_score(self, extracted: Dict[str, Any], missing_fields: List[str]) -> int:
        """Calculate confidence score based on fields present."""
        total_fields = 9  # Total possible fields
        found_fields = total_fields - len(missing_fields)
        
        # Adjust score based on critical fields
        critical_fields = ['supplier', 'invoice_or_po_number', 'total_amount']
        missing_critical = [f for f in missing_fields if f in critical_fields]
        
        base_score = int((found_fields / total_fields) * 100)
        
        # Reduce score by 10% for each missing critical field
        penalty = len(missing_critical) * 10
        
        confidence = max(0, base_score - penalty)
        return confidence
    
    def extract_document(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract procurement data from a single PDF.
        
        Returns:
            Dictionary with extracted data and missing fields
        """
        print(f"\n{'='*70}")
        print(f"Extracting: {pdf_path.name}")
        print('='*70)
        
        try:
            document_name = pdf_path.name
            doc_classification = self.classifications.get(document_name, {})
            document_type = doc_classification.get("document_type", "unknown")
            extraction_method = doc_classification.get("extraction_method", "unknown")
            
            # Extract text based on document type
            if document_type == "scanned":
                extracted_text = self.extract_ocr_based(pdf_path)
            else:
                extracted_text = self.extract_text_based(pdf_path)
            
            if not extracted_text:
                print(f"  ⚠️  No text extracted from {document_name}")
                extracted_text = ""
            
            # Extract all fields
            print("\n📋 Extracting fields...")
            
            supplier = self.extract_field(extracted_text, self.PATTERNS['supplier'])
            invoice_po = self.extract_field(extracted_text, self.PATTERNS['invoice_po'])
            issue_date = self.extract_field(extracted_text, self.PATTERNS['date'])
            currency = self.extract_field(extracted_text, self.PATTERNS['currency'])
            
            prices, subtotal, tax, total_amount = self.extract_all_prices(extracted_text)
            line_items = self.extract_line_items(extracted_text)
            
            # Track missing fields
            missing_fields = []
            if not supplier:
                missing_fields.append("supplier")
            if not invoice_po:
                missing_fields.append("invoice_or_po_number")
            if not issue_date:
                missing_fields.append("issue_date")
            if not currency:
                missing_fields.append("currency")
            if not line_items:
                missing_fields.append("line_items")
            if subtotal is None:
                missing_fields.append("subtotal")
            if tax is None:
                missing_fields.append("tax")
            if total_amount is None:
                missing_fields.append("total_amount")
            
            # Calculate confidence
            confidence = self.calculate_confidence_score(extracted_text, missing_fields)
            
            # Build result
            result = {
                "document_name": document_name,
                "document_type": document_type,
                "supplier": supplier or "",
                "invoice_or_po_number": invoice_po or "",
                "issue_date": issue_date or "",
                "currency": currency or "",
                "line_items": line_items,
                "subtotal": str(round(subtotal, 2)) if subtotal else "",
                "tax": str(round(tax, 2)) if tax else "",
                "total_amount": str(round(total_amount, 2)) if total_amount else "",
                "confidence_score": confidence,
                "missing_fields": missing_fields,
                "extraction_method": extraction_method,
            }
            
            # Print extracted data
            print(f"\n  Supplier: {result['supplier'] or '(missing)'}")
            print(f"  Invoice/PO: {result['invoice_or_po_number'] or '(missing)'}")
            print(f"  Date: {result['issue_date'] or '(missing)'}")
            print(f"  Currency: {result['currency'] or '(missing)'}")
            print(f"  Total: {result['total_amount'] or '(missing)'}")
            print(f"  Line Items: {len(line_items)} found")
            print(f"  Confidence: {confidence}%")
            print(f"  Missing Fields: {', '.join(missing_fields) if missing_fields else 'None'}")
            
            return result
        
        except Exception as e:
            print(f"  ❌ Error extracting document: {e}")
            return {
                "document_name": pdf_path.name,
                "document_type": "unknown",
                "supplier": "",
                "invoice_or_po_number": "",
                "issue_date": "",
                "currency": "",
                "line_items": [],
                "subtotal": "",
                "tax": "",
                "total_amount": "",
                "confidence_score": 0,
                "missing_fields": ["all"],
                "extraction_method": "error",
                "error": str(e)
            }
    
    def extract_all_documents(self) -> List[Dict[str, Any]]:
        """Extract data from all documents."""
        self.extracted_data = []
        
        pdf_files = sorted(self.pdf_folder.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {self.pdf_folder}")
            return []
        
        print(f"\n🚀 Starting extraction pipeline for {len(pdf_files)} documents")
        print("=" * 70)
        
        for pdf_path in pdf_files:
            try:
                result = self.extract_document(pdf_path)
                self.extracted_data.append(result)
            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}")
                # Add error record
                self.extracted_data.append({
                    "document_name": pdf_path.name,
                    "document_type": "unknown",
                    "error": str(e),
                    "missing_fields": ["all"],
                    "confidence_score": 0,
                })
        
        return self.extracted_data
    
    def save_extracted_data(self, output_path: str = None) -> Path:
        """Save extracted data to JSON file."""
        if not output_path:
            output_path = self.pdf_folder.parent / "output" / "extracted_procurement.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.extracted_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Extracted data saved to: {output_path}")
        return output_path
    
    def generate_extraction_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        summary = {
            "total_documents": len(self.extracted_data),
            "extraction_timestamp": datetime.now().isoformat(),
            "documents_by_type": {
                "text": len([d for d in self.extracted_data if d.get("document_type") == "text"]),
                "scanned": len([d for d in self.extracted_data if d.get("document_type") == "scanned"]),
            },
            "average_confidence": sum(d.get("confidence_score", 0) for d in self.extracted_data) / len(self.extracted_data) if self.extracted_data else 0,
            "documents": []
        }
        
        for doc in self.extracted_data:
            doc_summary = {
                "document_name": doc.get("document_name"),
                "document_type": doc.get("document_type"),
                "confidence_score": doc.get("confidence_score"),
                "missing_fields_count": len(doc.get("missing_fields", [])),
                "line_items_count": len(doc.get("line_items", [])),
                "has_supplier": bool(doc.get("supplier")),
                "has_total": bool(doc.get("total_amount")),
            }
            summary["documents"].append(doc_summary)
        
        return summary


def main():
    """Main execution function."""
    script_dir = Path(__file__).parent
    classifications_file = script_dir / "output" / "document_classifications.json"
    pdf_folder = script_dir / "pdfs"
    output_file = script_dir / "output" / "extracted_procurement.json"
    
    # Create extractor
    extractor = ProcurementExtractor(
        classifications_json=str(classifications_file),
        pdf_folder=str(pdf_folder)
    )
    
    # Extract all documents
    extracted_data = extractor.extract_all_documents()
    
    if not extracted_data:
        print("No data extracted")
        return
    
    # Save results
    extractor.save_extracted_data(str(output_file))
    
    # Generate summary
    print("\n" + "=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    
    summary = extractor.generate_extraction_summary()
    
    print(f"\nTotal Documents: {summary['total_documents']}")
    print(f"  • Text-based: {summary['documents_by_type']['text']}")
    print(f"  • Scanned: {summary['documents_by_type']['scanned']}")
    print(f"\nAverage Confidence Score: {summary['average_confidence']:.1f}%")
    
    print(f"\nDocument Details:")
    for doc in summary['documents']:
        print(f"\n  📄 {doc['document_name']}")
        print(f"     Type: {doc['document_type']} | Confidence: {doc['confidence_score']}%")
        print(f"     Supplier Found: {'✓' if doc['has_supplier'] else '✗'}")
        print(f"     Total Found: {'✓' if doc['has_total'] else '✗'}")
        print(f"     Line Items: {doc['line_items_count']}")
        print(f"     Missing Fields: {doc['missing_fields_count']}")
    
    print(f"\n✅ Full results saved to: {output_file}")


if __name__ == "__main__":
    main()
