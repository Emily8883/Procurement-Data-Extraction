import pdfplumber
from pathlib import Path

pdf_files = list(Path('pdfs').glob('*.pdf'))

for pdf_file in pdf_files:  # Look at all PDFs
    print(f"\n{'='*80}")
    print(f"FILE: {pdf_file.name}")
    print(f"{'='*80}\n")
    
    with pdfplumber.open(pdf_file) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        has_text = False
        
        # Look at specific pages
        for page_num in range(min(3, len(pdf.pages))):
            page = pdf.pages[page_num]
            text = page.extract_text()
            
            if text and text.strip():
                has_text = True
                print(f"\n--- PAGE {page_num + 1} (First 50 lines) ---")
                lines = text.split('\n')
                for i, line in enumerate(lines[:50]):
                    if line.strip():
                        print(f"{i:3d}: {line[:120]}")
        
        if not has_text:
            print("  [No extractable text found - likely scanned image]")
