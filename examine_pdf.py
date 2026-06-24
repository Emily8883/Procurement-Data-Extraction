import pdfplumber

pdf_file = 'pdfs/00c4e05f2d8e31c0.pdf'
with pdfplumber.open(pdf_file) as pdf:
    page = pdf.pages[0]
    
    # Try extracting tables
    tables = page.extract_tables()
    print(f"Tables found: {len(tables) if tables else 0}")
    
    if tables:
        for i, table in enumerate(tables):
            print(f"\n--- Table {i+1} ---")
            for row in table[:10]:  # First 10 rows
                print(row)
    
    # Also try raw text with different settings
    print("\n--- Raw text (with layout) ---")
    text = page.extract_text(layout=True)
    print(text[:1500] if text else "No text extracted")
