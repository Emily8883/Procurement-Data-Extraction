# Deterministic Pipeline v2.0 - Quick Reference Card

## 5 Major Enhancements - All Complete ✅

### 1. Schema Validation (Pydantic) ✅

**What it does**: Enforces strict type checking and field constraints

**Files**:
- `schemas/procurement_schema.py` - Pydantic models
- `schemas/schema_validator.py` - Validation logic

**Features**:
- Type checking for all fields
- Field constraints (min/max, patterns)
- Detailed error logging
- Automatic field validation

**Usage**:
```python
validator.validate_procurement_document(data, 'invoice.pdf')
# Returns: (valid_document, errors_dict)
```

---

### 2. Failure Recovery ✅

**What it does**: Retry extraction with fallback and graceful degradation

**Files**:
- `recovery/failure_recovery.py` - Retry decorator + recovery

**Features**:
- Max 2 retries with exponential backoff (1s, 2s)
- Fallback to text extraction if OCR fails
- Graceful degradation on complete failure
- Full recovery attempt logging

**Flow**:
```
Try OCR → Wait 1s → Retry → Wait 2s → Retry
  → Fallback to Text
    → Degraded output (confidence=0)
```

---

### 3. Confidence Threshold ✅

**What it does**: Flag low-confidence documents for manual review

**Configuration**:
```json
{
  "global_settings": {
    "confidence_threshold_requires_review": 70  // Default
  }
}
```

**Behavior**:
```
if confidence < 70%:
  → requires_review = True
  → status = "REQUIRES_REVIEW"
  → Excluded from auto-processing
```

---

### 4. Batch Safety ✅

**What it does**: Partial failures don't stop entire batch

**Key Feature**: Each document is independent transaction

**Example**:
```
10 PDFs: 7 successful, 2 failed, 1 requires_review
Status: BATCH COMPLETED (failures didn't stop processing)
```

**Summary Field**:
```json
{
  "batch_processing_safety": {
    "successful": 7,
    "failed": 2,
    "requires_review": 1,
    "total_attempted": 10
  }
}
```

---

### 5. Audit Logging ✅

**What it does**: Complete traceable lifecycle for every document

**New Fields**:
| Field | Example | Purpose |
|-------|---------|---------|
| `input_hash` | `e3b0c442...` | File integrity (SHA256) |
| `pipeline_version` | `2.0` | Track which version used |
| `extraction_confidence` | `65.0` | Quality metric 0-100 |
| `extraction_method` | `text_parser` | Which extraction method |
| `validation_result` | `PASS` | Pass/Fail/Warning |
| `schema_validation_passed` | `true` | Pydantic validation result |
| `requires_review` | `false` | Manual review needed? |
| `confidence_threshold` | `70` | Threshold used |
| `failure_details` | `Traceback...` | Full stack trace if error |

**Example Log**:
```json
{
  "document_name": "invoice.pdf",
  "input_hash": "e3b0c442...",
  "pipeline_version": "2.0",
  "extraction_confidence": 65.0,
  "validation_result": "PASS",
  "schema_validation_passed": true,
  "status": "SUCCESS",
  "requires_review": false,
  "failure_details": null,
  "timestamp": "2026-06-24T10:00:05"
}
```

---

## File Inventory

### NEW (Created for v2.0)

```
schemas/
├── __init__.py
├── procurement_schema.py ............ Pydantic models
└── schema_validator.py ............. Validation wrapper

recovery/
├── __init__.py
└── failure_recovery.py ............. Retry + recovery

examples/
├── __init__.py
└── example_execution_logs.py ....... Example logs

Documentation:
├── ENHANCED_ARCHITECTURE_v2.md ..... Detailed architecture
├── ENHANCED_IMPLEMENTATION_GUIDE.md  Step-by-step guide
└── IMPLEMENTATION_COMPLETE_v2.0.txt  Completion summary
```

### MODIFIED (Enhanced for v2.0)

```
pipelines/base_pipeline.py
├── Added: _calculate_file_hash() method
├── Added: _apply_schema_validation() method
├── Added: confidence_threshold property
├── Added: requires_review flag logic
├── Added: pipeline_version constant
└── Enhanced: process_document() with new fields

deterministic_pipeline.py
├── Enhanced: process_documents() with batch safety
├── Enhanced: process_single_document() with audit fields
├── Added: per-document exception handling
└── Added: requires_review routing

logging/execution_logger.py
├── Enhanced: ExecutionLog dataclass with audit fields
├── Added: input_hash field
├── Added: pipeline_version field
├── Added: extraction_method field
├── Added: schema_validation_passed field
├── Added: requires_review field
├── Added: confidence_threshold field
└── Enhanced: failure_details for stack traces
```

---

## Quick Start

### Install Dependencies
```bash
pip install pydantic
```

### Run Pipeline
```bash
python deterministic_pipeline.py
```

### Check Results
```bash
# Execution log with audit trail
cat logging/logs/execution_*.json | jq .

# Results by type
cat output/deterministic_procurement_*.json
cat output/deterministic_specification_*.json
```

### View Example Logs
```bash
python examples/example_execution_logs.py
```

---

## Output Locations

| What | Where |
|------|-------|
| Execution logs (audit trail) | `logging/logs/execution_*.json` |
| Procurement results | `output/deterministic_procurement_*.json` |
| Specification results | `output/deterministic_specification_*.json` |
| Combined results | `output/deterministic_pipeline_*.json` |
| Schema validation failures | `logging/validation_errors/` |
| Degradation logs | `logging/degradation_logs/` |

---

## Safety Guarantees

✅ **No Silent Failures**
- Every failure logged with stack trace
- failure_details field contains full traceback

✅ **No Unlogged Data Loss**
- input_hash tracks file integrity
- All operations timestamped
- Complete audit trail saved

✅ **Complete Lifecycle Traceability**
- From file intake through final decision
- Every stage logged with metadata

✅ **Zero Ambiguity**
- All decisions rule-based
- Routing deterministic
- Validation configurable

✅ **Batch Processing Integrity**
- Partial failures don't stop processing
- Each document independent
- Full failure summary generated

---

## Configuration Options

### Confidence Threshold
```json
// config/validation_rules.json
"global_settings": {
  "confidence_threshold_requires_review": 70
}
```

### Enable/Disable Schema Validation
```python
# deterministic_pipeline.py
enable_schema_validation=True  # or False
```

### Retry Behavior
```python
# recovery/failure_recovery.py
config = RetryConfig(
    max_retries=2,           # Number of retries
    initial_delay=1.0,       # Initial wait (seconds)
    backoff_factor=2.0,      # Exponential multiplier
    fallback_enabled=True    # Enable fallback
)
```

---

## Status Codes

| Status | Meaning |
|--------|---------|
| `SUCCESS` | No errors, confidence OK |
| `WARNING` | Warnings only, no errors |
| `FAILED` | Critical errors detected |
| `REQUIRES_REVIEW` | Low confidence (<threshold) |

---

## Example Scenarios

### Scenario 1: Successful Processing
```
Input: invoice_001.pdf (clear, text-based)
Extraction: 85% confidence
Validation: PASS
Schema: Valid
Status: SUCCESS ✅
```

### Scenario 2: Low Confidence
```
Input: scanned_invoice.pdf (poor quality)
Extraction: 45% confidence
Threshold: 70%
Status: REQUIRES_REVIEW ⚠️
Action: Routed to human queue
```

### Scenario 3: Schema Failure
```
Input: po.pdf (missing critical field)
Extraction: 60% confidence
Schema: total_amount field required
Status: FAILED ❌
Action: Flag for manual data entry
```

### Scenario 4: OCR Failure → Fallback
```
Input: damaged.pdf (scanned, damaged)
Try OCR: FAILS
Retry 1: FAILS (wait 1s)
Retry 2: FAILS (wait 2s)
Fallback: Text extraction SUCCEEDS (partial)
Status: FAILED with partial data
Action: Manual review + data completion
```

### Scenario 5: Batch with Mixed Results
```
PDFs: 10 files
Results:
  - Successful: 7 ✅
  - Failed: 2 ❌
  - Requires Review: 1 ⚠️
Summary: Batch completed despite 3 issues
All failures logged with full details
```

---

## Monitoring & Troubleshooting

### Check What Happened to a Document
```bash
# Find in execution log
cat logging/logs/execution_*.json | jq '.execution_logs[] | select(.document_name=="invoice.pdf")'
```

### View Failures
```bash
# All failed documents
cat logging/logs/execution_*.json | jq '.execution_logs[] | select(.status=="FAILED")'
```

### Schema Validation Errors
```bash
# Check validation failures
ls logging/validation_errors/
cat logging/validation_errors/validation_failure_*.json
```

### Degradation Events
```bash
# Check extraction fallbacks
ls logging/degradation_logs/
cat logging/degradation_logs/degradation_*.json
```

---

## Version Info

| Aspect | Value |
|--------|-------|
| Pipeline Version | 2.0 |
| Release Date | 2026-06-24 |
| Status | ✅ Production Ready |
| Safety Level | Financial Grade |

---

## Support Docs

1. **[ENHANCED_ARCHITECTURE_v2.md](ENHANCED_ARCHITECTURE_v2.md)** - Detailed architecture
2. **[ENHANCED_IMPLEMENTATION_GUIDE.md](ENHANCED_IMPLEMENTATION_GUIDE.md)** - Implementation details
3. **[IMPLEMENTATION_COMPLETE_v2.0.txt](IMPLEMENTATION_COMPLETE_v2.0.txt)** - Completion summary
4. **[examples/example_execution_logs.py](examples/example_execution_logs.py)** - Example logs

---

**All 5 Tasks Complete & Production Ready ✅**
