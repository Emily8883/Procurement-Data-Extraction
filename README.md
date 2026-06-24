# Procurement Extraction Pipeline

This repository contains tools to extract procurement information from PDF documents (text and scanned). The pipeline is designed around an extraction step, normalization, supplier matching (placeholder), price estimation (placeholder), and export to JSON/Excel.

Assumptions
- No supplier sources are configured by default; matching is a placeholder.
- OCR libraries (`pytesseract`, `pdf2image`) are optional; code falls back to `PyMuPDF` (`fitz`) where available.
- No website scraping is implemented or allowed — connectors must be provided separately.

Workflow
1. Extraction: `extract_procurement.py` provides text-based and OCR-based extraction.
2. Normalization: `run.py` normalizes raw extracted items into a canonical schema.
3. Matching: `supplier_matching.py` exposes `SupplierMatcher` (placeholder) for plugging real sources.
4. Price estimation: `price_estimation.py` provides `PriceEstimator` placeholder.
5. Export: `run.py` writes `output/output.json` and `output/output.xlsx`.

Match Confidence Methodology
- Extraction confidence derives from OCR/text heuristics inside `extract_procurement.py`.
- Supplier matching returns conservative confidence (0 by default). When integrating real sources, return a numeric confidence [0..1].
- Price estimation returns low confidence for heuristic matches; connectors should provide calibrated scores.

How to plug in supplier sources
- Replace or extend `supplier_matching.SupplierMatcher.match_supplier` to call approved APIs or local lookup tables.
- Expected return format from `match_supplier`:
  - `{'match_id': str|None, 'name': str|None, 'confidence': float, 'source': str}`
- Do not add web scraping code. Use approved connectors / APIs and keep credentials out of the repository.

Running
- Run the pipeline: `python run.py` (processes PDFs in `pdfs/` and writes `output/output.json` and `output/output.xlsx`).

Next steps
- Implement a robust normalization module and unit tests.
- Add connectors for supplier data sources and price lookup.
