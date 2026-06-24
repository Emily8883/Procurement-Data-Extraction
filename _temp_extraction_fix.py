from pathlib import Path

path = Path('extract_procurement.py')
text = path.read_text(encoding='utf-8', errors='replace')
old1 = '    def extract_ocr_based(self, pdf_path: Path) -> str:\r\n        """Extract text from scanned PDF using OCR with preprocessing and candidate ranking."""\r\n        print(f"\\n\U0001f5bc\ufe0f  Processing SCANNED document: {pdf_path.name}")\r\n\r\n        if not OCR_AVAILABLE:\r\n            print("  \u26a0\ufe0f  OCR not available. Please install: pytesseract, pdf2image, Tesseract-OCR")\r\n            return \"\"\r\n\r\n        try:\r\n            ocr_text, extraction_method = self.extract_ocr_candidates(pdf_path)\r\n            if not ocr_text.strip() and extraction_method == 'ocr_fallback':\r\n                print("  \u26a0\ufe0f  OCR candidate selection produced empty output")\r\n            return ocr_text\r\n        except Exception as e:\r\n            print(f"  Error during OCR: {e}")\r\n            return \"\"\r\n'
new1 = '    def extract_ocr_based(self, pdf_path: Path) -> Tuple[str, str]:\r\n        """Extract text from scanned PDF using OCR with preprocessing and candidate ranking."""\r\n        print(f"\\n\U0001f5bc\ufe0f  Processing SCANNED document: {pdf_path.name}")\r\n\r\n        if not OCR_AVAILABLE:\r\n            print("  \u26a0\ufe0f  OCR not available. Please install: pytesseract, pdf2image, Tesseract-OCR")\r\n            return \"\", \"ocr_unavailable\"\r\n\r\n        try:\r\n            ocr_text, extraction_method = self.extract_ocr_candidates(pdf_path)\r\n            if not ocr_text.strip() and extraction_method == 'ocr_fallback':\r\n                print("  \u26a0\ufe0f  OCR candidate selection produced empty output")\r\n            return ocr_text, extraction_method\r\n        except Exception as e:\r\n            print(f"  Error during OCR: {e}")\r\n            return \"\", \"ocr_error\"\r\n'
if old1 not in text:
    print('old1 not found')
else:
    text = text.replace(old1, new1, 1)
    print('patched old1')
old2 = '            # Extract text based on document type\r\n            if document_type == "scanned":\r\n                extracted_text = self.extract_ocr_based(pdf_path)\r\n            else:\r\n                extracted_text = self.extract_text_based(pdf_path)\r\n            \r\n            if not extracted_text:\r\n                print(f"  \u26a0\ufe0f  No text extracted from {document_name}")\r\n                extracted_text = \"\"\r\n'
new2 = '            # Extract text based on document type\r\n            if document_type == "scanned":\r\n                extracted_text, extracted_method = self.extract_ocr_based(pdf_path)\r\n                extraction_method = extracted_method or extraction_method\r\n            else:\r\n                extracted_text = self.extract_text_based(pdf_path)\r\n            \r\n            if not extracted_text:\r\n                print(f"  \u26a0\ufe0f  No text extracted from {document_name}")\r\n                extracted_text = \"\"\r\n'
if old2 not in text:
    print('old2 not found')
else:
    text = text.replace(old2, new2, 1)
    print('patched old2')
path.write_text(text, encoding='utf-8')
print('done')