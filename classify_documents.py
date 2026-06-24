"""
PDF Document Classification System

Classifies each PDF as either:
- TEXT-BASED: Contains selectable text (use text parser)
- SCANNED: Image-based document (requires OCR)

Outputs classification results with recommended extraction methods.
"""

import pdfplumber
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json

# Try to import PyMuPDF, but fallback to pdfplumber-only analysis if unavailable
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


class DocumentClassifier:
    """Classify PDFs by type (text-based vs scanned/image-based)."""
    
    def __init__(self, pdf_folder: str = "pdfs"):
        """
        Initialize the classifier.
        
        Args:
            pdf_folder: Path to folder containing PDF files
        """
        self.pdf_folder = Path(pdf_folder)
        self.classifications = []
    
    def get_text_density(self, pdf_path: Path) -> Tuple[int, int, float]:
        """
        Calculate text density in the PDF.
        
        Returns:
            Tuple of (total_text_chars, total_pages, avg_chars_per_page)
        """
        total_chars = 0
        total_pages = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        total_chars += len(text)
        except Exception as e:
            print(f"  Warning: Error reading {pdf_path.name}: {e}")
            return 0, total_pages, 0
        
        avg_chars = total_chars / total_pages if total_pages > 0 else 0
        return total_chars, total_pages, avg_chars
    
    def has_extractable_text(self, pdf_path: Path) -> bool:
        """Check if PDF has extractable text."""
        try:
            total_chars, total_pages, avg_chars = self.get_text_density(pdf_path)
            
            # If average chars per page is > 100, it's likely text-based
            # Otherwise, it's likely scanned/image-based
            return avg_chars > 100
        except Exception as e:
            print(f"  Error checking text: {e}")
            return False
    
    def has_images(self, pdf_path: Path) -> bool:
        """Check if PDF contains images (indicating scanned document)."""
        if not FITZ_AVAILABLE:
            return False  # Can't detect without PyMuPDF
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc):
                image_list = page.get_images()
                if image_list:
                    doc.close()
                    return True
            
            doc.close()
            return False
        except Exception as e:
            print(f"  Error checking images: {e}")
            return False
    
    def get_page_analysis(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Analyze each page to determine if it's text or image.
        
        Returns:
            Dictionary with analysis details per page
        """
        analysis = {
            "pages": [],
            "text_pages": 0,
            "image_pages": 0,
            "mixed_pages": 0
        }
        
        if FITZ_AVAILABLE:
            # Use PyMuPDF for detailed analysis
            try:
                doc = fitz.open(pdf_path)
                
                for page_num, page in enumerate(doc):
                    page_info = {
                        "page_number": page_num + 1,
                        "has_text": False,
                        "has_images": False,
                        "text_chars": 0,
                        "image_count": 0
                    }
                    
                    # Check for text
                    text = page.get_text()
                    if text and len(text.strip()) > 50:
                        page_info["has_text"] = True
                        page_info["text_chars"] = len(text)
                    
                    # Check for images
                    images = page.get_images()
                    if images:
                        page_info["has_images"] = True
                        page_info["image_count"] = len(images)
                    
                    # Classify page
                    if page_info["has_text"] and page_info["has_images"]:
                        analysis["mixed_pages"] += 1
                    elif page_info["has_text"]:
                        analysis["text_pages"] += 1
                    elif page_info["has_images"]:
                        analysis["image_pages"] += 1
                    
                    analysis["pages"].append(page_info)
                
                doc.close()
                return analysis
            except Exception as e:
                print(f"  Error analyzing pages with PyMuPDF: {e}")
        
        # Fallback: Use pdfplumber only
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_info = {
                        "page_number": page_num + 1,
                        "has_text": False,
                        "has_images": False,
                        "text_chars": 0,
                        "image_count": 0
                    }
                    
                    # Check for text using pdfplumber
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        page_info["has_text"] = True
                        page_info["text_chars"] = len(text)
                    
                    # Try to detect images
                    # pdfplumber doesn't directly list images, but we can check cropped images
                    try:
                        im = page.debug_tablefinder()
                        page_info["image_count"] = len(page.chars) if page.chars else 0
                    except:
                        pass
                    
                    # If page has no significant text, likely image-based
                    if not page_info["has_text"]:
                        page_info["has_images"] = True  # Assume scanned if no text
                    
                    # Classify page
                    if page_info["has_text"] and page_info["has_images"]:
                        analysis["mixed_pages"] += 1
                    elif page_info["has_text"]:
                        analysis["text_pages"] += 1
                    elif page_info["has_images"]:
                        analysis["image_pages"] += 1
                    
                    analysis["pages"].append(page_info)
                
                return analysis
        except Exception as e:
            print(f"  Error analyzing pages: {e}")
            return analysis
    
    def classify_document(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Classify a single PDF document.
        
        Returns:
            Classification result dictionary
        """
        print(f"\nClassifying: {pdf_path.name}")
        print("-" * 60)
        
        result = {
            "document_name": pdf_path.name,
            "file_path": str(pdf_path),
            "file_size_mb": pdf_path.stat().st_size / (1024 * 1024),
        }
        
        try:
            # Get page analysis
            page_analysis = self.get_page_analysis(pdf_path)
            total_pages = len(page_analysis["pages"])
            
            print(f"Total Pages: {total_pages}")
            print(f"  • Text Pages: {page_analysis['text_pages']}")
            print(f"  • Image/Scanned Pages: {page_analysis['image_pages']}")
            print(f"  • Mixed Pages: {page_analysis['mixed_pages']}")
            
            # Get text density
            total_chars, _, avg_chars = self.get_text_density(pdf_path)
            print(f"Text Density: {total_chars} chars across {total_pages} pages")
            print(f"  Average: {avg_chars:.1f} chars/page")
            
            # Determine document type
            # Rule: If majority of pages have text > 100 chars, it's TEXT
            text_ratio = page_analysis["text_pages"] / total_pages if total_pages > 0 else 0
            image_ratio = page_analysis["image_pages"] / total_pages if total_pages > 0 else 0
            mixed_ratio = page_analysis["mixed_pages"] / total_pages if total_pages > 0 else 0
            
            result["page_analysis"] = page_analysis
            result["text_ratio"] = round(text_ratio, 2)
            result["image_ratio"] = round(image_ratio, 2)
            result["mixed_ratio"] = round(mixed_ratio, 2)
            
            # Classification logic
            if avg_chars > 100 or text_ratio >= 0.5:
                result["document_type"] = "text"
                result["extraction_method"] = "text_parser"
                confidence = "HIGH"
                
                if mixed_ratio > 0.3:
                    confidence = "MEDIUM"
                    print(f"\n⚠️  Note: {page_analysis['mixed_pages']} mixed pages detected")
            
            elif image_ratio > 0.5:
                result["document_type"] = "scanned"
                result["extraction_method"] = "ocr_engine"
                confidence = "HIGH"
            
            elif mixed_ratio > text_ratio and mixed_ratio > image_ratio:
                result["document_type"] = "scanned"
                result["extraction_method"] = "ocr_engine"
                confidence = "MEDIUM"
            
            else:
                # Default to scanned if unclear
                result["document_type"] = "scanned"
                result["extraction_method"] = "ocr_engine"
                confidence = "LOW"
            
            result["classification_confidence"] = confidence
            
            # Print result
            print(f"\n✓ Classification:")
            print(f"  Document Type: {result['document_type'].upper()}")
            print(f"  Extraction Method: {result['extraction_method'].upper()}")
            print(f"  Confidence: {confidence}")
            
        except Exception as e:
            print(f"Error classifying document: {e}")
            result["document_type"] = "unknown"
            result["extraction_method"] = "manual_review"
            result["error"] = str(e)
        
        return result
    
    def classify_all_documents(self) -> List[Dict[str, Any]]:
        """Classify all PDF documents in the folder."""
        self.classifications = []
        
        if not self.pdf_folder.exists():
            print(f"Error: PDF folder not found at {self.pdf_folder}")
            return []
        
        pdf_files = sorted(self.pdf_folder.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {self.pdf_folder}")
            return []
        
        print(f"Found {len(pdf_files)} PDF file(s) to classify")
        print("=" * 60)
        
        for pdf_path in pdf_files:
            classification = self.classify_document(pdf_path)
            self.classifications.append(classification)
        
        return self.classifications
    
    def save_classifications(self, output_path: str = None) -> Path:
        """Save classifications to JSON file."""
        if not output_path:
            output_path = self.pdf_folder.parent / "output" / "document_classifications.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare simplified output
        simplified = []
        for clf in self.classifications:
            simplified.append({
                "document_name": clf["document_name"],
                "document_type": clf["document_type"],
                "extraction_method": clf["extraction_method"],
                "classification_confidence": clf.get("classification_confidence", "UNKNOWN"),
                "file_size_mb": clf["file_size_mb"],
                "text_ratio": clf.get("text_ratio", None),
                "image_ratio": clf.get("image_ratio", None),
                "mixed_ratio": clf.get("mixed_ratio", None),
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(simplified, f, indent=2, ensure_ascii=False)
        
        print(f"\nClassifications saved to: {output_path}")
        return output_path
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary statistics of classifications."""
        report = {
            "total_documents": len(self.classifications),
            "text_based": 0,
            "scanned": 0,
            "unknown": 0,
            "confidence_distribution": {
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "UNKNOWN": 0
            },
            "documents": []
        }
        
        for clf in self.classifications:
            doc_type = clf.get("document_type", "unknown")
            confidence = clf.get("classification_confidence", "UNKNOWN")
            
            if doc_type == "text":
                report["text_based"] += 1
            elif doc_type == "scanned":
                report["scanned"] += 1
            else:
                report["unknown"] += 1
            
            report["confidence_distribution"][confidence] = report["confidence_distribution"].get(confidence, 0) + 1
            
            report["documents"].append({
                "document_name": clf["document_name"],
                "document_type": doc_type,
                "extraction_method": clf.get("extraction_method"),
                "confidence": confidence
            })
        
        return report


def main():
    """Main execution function."""
    script_dir = Path(__file__).parent
    pdf_folder = script_dir / "pdfs"
    output_file = script_dir / "output" / "document_classifications.json"
    
    # Create classifier
    classifier = DocumentClassifier(pdf_folder=str(pdf_folder))
    
    # Classify all documents
    classifications = classifier.classify_all_documents()
    
    if not classifications:
        print("No documents to classify")
        return
    
    # Save results
    classifier.save_classifications(str(output_file))
    
    # Generate and display summary
    print("\n" + "=" * 60)
    print("CLASSIFICATION SUMMARY")
    print("=" * 60)
    
    report = classifier.generate_summary_report()
    
    print(f"\nTotal Documents: {report['total_documents']}")
    print(f"  • Text-Based: {report['text_based']}")
    print(f"  • Scanned: {report['scanned']}")
    print(f"  • Unknown: {report['unknown']}")
    
    print(f"\nClassification Confidence:")
    for confidence, count in report["confidence_distribution"].items():
        print(f"  • {confidence}: {count}")
    
    print(f"\nDocument Details:")
    for doc in report["documents"]:
        method_icon = "📄" if doc["document_type"] == "text" else "🖼️" if doc["document_type"] == "scanned" else "❓"
        print(f"{method_icon} {doc['document_name']}")
        print(f"   Type: {doc['document_type']} | Method: {doc['extraction_method']} | Confidence: {doc['confidence']}")
    
    print("\n" + "=" * 60)
    
    # Also print as JSON
    print("\nJSON Output:")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
