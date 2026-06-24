"""
Example execution logs demonstrating the audit-grade logging system.
Shows both successful and failed document processing scenarios.
"""

import json
from datetime import datetime, timedelta


# EXAMPLE 1: Successful Procurement Document Processing
SUCCESSFUL_PROCUREMENT_LOG = {
    "session_id": "a1b2c3d4",
    "session_start": "2026-06-24T10:00:00",
    "session_duration_seconds": 45.23,
    "summary": {
        "total_documents": 4,
        "successful": 2,
        "warnings": 1,
        "failed": 1,
        "success_rate": "50.0%",
        "average_confidence": "52.5%",
        "total_processing_time": "12.45s"
    },
    "by_pipeline": {
        "Procurement Pipeline": 2,
        "Specification Pipeline": 2
    },
    "execution_logs": [
        {
            "execution_id": "a1b2c3d4_abc12345",
            "document_name": "invoice_001.pdf",
            "timestamp": "2026-06-24T10:00:05",
            "input_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "pipeline_version": "2.0",
            "pipeline_used": "Procurement Pipeline",
            "document_type": "procurement",
            "routing_decision": "procurement",
            "routing_confidence": 0.92,
            "extraction_confidence": 65.0,
            "extraction_method": "text_parser",
            "validation_result": "PASS",
            "validation_errors": [],
            "validation_warnings": [],
            "schema_validation_passed": True,
            "processing_time_seconds": 2.34,
            "status": "SUCCESS",
            "requires_review": False,
            "confidence_threshold": 70,
            "failure_reason": None,
            "failure_details": None,
            "extracted_fields": {
                "document_name": "invoice_001.pdf",
                "supplier": "Acme Corporation",
                "invoice_or_po_number": "INV-2026-001",
                "issue_date": "2026-06-20",
                "currency": "USD",
                "subtotal": 1000.00,
                "tax": 100.00,
                "total_amount": 1100.00,
                "line_items": [
                    {
                        "description": "Professional Services",
                        "quantity": 10,
                        "unit_price": 100.0,
                        "total_price": 1000.0,
                        "unit": "hours"
                    }
                ],
                "line_item_count": 1,
                "missing_fields": [],
                "processing_status": "valid"
            },
            "metadata": {
                "routing_confidence": 0.92,
                "enforcement_mode": "STRICT",
                "input_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "pipeline_version": "2.0",
                "extraction_method": "text_parser",
                "schema_validation_passed": True,
                "requires_review": False,
                "confidence_threshold": 70
            }
        },
        {
            "execution_id": "a1b2c3d4_def54321",
            "document_name": "spec_datasheet.pdf",
            "timestamp": "2026-06-24T10:00:10",
            "input_hash": "5d41402abc4b2a76b9719d911017c592",
            "pipeline_version": "2.0",
            "pipeline_used": "Specification Pipeline",
            "document_type": "specification",
            "routing_decision": "specification",
            "routing_confidence": 0.78,
            "extraction_confidence": 40.0,
            "extraction_method": "text_parser",
            "validation_result": "PASS",
            "validation_errors": [],
            "validation_warnings": [
                "Optional field missing: supplier",
                "Optional field missing: issue_date"
            ],
            "schema_validation_passed": True,
            "processing_time_seconds": 1.89,
            "status": "WARNING",
            "requires_review": True,
            "confidence_threshold": 70,
            "failure_reason": None,
            "failure_details": None,
            "extracted_fields": {
                "document_name": "spec_datasheet.pdf",
                "document_type": "specification",
                "supplier": None,
                "issue_date": None,
                "line_items": [
                    {
                        "description": "Operating Temperature Range",
                        "quantity": None,
                        "unit_price": None,
                        "unit": "celsius"
                    },
                    {
                        "description": "Power Consumption",
                        "quantity": 5,
                        "unit": "watts"
                    }
                ],
                "line_item_count": 2,
                "technical_specifications": {
                    "has_technical_requirements": True,
                    "detected_standards": ["IEC 61000"]
                },
                "processing_status": "valid"
            },
            "metadata": {
                "routing_confidence": 0.78,
                "enforcement_mode": "LENIENT",
                "input_hash": "5d41402abc4b2a76b9719d911017c592",
                "pipeline_version": "2.0",
                "extraction_method": "text_parser",
                "schema_validation_passed": True,
                "requires_review": True,
                "confidence_threshold": 70
            }
        },
        {
            "execution_id": "a1b2c3d4_ghi78901",
            "document_name": "po_purchase_order.pdf",
            "timestamp": "2026-06-24T10:00:15",
            "input_hash": "6512bd43d9caa6e02c990b0a82652dca",
            "pipeline_version": "2.0",
            "pipeline_used": "Procurement Pipeline",
            "document_type": "procurement",
            "routing_decision": "procurement",
            "routing_confidence": 0.87,
            "extraction_confidence": 45.0,
            "extraction_method": "text_parser",
            "validation_result": "FAIL",
            "validation_errors": [
                "CRITICAL: Missing field 'total_amount'",
                "CRITICAL: Missing field 'issue_date'",
                "Schema validation - total_amount: field required"
            ],
            "validation_warnings": [
                "Low extraction confidence: 45%",
                "Suspicious quantity detected (29783 units) in line item"
            ],
            "schema_validation_passed": False,
            "processing_time_seconds": 2.12,
            "status": "FAILED",
            "requires_review": True,
            "confidence_threshold": 70,
            "failure_reason": "CRITICAL: Missing field 'total_amount'",
            "failure_details": None,
            "extracted_fields": {
                "document_name": "po_purchase_order.pdf",
                "supplier": "Global Supplies Ltd",
                "invoice_or_po_number": "PO-2026-5234",
                "issue_date": None,
                "currency": "EUR",
                "subtotal": None,
                "tax": None,
                "total_amount": None,
                "line_items": [
                    {
                        "description": "Item A (with metadata)",
                        "quantity": 29783,
                        "unit_price": None,
                        "total_price": None
                    }
                ],
                "line_item_count": 1,
                "missing_fields": ["issue_date", "total_amount"],
                "processing_status": "invalid"
            },
            "metadata": {
                "routing_confidence": 0.87,
                "enforcement_mode": "STRICT",
                "input_hash": "6512bd43d9caa6e02c990b0a82652dca",
                "pipeline_version": "2.0",
                "extraction_method": "text_parser",
                "schema_validation_passed": False,
                "requires_review": True,
                "confidence_threshold": 70
            }
        },
        {
            "execution_id": "a1b2c3d4_jkl45678",
            "document_name": "scanned_invoice.pdf",
            "timestamp": "2026-06-24T10:00:22",
            "input_hash": "c51ce410c124a10e9237e5d6cb523375",
            "pipeline_version": "2.0",
            "pipeline_used": "Procurement Pipeline",
            "document_type": "procurement",
            "routing_decision": "procurement",
            "routing_confidence": 0.81,
            "extraction_confidence": 0.0,
            "extraction_method": "ocr_extract_failed_degraded",
            "validation_result": "FAIL",
            "validation_errors": [
                "Extraction failed: OCRExtractionError",
                "Using degraded/partial data - manual review required",
                "CRITICAL: Missing field 'supplier'",
                "CRITICAL: Missing field 'invoice_or_po_number'",
                "CRITICAL: Missing field 'total_amount'"
            ],
            "validation_warnings": [
                "Zero extraction confidence - document not processable"
            ],
            "schema_validation_passed": False,
            "processing_time_seconds": 5.67,
            "status": "FAILED",
            "requires_review": True,
            "confidence_threshold": 70,
            "failure_reason": "Extraction failed: OCRExtractionError",
            "failure_details": "Traceback (most recent call last):\n  File \"pipelines/procurement_pipeline.py\", line 123, in extract\n    result = ocr_extractor.extract(pdf_path)\nException: OCR failed to process image - insufficient contrast\n\nFallback to text extraction: No selectable text detected in PDF",
            "extracted_fields": {
                "document_name": "scanned_invoice.pdf",
                "supplier": None,
                "invoice_or_po_number": None,
                "issue_date": None,
                "currency": None,
                "subtotal": None,
                "tax": None,
                "total_amount": None,
                "line_items": [],
                "line_item_count": 0,
                "missing_fields": ["supplier", "invoice_or_po_number", "issue_date", "total_amount"],
                "extraction_method": "ocr_extract_degraded",
                "degradation_mode": True,
                "degradation_reason": "OCR failed to process image - insufficient contrast",
                "processing_status": "invalid"
            },
            "metadata": {
                "routing_confidence": 0.81,
                "enforcement_mode": "STRICT",
                "input_hash": "c51ce410c124a10e9237e5d6cb523375",
                "pipeline_version": "2.0",
                "extraction_method": "ocr_extract_failed_degraded",
                "schema_validation_passed": False,
                "requires_review": True,
                "confidence_threshold": 70,
                "failure_type": "extraction_failure",
                "failure_mode": "graceful_degradation"
            }
        }
    ]
}


# EXAMPLE 2: Batch Processing with Partial Failures
BATCH_PROCESSING_SUMMARY = {
    "session_id": "x9y8z7w6",
    "timestamp": "2026-06-24T11:30:00",
    "total_documents": 10,
    "by_pipeline": {
        "procurement": 6,
        "specification": 4
    },
    "batch_processing_safety": {
        "successful": 7,
        "failed": 2,
        "requires_review": 1,
        "total_attempted": 10,
        "partial_failure_note": "Batch completed with partial failures (not stopped by individual failures)"
    },
    "results": {
        "procurement": [
            {"document_name": "inv_001.pdf", "status": "SUCCESS"},
            {"document_name": "inv_002.pdf", "status": "SUCCESS"},
            {"document_name": "inv_003.pdf", "status": "REQUIRES_REVIEW"},
            {"document_name": "po_001.pdf", "status": "FAILED"},
        ],
        "specification": [
            {"document_name": "spec_001.pdf", "status": "SUCCESS"},
            {"document_name": "spec_002.pdf", "status": "SUCCESS"},
            {"document_name": "spec_003.pdf", "status": "SUCCESS"},
            {"document_name": "spec_004.pdf", "status": "FAILED"}
        ]
    }
}


# EXAMPLE 3: Audit Trail Record Format
AUDIT_TRAIL_RECORD = {
    "document_name": "critical_invoice.pdf",
    "processing_chain": [
        {
            "step": "file_intake",
            "timestamp": "2026-06-24T14:22:10",
            "input_hash": "f47ac10b58cc4edd6d54e59f9b9c85afc33d5593e1b09ed3c7c2a8c9d2f2f2f2",
            "file_size_bytes": 245823,
            "file_exists": True
        },
        {
            "step": "document_routing",
            "timestamp": "2026-06-24T14:22:11",
            "route_decision": "procurement",
            "route_confidence": 0.94,
            "route_keywords_matched": ["invoice", "factura", "total amount"],
            "extraction_signals": ["supplier_present", "pricing_present"]
        },
        {
            "step": "extraction",
            "timestamp": "2026-06-24T14:22:12",
            "method": "text_parser",
            "confidence": 78.5,
            "fields_extracted": 8,
            "fields_empty": 0,
            "extraction_time_ms": 645
        },
        {
            "step": "schema_validation",
            "timestamp": "2026-06-24T14:22:13",
            "validation_passed": True,
            "schema_version": "2.0",
            "fields_validated": ["supplier", "invoice_number", "total_amount"],
            "schema_errors": []
        },
        {
            "step": "business_rule_validation",
            "timestamp": "2026-06-24T14:22:14",
            "validation_mode": "STRICT",
            "math_checks_passed": True,
            "line_item_checks_passed": True,
            "confidence_threshold_check": True,
            "validation_errors": []
        },
        {
            "step": "final_decision",
            "timestamp": "2026-06-24T14:22:15",
            "final_status": "SUCCESS",
            "requires_review": False,
            "total_processing_time_ms": 5234
        }
    ],
    "summary": {
        "document": "critical_invoice.pdf",
        "route": "procurement",
        "confidence": 78.5,
        "status": "SUCCESS",
        "requires_review": False,
        "input_hash": "f47ac10b58cc4edd6d54e59f9b9c85afc33d5593e1b09ed3c7c2a8c9d2f2f2f2"
    }
}


def print_example_logs():
    """Print example logs to console"""
    print("\n" + "="*80)
    print("EXAMPLE 1: COMPLETE EXECUTION LOG (Successful + Failed)")
    print("="*80)
    print(json.dumps(SUCCESSFUL_PROCUREMENT_LOG, indent=2))
    
    print("\n" + "="*80)
    print("EXAMPLE 2: BATCH PROCESSING SUMMARY")
    print("="*80)
    print(json.dumps(BATCH_PROCESSING_SUMMARY, indent=2))
    
    print("\n" + "="*80)
    print("EXAMPLE 3: AUDIT TRAIL RECORD")
    print("="*80)
    print(json.dumps(AUDIT_TRAIL_RECORD, indent=2))


if __name__ == "__main__":
    print_example_logs()
