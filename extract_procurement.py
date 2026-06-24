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

# Optional OCR/image libraries
OCR_AVAILABLE = False
PDF2IMAGE_AVAILABLE = False
PIL_AVAILABLE = False
FITZ_AVAILABLE = False
OPENCV_AVAILABLE = False

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    Image = ImageOps = ImageEnhance = ImageFilter = None

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    pdf2image = None

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    fitz = None

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None


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
    
    def load_pdf_images(self, pdf_path: Path) -> List[Any]:
        """Load PDF pages as PIL images using available rendering libraries."""
        images = []
        if PDF2IMAGE_AVAILABLE:
            try:
                images = pdf2image.convert_from_path(str(pdf_path), dpi=300)
                return images
            except Exception:
                pass

        if FITZ_AVAILABLE:
            try:
                doc = fitz.open(str(pdf_path))
                for page in doc:
                    pix = page.get_pixmap(dpi=300)
                    mode = "RGB" if pix.n < 4 else "RGB"
                    image = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                    images.append(image)
                doc.close()
                return images
            except Exception:
                pass

        raise RuntimeError(
            "No PDF rendering library available for OCR. Install pdf2image+poppler or PyMuPDF."
        )

    def clean_ocr_text(self, text: str) -> str:
        """Apply lightweight OCR cleanup and normalize common substitution errors."""
        if not text:
            return text

        text = text.replace('\r', '\n')
        text = re.sub(r'[-]+', '', text)
        substitutions = {
            r'(?<=\D)0(?=[A-ZÁÉÍÓÚÑÜ])': 'O',
            r'(?<=[A-Za-zÁÉÍÓÚÑÜ])1(?=[A-Za-zÁÉÍÓÚÑÜ])': 'I',
            r'(?<=\D)l(?=\d)': '1',
            r'(?<=\d)O(?=\d)': '0',
            r'(?<=\s)\|(?=\s)': '|',
            r'[‘’`´]': "'",
        }

        for pattern, replacement in substitutions.items():
            text = re.sub(pattern, replacement, text)

        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def preprocess_image(self, image: Any) -> Any:
        """Preprocess an image before OCR to improve contrast and readability."""
        if not PIL_AVAILABLE:
            return image

        image = image.convert('L')
        image = ImageOps.autocontrast(image, cutoff=2)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        image = ImageEnhance.Contrast(image).enhance(1.5)
        image = image.filter(ImageFilter.SMOOTH_MORE)

        try:
            import numpy as np
        except ImportError:
            return image

        if OPENCV_AVAILABLE:
            try:
                arr = np.array(image)
                arr = cv2.GaussianBlur(arr, (3, 3), 0)
                _, thresh = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                return Image.fromarray(thresh)
            except Exception:
                pass

        # Fallback to simple thresholding
        image = image.point(lambda x: 0 if x < 140 else 255, '1')
        return image.convert('L')

    def ocr_image(self, image: Any, config: str = '--psm 6 --oem 3') -> str:
        """Perform OCR on an image and return cleaned text."""
        if not OCR_AVAILABLE:
            raise RuntimeError('OCR engine unavailable')

        text = pytesseract.image_to_string(image, lang='spa+eng', config=config)
        text = self.clean_ocr_text(text)
        return text

    def _score_ocr_text(self, text: str) -> float:
        """Score extracted OCR text to choose the best candidate."""
        if not text or len(text.strip()) < 20:
            return 0.0

        keywords = re.findall(
            r'(?:INVOICE|FACTURA|TOTAL|SUBTOTAL|IVA|TAX|PROVEEDOR|SUPPLIER|FECHA|DATE|CANTIDAD|QUANTITY|MONEDA|CURRENCY)',
            text, re.IGNORECASE)
        keyword_score = min(len(keywords) * 6, 40)

        numeric_density = len(re.findall(r'\d', text)) / max(len(text), 1)
        numeric_score = min(numeric_density * 40, 40)

        noise_penalty = len(re.findall(r'[\$@%&*#\^~]', text))
        noise_score = max(0, 20 - noise_penalty * 2)

        table_bonus = 10 if '|' in text or '\t' in text else 0

        return keyword_score + numeric_score + noise_score + table_bonus

    def extract_ocr_candidates(self, pdf_path: Path) -> Tuple[str, str]:
        """Run OCR on a scanned PDF using multiple preprocess strategies and return best text."""
        images = self.load_pdf_images(pdf_path)
        document_text_parts = []
        best_overall_method = 'ocr_raw'
        overall_scores = []

        for page_num, image in enumerate(images, 1):
            page_candidates = []

            try:
                raw_text = self.ocr_image(image)
                page_candidates.append(('raw', raw_text))
            except Exception:
                page_candidates.append(('raw', ''))

            try:
                enhanced_image = self.preprocess_image(image)
                enhanced_text = self.ocr_image(enhanced_image)
                page_candidates.append(('enhanced', enhanced_text))
            except Exception:
                page_candidates.append(('enhanced', ''))

            best_page_text = ''
            best_page_score = -1.0
            best_page_method = 'ocr_raw'

            for mode, candidate_text in page_candidates:
                page_score = self._score_ocr_text(candidate_text)
                if page_score > best_page_score:
                    best_page_score = page_score
                    best_page_text = candidate_text
                    best_page_method = mode

            if best_page_score < 20:
                best_page_text = page_candidates[0][1]
                best_page_method = 'ocr_fallback'

            document_text_parts.append(f"\n--- PAGE {page_num} ({best_page_method.upper()}) ---\n{best_page_text}")
            overall_scores.append((best_page_score, best_page_method))

        if overall_scores:
            best_overall_method = max(overall_scores, key=lambda item: item[0])[1]

        return "\n".join(document_text_parts).strip(), best_overall_method

    def extract_ocr_based(self, pdf_path: Path) -> Tuple[str, str]:
        """Extract text from scanned PDF using OCR with preprocessing and candidate ranking."""
        print(f"\n🖼️  Processing SCANNED document: {pdf_path.name}")

        if not OCR_AVAILABLE:
            print("  ⚠️  OCR not available. Please install: pytesseract, pdf2image, Tesseract-OCR")
            return "", "ocr_unavailable"

        try:
            ocr_text, extraction_method = self.extract_ocr_candidates(pdf_path)
            if not ocr_text.strip() and extraction_method == 'ocr_fallback':
                print("  ⚠️  OCR candidate selection produced empty output")
            return ocr_text, extraction_method
        except Exception as e:
            print(f"  Error during OCR: {e}")
            return "", "ocr_error"
    
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
    
    def _parse_decimal(self, raw_value: str) -> Optional[float]:
        """Parse a numeric string into a float, handling common OCR separators."""
        if not raw_value:
            return None

        value_str = raw_value.replace(' ', '').replace('O', '0').replace('o', '0')
        value_str = value_str.replace('€', '').replace('$', '').replace('£', '')
        value_str = re.sub(r'[^0-9\.,]', '', value_str)

        if value_str.count('.') > 1 and value_str.count(',') == 1:
            value_str = value_str.replace('.', '')
        if value_str.count(',') > 1 and value_str.count('.') == 1:
            value_str = value_str.replace(',', '')
        if ',' in value_str and '.' in value_str and value_str.index(',') > value_str.index('.'):
            value_str = value_str.replace(',', '')
        value_str = value_str.replace(',', '.')

        try:
            return float(value_str)
        except ValueError:
            return None

    def extract_all_prices(self, text: str) -> Tuple[List[float], Optional[float], Optional[float], Optional[float]]:
        """Extract all price-related values from text."""
        prices = []
        price_pattern = r'(?:[\$€£]|USD|EUR|GBP|MXN|COP|ARS|CAD|AUD)?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)'
        matches = re.findall(price_pattern, text, re.IGNORECASE)

        for match in matches:
            value = self._parse_decimal(match)
            if value is not None and 0 < value < 10000000:
                prices.append(value)

        subtotal = None
        tax = None
        total_amount = None

        labeled_patterns = {
            'subtotal': r'(?:Subtotal|Sub-total|Sub Total|SUBTOTAL)[:\s]*[\$€£]?\s*([\d,\.]+)',
            'tax': r'(?:Tax|VAT|IVA|Impuesto|Impuesto Ventas)[:\s]*[\$€£]?\s*([\d,\.]+)',
            'total': r'(?:Total Amount|Total|TOTAL|Total Due|Monto Total|Importe Total|Total a Pagar)[:\s]*[\$€£]?\s*([\d,\.]+)',
        }

        for field, pattern in labeled_patterns.items():
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    parsed = self._parse_decimal(match.group(1))
                    if parsed is not None:
                        if field == 'subtotal':
                            subtotal = parsed
                        elif field == 'tax':
                            tax = parsed
                        elif field == 'total':
                            total_amount = parsed
            except (ValueError, AttributeError):
                continue

        if total_amount is None and prices:
            total_amount = max(prices)

        return prices, subtotal, tax, total_amount
    
    def _find_quantity_in_line(self, line: str) -> Optional[str]:
        match = re.search(r'(?:Qty|Quantity|Cantidad|Cant\.|QTY)[:\s]*([\d,\.]+)', line, re.IGNORECASE)
        if match:
            return match.group(1).replace(',', '.').strip()

        match = re.search(r'([\d,\.]+)\s*(?:u|un|pcs|kg|m|l|ud|uds|pza|pz)', line, re.IGNORECASE)
        if match:
            return match.group(1).replace(',', '.').strip()

        return None

    def _find_price_in_line(self, line: str) -> Optional[str]:
        match = re.search(r'(?:Unit Price|Precio Unitario|Price|Precio)[:\s]*[\$€£]?\s*([\d,\.]+)', line, re.IGNORECASE)
        if match:
            return match.group(1).replace(',', '.').strip()

        match = re.search(r'[\$€£]\s*([\d,\.]+)', line)
        if match:
            return match.group(1).replace(',', '.').strip()

        return None

    def _find_total_in_line(self, line: str) -> Optional[str]:
        match = re.search(r'(?:Total Amount|Total|TOTAL|Monto Total|Importe Total|Total a Pagar)[:\s]*[\$€£]?\s*([\d,\.]+)', line, re.IGNORECASE)
        if match:
            return match.group(1).replace(',', '.').strip()
        return None

    def extract_line_items(self, text: str) -> List[Dict[str, str]]:
        """Extract line items from text."""
        line_items = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        for line in lines:
            if len(line) < 12:
                continue
            if any(skip in line.upper() for skip in ['PAGE', 'INVOICE', 'FACTURA', 'DATE:', 'FECHA:', '---', 'SUBTOTAL', 'TOTAL', 'TAX', 'IVA', 'PROVEEDOR', 'SUPPLIER']):
                continue

            if '|' in line or '\t' in line:
                cols = re.split(r'\s*\|\s*|\t+', line)
                if len(cols) >= 3 and any(re.search(r'\d', col) for col in cols[1:]):
                    description = cols[1].strip() if len(cols) > 1 else cols[0].strip()
                    quantity = self._find_quantity_in_line(line) or self._find_quantity_in_line(cols[-2] if len(cols) > 2 else line)
                    unit_price = self._find_price_in_line(line) or self._find_price_in_line(cols[-1] if len(cols) > 2 else line)
                    total_price = self._find_total_in_line(line) or self._find_price_in_line(cols[-1] if len(cols) > 2 else line)

                    if description and (quantity or unit_price or total_price):
                        line_items.append({
                            'description': description[:150],
                            'quantity': quantity or '',
                            'unit_price': unit_price or '',
                            'total_price': total_price or ''
                        })
                        continue

            text_match = re.search(r'[A-Za-z]{5,}', line)
            number_match = re.search(r'[\d,\.]{2,}', line)
            if text_match and number_match:
                quantity = self._find_quantity_in_line(line)
                unit_price = self._find_price_in_line(line)
                total_price = self._find_total_in_line(line)

                if quantity or unit_price or total_price:
                    line_items.append({
                        'description': line[:150],
                        'quantity': quantity or '',
                        'unit_price': unit_price or '',
                        'total_price': total_price or ''
                    })

        unique_items = []
        seen_descriptions = set()
        for item in line_items:
            desc_lower = item['description'].lower()
            if desc_lower not in seen_descriptions:
                seen_descriptions.add(desc_lower)
                unique_items.append(item)

        return unique_items[:20]
    
    def _estimate_text_confidence(self, text: str) -> int:
        if not text or len(text.strip()) < 20:
            return 0

        keywords = re.findall(
            r'(?:INVOICE|FACTURA|TOTAL|SUBTOTAL|IVA|TAX|PROVEEDOR|SUPPLIER|FECHA|DATE|CANTIDAD|QUANTITY|MONEDA|CURRENCY|ORDER|ORDEN)',
            text, re.IGNORECASE)
        score = min(len(keywords) * 8, 40)

        line_item_matches = len(re.findall(r'\b(?:Qty|Quantity|Cantidad|Unidad|Unit)\b', text, re.IGNORECASE))
        score += min(line_item_matches * 5, 20)

        noise_count = len(re.findall(r'[^\w\s\-:\|\.\$€£,\/]', text))
        score -= min(noise_count, 15)

        return max(0, min(score, 60))

    def calculate_confidence_score(self, missing_fields: List[str], extracted_text: str = "") -> int:
        """Calculate confidence score based on missing fields and OCR text quality."""
        total_fields = 8
        found_fields = max(0, total_fields - len(missing_fields))

        base_score = int((found_fields / total_fields) * 100)
        text_quality = self._estimate_text_confidence(extracted_text)

        critical_fields = ['supplier', 'invoice_or_po_number', 'total_amount']
        missing_critical = [f for f in missing_fields if f in critical_fields]
        penalty = len(missing_critical) * 10

        confidence = max(0, min(100, base_score + int(text_quality * 0.5) - penalty))
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
                extracted_text, extracted_method = self.extract_ocr_based(pdf_path)
                extraction_method = extracted_method or extraction_method
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
            confidence = self.calculate_confidence_score(missing_fields, extracted_text)
            
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
