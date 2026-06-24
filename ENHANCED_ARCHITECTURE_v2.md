# Enhanced Deterministic Pipeline Architecture v2.0

## System Overview

The deterministic pipeline has been enhanced with:
- ✅ **Pydantic Schema Validation** - Strict type checking and field validation
- ✅ **Failure Recovery System** - Retries with exponential backoff and graceful degradation
- ✅ **Confidence Threshold Routing** - Automatic flagging of low-confidence documents
- ✅ **Batch Processing Safety** - Partial failures don't stop batch execution
- ✅ **Audit-Grade Logging** - Complete traceable lifecycle for every document

---

## Architecture Diagram v2.0

```
┌────────────────────────────────────────────────────────────────────┐
│                    BATCH INPUT: PDF Files                          │
│            (Independent transactions, partial failures OK)          │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              (File Hash)        (Validation Setup)
                    │                 │
                    ▼                 ▼
         ┌──────────────────┐   ┌─────────────────┐
         │ Input Hash (SHA) │   │ Schema Validator│
         │   for Audit      │   │  (Pydantic)     │
         └──────────────────┘   └─────────────────┘
                    │                 │
                    └────────┬────────┘
                             │
            ┌────────────────┴──────────────────┐
            │                                   │
            ▼                                   ▼
    ┌──────────────────┐             ┌─────────────────┐
    │ Document Router  │             │ Retry Config +  │
    │ (Deterministic)  │             │ Failure Recovery│
    │                  │             │                 │
    │ Scores:          │             │ - Retry Logic   │
    │ • Procurement    │             │ - Fallback      │
    │ • Specification  │             │ - Degradation   │
    └────────┬─────────┘             └─────────────────┘
             │
             │ routing_decision + confidence
             │
    ┌────────┴─────────────┐
    │                      │
    ▼                      ▼
┌─────────────┐    ┌──────────────┐
│ Procurement │    │ Specification│
│  Pipeline   │    │   Pipeline   │
│  (STRICT)   │    │  (LENIENT)   │
└──────┬──────┘    └───────┬──────┘
       │                   │
       ├─ Extract      (with retry + fallback)
       ├─ Validate     (schema + business rules)
       ├─ Check Confidence Threshold
       ├─ Apply Schema Validation (Pydantic)
       └─ Finalize
             │
             ▼
    ┌────────────────────┐
    │  Result with:      │
    │ • input_hash       │
    │ • pipeline_version │
    │ • extraction_conf  │
    │ • validation_result│
    │ • requires_review  │
    │ • failure_details  │
    │ • stack_trace      │
    └────────┬───────────┘
             │
    ┌────────┴────────────────┐
    │                         │
    ▼                         ▼
┌──────────┐            ┌───────────┐
│  Audit   │            │ Execution │
│  Logger  │            │   Report  │
│          │            │           │
│ • Hash   │            │ • Status  │
│ • Version│            │ • Errors  │
│ • Trace  │            │ • Summary │
└──────┬───┘            └─────┬─────┘
       │                      │
       └──────────┬───────────┘
                  │
            ┌─────┴─────┐
            │           │
            ▼           ▼
        ┌─────────────────────┐
        │ Output Files:       │
        │ • Procurement Results
        │ • Specification Results
        │ • Combined Results  │
        │ • Execution Log     │
        │   (JSON)            │
        └─────────────────────┘
```

---

## Component Details

### 1. Input Hash Calculation (Audit Trail)

```
SHA256("invoice.pdf") → e3b0c44298fc1c14...
```

**Purpose**: Verify file integrity and create immutable audit reference

**Location**: `base_pipeline._calculate_file_hash()`

**Usage**: Every execution log includes input_hash for traceability

---

### 2. Schema Validation Layer

```
ProcurementDocument (Pydantic Model)
├── Required fields:
│   ├── document_name: str (min_length=1)
│   ├── supplier: Optional[str]
│   ├── invoice_or_po_number: Optional[str]
│   ├── total_amount: Optional[float] (≥ 0)
│   └── extraction_confidence: float (0-100)
│
├── Validators:
│   ├── @validator('extraction_confidence')
│   ├── @validator('currency')
│   └── @validator('line_item_count')
│
└── Behavior:
    ├── Raises ValidationError on failure
    ├── Logs field-level errors
    └── Returns (document, errors) tuple
```

**Location**: `schemas/procurement_schema.py`, `schemas/schema_validator.py`

**Integration**: Applied in `base_pipeline._apply_schema_validation()`

---

### 3. Failure Recovery System

#### Retry Mechanism

```python
@with_retry_and_fallback(
    config=RetryConfig(
        max_retries=2,
        initial_delay=1.0,
        backoff_factor=2.0
    ),
    on_failure=fallback_to_text_extraction
)
def extract_with_ocr(pdf_path):
    ...
```

**Behavior**:
1. **Attempt 1**: Try primary method (OCR)
2. **Wait**: 1.0s delay
3. **Attempt 2**: Retry with full delay
4. **Wait**: 2.0s delay
5. **Attempt 3**: Final retry
6. **Fallback**: Switch to text extraction if all fail
7. **Degradation**: Return partial data if fallback fails

**Location**: `recovery/failure_recovery.py`

#### Graceful Degradation

```
OCR Failure → Fall Back to Text
     ↓
Text Failure → Return Partial Data
     ↓
Set confidence = 0.0
Set status = "FAILED"
Set requires_review = True
Flag for manual review
```

---

### 4. Confidence Threshold Routing

```python
if extraction_confidence < confidence_threshold:
    status = "REQUIRES_REVIEW"
    validation_warnings.append(
        f"Low confidence ({confidence:.0f}%) - marked for review"
    )
```

**Default Threshold**: 70%

**Behavior**:
- Document marked with `requires_review = True`
- Status changed to `REQUIRES_REVIEW`
- Excluded from automatic processing
- Logged with explicit flag in audit trail

**Configuration**: `config/validation_rules.json` → `global_settings.confidence_threshold_requires_review`

---

### 5. Batch Processing Safety

```python
for pdf_path in pdf_paths:
    try:
        result = process_single_document(pdf_path)
    except Exception as e:
        # Log error but CONTINUE
        logger.log_execution(..., status='FAILED')
        failed_count += 1
        # Next document processes
```

**Key Features**:
- Each document is independent transaction
- Failure doesn't stop batch
- Partial failures reported in summary
- All failures logged in audit trail

**Result Summary**:
```json
{
    "batch_processing_safety": {
        "successful": 7,
        "failed": 2,
        "requires_review": 1,
        "total_attempted": 10,
        "partial_failure_note": "Batch completed with partial failures"
    }
}
```

---

### 6. Audit-Grade Logging

```python
log_entry = ExecutionLog(
    # Identification
    execution_id="a1b2c3d4_abc12345",
    document_name="invoice_001.pdf",
    timestamp="2026-06-24T10:00:05",
    
    # Audit Trail
    input_hash="e3b0c44298fc1c14...",  # File integrity
    pipeline_version="2.0",             # Version tracking
    
    # Routing Decision
    routing_decision="procurement",
    routing_confidence=0.92,
    
    # Extraction Details
    extraction_confidence=65.0,
    extraction_method="text_parser",
    
    # Validation Results
    validation_result="PASS",
    validation_errors=[],
    validation_warnings=[],
    schema_validation_passed=True,
    
    # Processing Status
    status="SUCCESS",
    requires_review=False,
    confidence_threshold=70,
    processing_time_seconds=2.34,
    
    # Failure Details (if any)
    failure_reason=None,
    failure_details=None,  # Stack trace if exception
    
    # Extracted Data
    extracted_fields={...},
    metadata={
        'input_hash': '...',
        'pipeline_version': '2.0',
        'extraction_method': 'text_parser'
    }
)
```

**Location**: `logging/execution_logger.py` → `ExecutionLog` dataclass

**Output**: JSON with complete audit trail in `logging/logs/execution_*.json`

---

## Processing Flow (Detailed)

```
START: process_documents([pdf_list])
  │
  ├─ Batch Processing Loop (partial failure safe)
  │  │
  │  └─ For each PDF (independent transaction):
  │     │
  │     ├─ Calculate input_hash(SHA256)
  │     │
  │     ├─ Route Document
  │     │  └─ Score procurement vs specification
  │     │     └─ Return (route, confidence)
  │     │
  │     ├─ Select Pipeline
  │     │  └─ if route == 'procurement': use ProcurementPipeline
  │     │     else: use SpecificationPipeline
  │     │
  │     ├─ Extract Data
  │     │  ├─ Try primary method (text_parser or ocr)
  │     │  ├─ If fails: retry with backoff (max 2 retries)
  │     │  ├─ If still fails: fallback to alternate method
  │     │  └─ If all fail: return degraded data (conf=0)
  │     │
  │     ├─ Validate Data
  │     │  ├─ Check schema with Pydantic
  │     │  │  └─ If fails: add schema errors
  │     │  └─ Check business rules
  │     │     ├─ Field completeness (STRICT vs LENIENT)
  │     │     └─ Math consistency (if enabled)
  │     │
  │     ├─ Check Confidence Threshold
  │     │  ├─ if confidence < threshold (70%):
  │     │  │  ├─ Set requires_review = True
  │     │  │  └─ Status = "REQUIRES_REVIEW"
  │     │  └─ else: Continue
  │     │
  │     ├─ Finalize Output
  │     │  └─ Format for pipeline type
  │     │
  │     ├─ Log Execution
  │     │  ├─ Include input_hash
  │     │  ├─ Include pipeline_version
  │     │  ├─ Include extraction_confidence
  │     │  ├─ Include validation_result
  │     │  ├─ Include failure_details (if any)
  │     │  ├─ Include requires_review flag
  │     │  └─ Save to execution_log
  │     │
  │     └─ Store Result by Pipeline
  │        └─ results[route].append(result)
  │        (If exception: log and continue to next document)
  │
  ├─ Generate Execution Report
  │  └─ Aggregate stats, success rate, timing
  │
  ├─ Save Execution Log (JSON)
  │  └─ logging/logs/execution_YYYYMMDD_HHMMSS.json
  │
  ├─ Save Results Files
  │  ├─ output/deterministic_procurement_*.json
  │  ├─ output/deterministic_specification_*.json
  │  └─ output/deterministic_pipeline_*.json
  │
  └─ Return summary with:
     ├─ total_documents
     ├─ successful, failed, requires_review counts
     ├─ by_pipeline breakdown
     ├─ batch_processing_safety flags
     └─ execution_log_file path

END
```

---

## Output Files

### 1. Execution Log (Audit Trail)

`logging/logs/execution_20260624_100000.json`

```json
{
  "session_id": "a1b2c3d4",
  "session_start": "2026-06-24T10:00:00",
  "execution_logs": [
    {
      "execution_id": "a1b2c3d4_abc12345",
      "document_name": "invoice_001.pdf",
      "input_hash": "e3b0c44298fc1c14...",
      "pipeline_version": "2.0",
      "extraction_confidence": 65.0,
      "validation_result": "PASS",
      "status": "SUCCESS",
      "requires_review": false,
      "failure_details": null,
      "metadata": {
        "input_hash": "e3b0c44298fc1c14...",
        "pipeline_version": "2.0"
      }
    }
  ]
}
```

### 2. Results File (By Pipeline Type)

```json
[
  {
    "document_name": "invoice_001.pdf",
    "extraction_confidence": 65.0,
    "processing_status": "valid",
    "supplier": "Acme Corp",
    ...
  }
]
```

---

## Financial/Procurement Safety Guarantees

### ✅ No Silent Failures
Every failure logged with stack trace in `failure_details`

### ✅ No Unlogged Data Loss
Input hash tracks file integrity
All operations logged in audit trail

### ✅ Complete Document Lifecycle
From file intake through final decision:
```
file_hash → routing → extraction → validation → schema_check → final_decision
```

### ✅ Traceable Decisions
Every document processing decision includes:
- Who (which pipeline version)
- What (extraction method)
- Why (confidence score, routing logic)
- When (timestamp)
- Whether (success/failure with reason)
- How (complete stack trace if failed)

### ✅ Batch Processing Safety
Individual document failures don't affect others:
```
Doc1: SUCCESS ✅
Doc2: FAILED ❌ (doesn't stop batch)
Doc3: SUCCESS ✅
Doc4: REQUIRES_REVIEW ⚠️
Summary: 2/4 successful, 1 failed, 1 needs review
```

---

## Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| SUCCESS | No errors, within threshold | Ready for processing |
| WARNING | Warnings only, no errors | Check warnings but proceed |
| FAILED | Has critical errors | Manual review required |
| REQUIRES_REVIEW | Low confidence (<70%) | Route to human review |

---

## Error Scenarios & Handling

### Scenario 1: OCR Failure

```
OCR extraction fails
  ↓
Retry up to 2 times with backoff
  ↓
Fallback to text extraction
  ↓
Text extraction fails
  ↓
Return degraded data with confidence=0
  ↓
Mark as FAILED + requires_review
  ↓
Log complete failure details
```

### Scenario 2: Schema Validation Failure

```
Extract data
  ↓
Apply Pydantic schema
  ↓
Validation error: missing required field
  ↓
Add to validation_errors list
  ↓
Set schema_validation_passed=False
  ↓
Mark document as FAILED
  ↓
Log field-level errors
```

### Scenario 3: Low Confidence

```
Extract data: confidence=45%
  ↓
Check threshold: 45% < 70%
  ↓
Set requires_review=True
  ↓
Add warning: "Low confidence"
  ↓
Status=REQUIRES_REVIEW
  ↓
Flag in metadata and execution log
```

### Scenario 4: Batch Failure

```
Process Doc1: SUCCESS
  ↓
Process Doc2: FAILED (exception)
  ↓
Catch exception, log it
  ↓
DON'T STOP BATCH
  ↓
Process Doc3: SUCCESS
  ↓
Process Doc4: SUCCESS
  ↓
Summary: 3 successful, 1 failed
```

---

## Configuration

### Enable/Disable Schema Validation

`deterministic_pipeline.py`:
```python
self.procurement_pipeline = ProcurementPipeline(
    rules_config,
    pipeline_config,
    logger,
    enable_schema_validation=True  # Set to False to disable
)
```

### Adjust Confidence Threshold

`config/validation_rules.json`:
```json
{
  "global_settings": {
    "confidence_threshold_requires_review": 70
  }
}
```

### Customize Retry Behavior

`recovery/failure_recovery.py`:
```python
config = RetryConfig(
    max_retries=2,           # Increase for more retries
    initial_delay=1.0,       # Increase for longer delays
    backoff_factor=2.0,      # Exponential backoff
    fallback_enabled=True    # Enable fallback strategy
)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-24 | Initial deterministic pipeline |
| 2.0 | 2026-06-24 | Schema validation, failure recovery, audit logging |

---

**Status**: ✅ Production Ready with Financial-Grade Safety

