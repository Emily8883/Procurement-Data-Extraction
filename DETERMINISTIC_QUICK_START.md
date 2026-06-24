# Deterministic Pipeline - Quick Start Guide

## Installation & Setup

### 1. Verify Structure

```bash
# All files should exist:
ls config/validation_rules.json
ls config/pipeline_config.json
ls pipelines/*.py
ls logging/execution_logger.py
ls deterministic_pipeline.py
```

### 2. Test Import

```bash
python -c "from deterministic_pipeline import DeterministicPipeline; print('✅ Import successful')"
```

---

## Basic Usage

### Example 1: Process All PDFs

```python
from deterministic_pipeline import DeterministicPipeline
from pathlib import Path

# Initialize
pipeline = DeterministicPipeline()

# Get PDFs
pdfs = list(Path('pdfs').glob('*.pdf'))

# Process
results = pipeline.process_documents([str(pdf) for pdf in pdfs])

# Save
output_files = pipeline.save_results()

# View summary
print(f"Processed {results['total_documents']} documents")
print(f"Procurement: {results['by_pipeline']['procurement']}")
print(f"Specifications: {results['by_pipeline']['specification']}")
```

### Example 2: Single Document Processing

```python
# Process one document
result = pipeline.process_single_document('pdfs/invoice.pdf')

# Check routing decision
print(f"Routed to: {result['pipeline_used']}")
print(f"Status: {result['status']}")
print(f"Confidence: {result['extraction_confidence']:.0f}%")

# View errors
if result['validation_errors']:
    print("Errors:")
    for error in result['validation_errors']:
        print(f"  - {error}")
```

### Example 3: Review Execution Log

```python
# Get complete execution report
report = pipeline.logger.generate_execution_report()

# Print summary
pipeline.logger.print_session_summary()

# Access individual logs
for log in report['execution_logs']:
    if log['status'] == 'FAILED':
        print(f"\n{log['document_name']}:")
        print(f"  Pipeline: {log['pipeline_used']}")
        print(f"  Errors: {log['validation_errors']}")
        print(f"  Reason: {log['failure_reason']}")

# Save for audit
pipeline.logger.save_execution_log(Path('audit_trail.json'))
```

---

## Configuration Changes

### Adjust Procurement Validation

Edit `config/validation_rules.json`:

```json
{
  "procurement_pipeline": {
    "field_completeness": {
      "critical_fields": [
        "supplier",
        "invoice_or_po_number",
        "issue_date",
        "total_amount"
        // Add or remove fields here
      ]
    },
    "math_validation": {
      "checks": [{
        "tolerance": 0.10  // Change from 0.05 to 0.10 (10%)
      }]
    }
  }
}
```

Then restart pipeline - changes are automatic.

### Add Routing Keywords

Edit `config/validation_rules.json`:

```json
{
  "routing_rules": {
    "classification_keywords": {
      "procurement": [
        "invoice",
        "purchase order",
        // Add new keywords here
        "my_custom_keyword"
      ],
      "specification": [
        "specification",
        // Add new keywords
        "my_spec_keyword"
      ]
    }
  }
}
```

---

## Understanding Execution Logs

### Log File Location

```
logging/logs/execution_20260624_150000.json
```

### Interpreting Log Entries

```json
{
  "execution_id": "a1b2c3d4_abc123",
  "document_name": "invoice_001.pdf",
  "timestamp": "2026-06-24T15:00:10",
  
  // Routing Decision
  "routing_decision": "procurement",
  "routing_confidence": 0.87,  // 87% confident
  
  // Pipeline Choice
  "pipeline_used": "Procurement Pipeline",
  "document_type": "procurement",
  
  // Extraction Quality
  "extraction_confidence": 45.0,  // 45% of fields extracted
  
  // Validation Results
  "validation_result": "FAIL",
  "validation_errors": [
    "CRITICAL: Missing field 'total_amount'"
  ],
  "validation_warnings": [
    "Low extraction confidence: 45%"
  ],
  
  // Status
  "status": "FAILED",
  "failure_reason": "CRITICAL: Missing field 'total_amount'",
  
  // Performance
  "processing_time_seconds": 2.34
}
```

### Interpreting Status Values

| Status | Meaning | Procurement | Specification |
|--------|---------|-------------|----------------|
| SUCCESS | No errors, no warnings | Proceed | Proceed |
| WARNING | Warnings only, no errors | BLOCKED | Proceed with caution |
| FAILED | Has errors | BLOCKED | BLOCKED |

---

## Output Files

### Procurement Results

`output/deterministic_procurement_20260624_150000.json`

```json
[
  {
    "document_name": "invoice_001.pdf",
    "document_type": "invoice_or_po",
    "processing_status": "invalid",
    "extraction_confidence": 45.0,
    "supplier": "ABC Company",
    "invoice_or_po_number": "INV-2026-001",
    "issue_date": "",
    "total_amount": "",
    "line_items": [...],
    "missing_fields": ["issue_date", "total_amount"]
  }
]
```

### Specification Results

`output/deterministic_specification_20260624_150000.json`

```json
[
  {
    "document_name": "spec_001.pdf",
    "document_type": "specification",
    "processing_status": "valid",
    "extraction_confidence": 30.0,
    "line_items": [...],
    "technical_specifications": {"has_technical_requirements": true},
    "missing_fields": ["supplier", "issue_date"]
  }
]
```

### Combined Results

`output/deterministic_pipeline_20260624_150000.json`

```json
{
  "session_id": "a1b2c3d4",
  "timestamp": "2026-06-24T15:00:00",
  "procurement_documents": [...],
  "specification_documents": [...]
}
```

---

## Troubleshooting

### Problem: Document routed incorrectly

**Solution:** Check routing keywords in `validation_rules.json`

```bash
# View current keywords
cat config/validation_rules.json | grep -A 10 "classification_keywords"

# Adjust if needed
```

### Problem: Validation too strict

**Solution:** Adjust enforcement mode in `validation_rules.json`

```json
{
  "procurement_pipeline": {
    "pass_criteria": {
      "allow_warnings": true,  // Set to true to allow warnings
      "allow_errors": false    // Keep false for critical errors
    }
  }
}
```

### Problem: Low confidence scores

**Solution:** Check extraction method - may need OCR

```bash
# View confidence in log
cat logging/logs/execution_*.json | grep extraction_confidence

# If 0%, document is scanned - OCR needed
```

### Problem: Math validation failing

**Solution:** Adjust tolerance in `validation_rules.json`

```json
{
  "math_validation": {
    "checks": [{
      "formula": "subtotal + tax ≈ total_amount",
      "tolerance": 0.10  // Increase from 0.05
    }]
  }
}
```

---

## Performance

| Metric | Value |
|--------|-------|
| Per-document processing | < 2.5 seconds |
| Typical batch (4 docs) | < 15 seconds |
| Memory usage | < 50MB |
| Log file size (per doc) | ~2KB |

---

## Example Execution Transcript

```bash
$ python deterministic_pipeline.py

================================================================================
DETERMINISTIC PROCUREMENT EXTRACTION PIPELINE
================================================================================

Processing 4 document(s)

INFO: Starting document processing: invoice_001.pdf [a1b2_abc123]
INFO: Routing: procurement (confidence: 87%)
INFO: 📄 Procurement/Invoice Pipeline | Confidence: 45% | Validation: FAIL | Time: 2.34s
ERROR:   🔴 ERROR: CRITICAL: Missing field 'total_amount'
ERROR:   🔴 ERROR: CRITICAL: Missing field 'issue_date'
WARNING:   🟡 WARNING: Low extraction confidence: 45%

INFO: Starting document processing: spec_001.pdf [a1b2_def456]
INFO: Routing: specification (confidence: 78%)
INFO: 📋 Specification/Datasheet Pipeline | Confidence: 30% | Validation: PASS | Time: 1.89s
WARNING:   🟡 WARNING: Optional fields missing: supplier, invoice_or_po_number

...

================================================================================
PIPELINE EXECUTION SUMMARY
================================================================================

Session ID: a1b2c3d4
Duration: 14.32s

Statistics:
  Total Documents: 4
  ✅ Successful: 2
  🟡 Warnings: 1
  ❌ Failed: 1
  Success Rate: 50.0%
  Average Confidence: 42.5%
  Total Time: 8.56s

By Pipeline:
  • Procurement Pipeline: 2 document(s)
  • Specification Pipeline: 2 document(s)

================================================================================

✅ Procurement results: output/deterministic_procurement_20260624_150000.json
✅ Specification results: output/deterministic_specification_20260624_150000.json
✅ Combined results: output/deterministic_pipeline_20260624_150000.json

================================================================================
PROCESSING COMPLETE
================================================================================

Results Summary:
  Procurement documents: 2
  Specification documents: 2

Output files saved to: /path/to/output
Execution log: /path/to/logging/logs

================================================================================
```

---

## Integration with External Systems

### Read Results Programmatically

```python
import json
from pathlib import Path

# Load results
results_file = Path('output').glob('deterministic_pipeline_*.json')
with open(next(results_file)) as f:
    results = json.load(f)

# Filter procurement documents
procurement_docs = results['procurement_documents']

# Process only valid ones
for doc in procurement_docs:
    if doc['processing_status'] == 'valid':
        supplier = doc['supplier']
        po_number = doc['invoice_or_po_number']
        # Use in your system...
```

### Check Audit Trail

```python
# Load execution log
log_file = Path('logging/logs').glob('execution_*.json')
with open(next(log_file)) as f:
    audit = json.load(f)

# Find failed documents
for log in audit['execution_logs']:
    if log['status'] == 'FAILED':
        print(f"{log['document_name']}: {log['failure_reason']}")
```

---

**Status:** ✅ Production Ready  
**Version:** 1.0  
**Last Updated:** 2026-06-24
