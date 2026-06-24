import json
import re
from pathlib import Path
from typing import List, Dict, Any

from .data_quality_validator import validate_pipeline_output


def _pdf_structure_summary(pdf_path: str) -> Dict[str, Any]:
    """Inspect the PDF to determine whether tables are present."""
    from pdfplumber import open as open_pdf

    pdf_path = Path(pdf_path)
    tables_found = False
    pages_with_tables = 0
    total_pages = 0

    try:
        with open_pdf(str(pdf_path)) as pdf:
            total_pages = len(pdf.pages)
            for page in pdf.pages:
                if page.extract_tables():
                    tables_found = True
                    pages_with_tables += 1
    except Exception:
        return {
            'tables_found': False,
            'pages_with_tables': 0,
            'total_pages': total_pages,
            'table_inspection_error': True
        }

    return {
        'tables_found': tables_found,
        'pages_with_tables': pages_with_tables,
        'total_pages': total_pages,
        'table_inspection_error': False
    }


def _missing_pct(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((count / total) * 100, 2)


def _detect_header_only(records: List[Dict[str, Any]], report: Dict[str, Any]) -> bool:
    if report['total_records'] == 0:
        return False

    header_fields = ['supplier_name', 'invoice_or_po_number']
    header_present = any(
        any(record.get(field) for field in header_fields)
        for record in records
    )
    if not header_present:
        return False

    item_fields_missing = 0
    for record in records:
        if not record.get('item_description') and not record.get('quantity') and not record.get('total_amount'):
            item_fields_missing += 1

    return item_fields_missing >= max(1, int(report['total_records'] * 0.6))


def _detect_scattered_values(records: List[Dict[str, Any]], report: Dict[str, Any]) -> bool:
    if report['total_records'] == 0:
        return False

    present_fields = 0
    for field in ['supplier_name', 'unit_price', 'currency', 'invoice_or_po_number']:
        if report['missing_fields_summary'].get(field, 0) < report['total_records']:
            present_fields += 1

    return present_fields >= 2 and report['invalid_records'] > 0


def _resolve_issue(records: List[Dict[str, Any]], report: Dict[str, Any], structure: Dict[str, Any]) -> str:
    if report['total_records'] == 0:
        return 'TABLE_FAILURE' if structure['tables_found'] else 'TEXT_FALLBACK_ONLY'

    if not structure['tables_found']:
        return 'TEXT_FALLBACK_ONLY'

    if _detect_header_only(records, report):
        return 'HEADER_ONLY_DATA'

    if _detect_scattered_values(records, report):
        return 'SCATTERED_VALUES'

    return 'SCATTERED_VALUES'


def generate_extraction_diagnostics(pdf_path: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a diagnostic report for a single PDF extraction job."""
    report = validate_pipeline_output(records)
    structure = _pdf_structure_summary(pdf_path)
    issue = _resolve_issue(records, report, structure)

    diagnostics = {
        'pdf_path': pdf_path,
        'issue': issue,
        'total_records': report['total_records'],
        'missing_supplier_name_pct': _missing_pct(report['missing_fields_summary'].get('supplier_name', 0), report['total_records']),
        'missing_unit_price_pct': _missing_pct(report['missing_fields_summary'].get('unit_price', 0), report['total_records']),
        'missing_currency_pct': _missing_pct(report['missing_fields_summary'].get('currency', 0), report['total_records']),
        'missing_invoice_or_po_number_pct': _missing_pct(report['missing_fields_summary'].get('invoice_or_po_number', 0), report['total_records']),
        'tables_found': structure['tables_found'],
        'pages_with_tables': structure['pages_with_tables'],
        'total_pages': structure['total_pages'],
        'validation_report': report
    }

    return diagnostics
