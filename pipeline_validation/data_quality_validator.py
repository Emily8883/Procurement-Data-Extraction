from typing import List, Dict, Any

from .record_validator import validate_record

REQUIRED_FIELDS = [
    'supplier_name',
    'invoice_or_po_number',
    'item_description',
    'quantity',
    'unit_price',
    'total_amount',
    'currency'
]


def _is_field_present(record: Dict[str, Any], field_name: str) -> bool:
    value = record.get(field_name)
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _classify_record(missing_count: int) -> str:
    if missing_count == 0:
        return 'VALID'
    if missing_count <= 2:
        return 'PARTIAL'
    return 'INVALID'


def validate_pipeline_output(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate procurement output records and generate a quality report."""
    report = {
        'total_records': 0,
        'valid_records': 0,
        'invalid_records': 0,
        'partial_records': 0,
        'missing_fields_summary': {field: 0 for field in REQUIRED_FIELDS},
        'completeness_score': 0.0,
        'records': []
    }

    if not isinstance(records, list):
        raise ValueError('Pipeline output records must be a list of dictionaries.')

    report['total_records'] = len(records)
    if report['total_records'] == 0:
        report['completeness_score'] = 0.0
        return report

    for record in records:
        if not isinstance(record, dict):
            record = {}  # treat non-dict entries as fully missing

        missing_fields = []
        for field in REQUIRED_FIELDS:
            if not _is_field_present(record, field):
                report['missing_fields_summary'][field] += 1
                missing_fields.append(field)

        classification = _classify_record(len(missing_fields))
        if classification == 'VALID':
            report['valid_records'] += 1
        elif classification == 'PARTIAL':
            report['partial_records'] += 1
        else:
            report['invalid_records'] += 1

        validation = validate_record(record)
        record_copy = dict(record)
        record_copy['quality_classification'] = classification
        record_copy['missing_fields'] = missing_fields
        record_copy['record_validation'] = validation
        report['records'].append(record_copy)

    total_possible_fields = report['total_records'] * len(REQUIRED_FIELDS)
    total_present = total_possible_fields - sum(report['missing_fields_summary'].values())
    report['completeness_score'] = round(total_present / total_possible_fields, 2) if total_possible_fields > 0 else 0.0

    return report
