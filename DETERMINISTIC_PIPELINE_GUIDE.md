# Deterministic Procurement Extraction Pipeline

## Overview

This is a production-grade, deterministic pipeline system for procurement document extraction with **zero ambiguous decisions**. Everything is rule-based, configurable, and fully auditable through execution logging.

### Key Principles

✅ **Deterministic** - Same input always produces same output  
✅ **Auditable** - Complete execution log for every document  
✅ **Configurable** - All rules in `config/validation_rules.json`  
✅ **No Manual Options** - Routing and validation fully automated  
✅ **Explainable** - Logs contain complete decision rationale  

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  deterministic_pipeline.py (Main Entry Point)           │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   ┌──────────┐    ┌───────────┐
   │  Router  │    │   Logger  │
   └────┬─────┘    └───────────┘
        │
        ├─────────────────┬──────────────────┐
        ▼                 ▼                  ▼
   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
   │ Procurement │  │Specification │  │ Base Pipeline│
   │ Pipeline    │  │ Pipeline     │  │ (Abstract)   │
   └─────────────┘  └──────────────┘  └──────────────┘
        │                 │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   config/          logging/logs/
   validation_rules.json  execution_*.json
```

---

## File Structure

```
📁 Workspace Root
├── config/
│   ├── validation_rules.json ........... Rules for both pipelines
│   └── pipeline_config.json ........... Execution configuration
│
├── pipelines/
│   ├── __init__.py
│   ├── base_pipeline.py .............. Abstract base class
│   ├── procurement_pipeline.py ........ Procurement/invoice pipeline
│   ├── specification_pipeline.py ...... Specification/datasheet pipeline
│   └── document_router.py ............ Rule-based document router
│
├── logging/
│   ├── __init__.py
│   ├── execution_logger.py ........... Execution logging system
│   └── logs/ ........................ JSON execution logs
│
├── deterministic_pipeline.py ......... Main orchestrator (ENTRY POINT)
└── output/ .......................... Results directory
    ├── deterministic_procurement_*.json
    ├── deterministic_specification_*.json
    └── deterministic_pipeline_*.json
```

---

## Execution Flow

### 1. Document Routing (Deterministic)

```python
router = DocumentTypeRouter(rules_config)
pipeline_type, confidence = router.route_document(pdf_path)
# Returns: ('procurement', 0.85) or ('specification', 0.72)
```

**Decision Logic:**
- Analyzes document text and extracted fields
- Scores likelihood of procurement vs specification
- Uses keyword matching, field presence, text patterns
- No manual intervention required

**Fallback Rules** (if tied):
1. Has explicit supplier → procurement
2. Has explicit pricing → procurement
3. Has explicit technical requirements → specification
4. No pricing data → specification
5. Default → procurement (configurable)

---

### 2. Pipeline Selection

```python
if pipeline_type == 'procurement':
    pipeline = ProcurementPipeline(...)
else:
    pipeline = SpecificationPipeline(...)
```

**Procurement Pipeline:**
- STRICT validation mode
- Requires: supplier, invoice_or_po_number, issue_date, total_amount
- Validates math: subtotal + tax ≈ total_amount
- Enforces per-line-item accuracy

**Specification Pipeline:**
- LENIENT validation mode
- Requires: document_name, line_items only
- Pricing optional (specs don't have prices)
- Allows warnings but not errors

---

### 3. Document Processing

```python
result = pipeline.process_document(pdf_path)
```

**Stages:**
1. Extract - Get data from document
2. Validate - Check against rules
3. Finalize - Format output for pipeline type
4. Log - Record all decisions

---

### 4. Execution Logging

```python
logger.log_execution(
    execution_id="abc123",
    document_name="invoice_001.pdf",
    pipeline_used="Procurement Pipeline",
    extraction_confidence=45.0,
    validation_result="FAIL",
    validation_errors=["Missing total_amount"],
    validation_warnings=[...],
    processing_time_seconds=2.34,
    status="FAILED",
    routing_decision="procurement",
    routing_confidence=0.85,
    ...
)
```

**Output:** JSON execution log with complete decision trail

---

## Configuration

### `config/validation_rules.json`

**Procurement Pipeline Rules:**
```json
{
  "procurement_pipeline": {
    "field_completeness": {
      "critical_fields": [
        "supplier",
        "invoice_or_po_number",
        "issue_date",
        "total_amount"
      ],
      "enforcement": "STRICT"
    },
    "math_validation": {
      "enabled": true,
      "checks": [
        {
          "formula": "subtotal + tax ≈ total_amount",
          "tolerance": 0.05
        }
      ]
    },
    "pass_criteria": {
      "allow_warnings": false,
      "allow_errors": false
    }
  }
}
```

**Specification Pipeline Rules:**
```json
{
  "specification_pipeline": {
    "field_completeness": {
      "critical_fields": ["document_name", "line_items"],
      "optional_fields": ["supplier", "issue_date", "total_amount"],
      "enforcement": "LENIENT"
    },
    "math_validation": {
      "enabled": false
    },
    "pass_criteria": {
      "allow_warnings": true,
      "allow_errors": false
    }
  }
}
```

---

## Usage

### Run Complete Pipeline

```bash
python deterministic_pipeline.py
```

**Output:**
- `output/deterministic_procurement_YYYYMMDD_HHMMSS.json`
- `output/deterministic_specification_YYYYMMDD_HHMMSS.json`
- `output/deterministic_pipeline_YYYYMMDD_HHMMSS.json` (combined)
- `logging/logs/execution_YYYYMMDD_HHMMSS.json` (full audit trail)

### Programmatic Usage

```python
from deterministic_pipeline import DeterministicPipeline

# Initialize
pipeline = DeterministicPipeline()

# Process documents
results = pipeline.process_documents([
    'pdfs/invoice_001.pdf',
    'pdfs/spec_product_a.pdf'
])

# Save results
output_files = pipeline.save_results()

# Review results
print(f"Procurement: {results['by_pipeline']['procurement']}")
print(f"Specifications: {results['by_pipeline']['specification']}")
```

### Access Execution Log

```python
# Get complete execution record
execution_log = pipeline.logger.generate_execution_report()

# Print summary
pipeline.logger.print_session_summary()

# Save for audit
pipeline.logger.save_execution_log(Path('my_audit.json'))
```

---

## Execution Log Structure

```json
{
  "session_id": "a1b2c3d4",
  "session_start": "2026-06-24T15:00:00",
  "session_duration_seconds": 45.23,
  "summary": {
    "total_documents": 4,
    "successful": 2,
    "warnings": 1,
    "failed": 1,
    "success_rate": "50.0%",
    "average_confidence": "42.5%"
  },
  "by_pipeline": {
    "Procurement Pipeline": 2,
    "Specification Pipeline": 2
  },
  "execution_logs": [
    {
      "execution_id": "a1b2c3d4_abc123",
      "document_name": "invoice_001.pdf",
      "timestamp": "2026-06-24T15:00:10",
      "pipeline_used": "Procurement Pipeline",
      "document_type": "procurement",
      "extraction_confidence": 45.0,
      "validation_result": "FAIL",
      "validation_errors": ["CRITICAL: Missing field 'total_amount'"],
      "validation_warnings": [],
      "processing_time_seconds": 2.34,
      "status": "FAILED",
      "routing_decision": "procurement",
      "routing_confidence": 0.87,
      "metadata": {...}
    },
    ...
  ]
}
```

---

## Output Schema

### Procurement Document Output

```json
{
  "document_name": "invoice_001.pdf",
  "document_type": "invoice_or_po",
  "pipeline": "procurement",
  "processing_status": "valid",
  "extraction_confidence": 45.0,
  
  "supplier": "Y SU PERSONAL",
  "invoice_or_po_number": "S600100040138",
  "issue_date": "",
  "currency": "PEN",
  
  "subtotal": "",
  "tax": "",
  "total_amount": "",
  
  "line_items": [...],
  "line_item_count": 15,
  
  "missing_fields": ["issue_date", "total_amount"],
  "extraction_method": "text_parser"
}
```

### Specification Document Output

```json
{
  "document_name": "spec_001.pdf",
  "document_type": "specification",
  "pipeline": "specification",
  "processing_status": "valid",
  "extraction_confidence": 30.0,
  
  "supplier": "",
  "invoice_or_po_number": "",
  "issue_date": "",
  "currency": "",
  
  "line_items": [...],
  "line_item_count": 15,
  
  "technical_specifications": {
    "has_technical_requirements": true
  },
  
  "missing_fields": ["supplier", "issue_date"],
  "extraction_method": "text_parser"
}
```

---

## Validation Rules

### Procurement Pipeline Rules

| Rule | Enforcement | Failure? |
|------|-------------|----------|
| All critical fields present | STRICT | YES |
| subtotal + tax ≈ total_amount (±5%) | STRICT | YES |
| quantity × unit_price ≈ total_price (±5%) | STRICT | WARNING |
| Confidence ≥ 30% | LENIENT | WARNING |

### Specification Pipeline Rules

| Rule | Enforcement | Failure? |
|------|-------------|----------|
| document_name + line_items present | STRICT | YES |
| Supplier/date/pricing optional | LENIENT | WARNING |
| No math validation | N/A | N/A |
| Technical content detected | LENIENT | WARNING |
| Confidence ≥ 20% | LENIENT | WARNING |

---

## Decision Logging Examples

### Example 1: Procurement Document Processing

```
INFO: Starting document processing: invoice_001.pdf [a1b2_abc123]
INFO: Routing: procurement (confidence: 87%)
INFO: Pipeline: Procurement Pipeline
INFO: Extraction: 45% confidence
ERROR: 🔴 ERROR: CRITICAL: Missing field 'total_amount'
ERROR: 🔴 ERROR: CRITICAL: Missing field 'issue_date'
WARNING: 🟡 WARNING: Line 12: Suspicious quantity (29783) - likely metadata
INFO: Status: FAILED (2 critical errors)
INFO: Processing time: 2.34s
```

**Execution Log Entry:**
```json
{
  "execution_id": "a1b2_abc123",
  "document_name": "invoice_001.pdf",
  "pipeline_used": "Procurement Pipeline",
  "validation_result": "FAIL",
  "status": "FAILED",
  "routing_decision": "procurement",
  "routing_confidence": 0.87,
  "validation_errors": [
    "CRITICAL: Missing field 'total_amount'",
    "CRITICAL: Missing field 'issue_date'"
  ]
}
```

---

## Error Handling

### Deterministic Fallbacks

1. **If extraction fails** → Log error, continue to validation
2. **If validation fails** → Mark as FAILED, log reasons
3. **If routing ambiguous** → Use override rules
4. **If no errors but warnings** → PROCUREMENT = FAIL, SPECIFICATION = PASS

---

## Extensibility

### Adding New Document Type

1. Create `new_type_pipeline.py`:
   ```python
   class NewTypePipeline(BasePipeline):
       def _get_pipeline_name(self): return "New Type Pipeline"
       def _get_pipeline_type(self): return "new_type"
       def extract(self, pdf_path): ...
       def validate(self, data): ...
       def finalize(self, data, validation_result): ...
   ```

2. Add rules to `validation_rules.json`:
   ```json
   {
     "new_type_pipeline": {
       "field_completeness": {...},
       "pass_criteria": {...}
     }
   }
   ```

3. Update `document_router.py` with keywords

4. Register in `deterministic_pipeline.py`:
   ```python
   self.new_type_pipeline = NewTypePipeline(...)
   if routing_decision == 'new_type':
       pipeline = self.new_type_pipeline
   ```

---

## Audit Trail

Every document processing decision is recorded in JSON:

```bash
cat logging/logs/execution_20260624_150000.json | jq '.execution_logs[0]'
```

Shows:
- What pipeline was selected and why
- What extraction confidence was achieved
- What validation rules were checked
- Which rules failed and which passed
- Processing time
- Complete failure rationale

---

## Testing

### Test Deterministic Routing

```python
from pipelines.document_router import DocumentTypeRouter

router = DocumentTypeRouter(rules_config)
pipeline_type, confidence = router.route_document('test.pdf')

# Should be consistent for same document
assert router.route_document('test.pdf')[0] == pipeline_type
```

### Test Pipeline Reproducibility

```python
# Same input → Same output every time
result1 = pipeline.process_document('invoice.pdf')
result2 = pipeline.process_document('invoice.pdf')

assert result1 == result2
```

---

## FAQ

**Q: Why different pipelines?**  
A: Procurement and specifications have fundamentally different requirements. Invoices need pricing (STRICT). Specifications don't (LENIENT). One validation rule can't work for both.

**Q: What if routing is wrong?**  
A: Execution log shows routing decision and confidence. Adjust routing keywords in `validation_rules.json` or override rules.

**Q: Can I modify validation at runtime?**  
A: No - that defeats determinism. Change `config/validation_rules.json` and restart.

**Q: How do I debug failed documents?**  
A: Check execution log for routing decision, extraction confidence, validation errors. All decisions are logged.

**Q: Can the system auto-correct values?**  
A: No - the system detects and flags only. No data modification.

---

## Status

✅ **Production Ready**

- Zero manual decisions
- Complete execution logging
- Rule-based deterministic routing
- Configurable validation rules
- Full audit trail
- Reproducible results

---

**Last Updated:** 2026-06-24  
**Version:** 1.0  
**Status:** Complete
