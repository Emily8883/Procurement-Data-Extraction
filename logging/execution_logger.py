#!/usr/bin/env python3
"""
Execution Logging System for Deterministic Pipeline

Logs all pipeline execution details in JSON format for complete auditability
and reproducibility. Every document processing decision is recorded.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import uuid


@dataclass
class ExecutionLog:
    """Single document execution log entry - Audit Grade"""
    
    # Basic identification (required)
    execution_id: str
    document_name: str
    timestamp: str
    pipeline_used: str
    document_type: str
    extraction_confidence: float
    validation_result: str  # PASS, FAIL, WARNING
    validation_errors: List[str]
    validation_warnings: List[str]
    processing_time_seconds: float
    status: str  # SUCCESS, FAILED, WARNING, REQUIRES_REVIEW
    
    # Audit trail (optional)
    input_hash: Optional[str] = None  # SHA256 for file integrity
    pipeline_version: Optional[str] = None  # Version of pipeline used
    extraction_method: Optional[str] = None  # text_parser, ocr_extract, etc.
    
    # Pipeline routing (optional)
    routing_decision: Optional[str] = None
    routing_confidence: Optional[float] = None
    
    # Validation (optional)
    schema_validation_passed: Optional[bool] = None
    
    # Processing status (optional)
    requires_review: Optional[bool] = None
    confidence_threshold: Optional[int] = None
    
    # Failure details (optional, with stack traces if applicable)
    failure_reason: Optional[str] = None
    failure_details: Optional[str] = None  # Full stack trace if exception
    
    # Data extraction (optional)
    extracted_fields: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class PipelineLogger:
    """Deterministic execution logger for pipeline processing"""
    
    def __init__(self, log_dir: Path = None):
        """Initialize logger"""
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / 'logging' / 'logs'
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.execution_logs: List[ExecutionLog] = []
        self.session_id = str(uuid.uuid4())[:8]
        self.session_start = datetime.now()
        
        # Setup Python logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure Python logging"""
        self.logger = logging.getLogger('PipelineLogger')
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
    
    def log_document_start(self, document_name: str) -> str:
        """Log document processing start"""
        execution_id = f"{self.session_id}_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()
        
        self.logger.info(
            f"Starting document processing: {document_name} "
            f"[{execution_id}]"
        )
        
        return execution_id
    
    def log_execution(
        self,
        execution_id: str,
        document_name: str,
        pipeline_used: str,
        document_type: str,
        extraction_confidence: float,
        validation_result: str,
        validation_errors: List[str],
        validation_warnings: List[str],
        processing_time_seconds: float,
        status: str,
        failure_reason: Optional[str] = None,
        failure_details: Optional[str] = None,
        routing_decision: Optional[str] = None,
        routing_confidence: Optional[float] = None,
        extracted_fields: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        input_hash: Optional[str] = None,
        pipeline_version: Optional[str] = None,
        extraction_method: Optional[str] = None,
        schema_validation_passed: Optional[bool] = None,
        requires_review: Optional[bool] = None,
        confidence_threshold: Optional[int] = None
    ) -> ExecutionLog:
        """Log complete execution for a document with audit-grade details"""
        
        log_entry = ExecutionLog(
            execution_id=execution_id,
            document_name=document_name,
            timestamp=datetime.now().isoformat(),
            input_hash=input_hash,
            pipeline_version=pipeline_version,
            pipeline_used=pipeline_used,
            document_type=document_type,
            routing_decision=routing_decision,
            routing_confidence=routing_confidence,
            extraction_confidence=extraction_confidence,
            extraction_method=extraction_method,
            validation_result=validation_result,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            schema_validation_passed=schema_validation_passed,
            processing_time_seconds=processing_time_seconds,
            status=status,
            requires_review=requires_review,
            confidence_threshold=confidence_threshold,
            failure_reason=failure_reason,
            failure_details=failure_details,
            extracted_fields=extracted_fields,
            metadata=metadata
        )
        
        self.execution_logs.append(log_entry)
        
        # Log to console with status
        status_icon = {
            "SUCCESS": "✅",
            "WARNING": "🟡",
            "FAILED": "❌",
            "REQUIRES_REVIEW": "🔶"
        }.get(status, "❓")
        
        confidence_str = f"{extraction_confidence:.0f}%"
        
        self.logger.info(
            f"{status_icon} {document_name}: {pipeline_used} | "
            f"Confidence: {confidence_str} | "
            f"Validation: {validation_result} | "
            f"Time: {processing_time_seconds:.2f}s"
        )
        
        # Log errors if present
        if validation_errors:
            for error in validation_errors:
                self.logger.error(f"  🔴 ERROR: {error}")
        
        # Log warnings if present
        if validation_warnings:
            for warning in validation_warnings:
                self.logger.warning(f"  🟡 WARNING: {warning}")
        
        # Log requires_review flag
        if requires_review:
            self.logger.warning(
                f"  ⚠️  REQUIRES REVIEW: Confidence {confidence_str} below threshold {confidence_threshold}%"
            )
        
        if failure_reason:
            self.logger.error(f"  Failure: {failure_reason}")
        
        return log_entry
    
    def generate_execution_report(self) -> Dict[str, Any]:
        """Generate complete execution report"""
        
        total_documents = len(self.execution_logs)
        successful = sum(1 for log in self.execution_logs if log.status == "SUCCESS")
        warnings = sum(1 for log in self.execution_logs if log.status == "WARNING")
        failed = sum(1 for log in self.execution_logs if log.status == "FAILED")
        
        pipeline_counts = {}
        for log in self.execution_logs:
            pipeline_counts[log.pipeline_used] = pipeline_counts.get(log.pipeline_used, 0) + 1
        
        avg_confidence = (
            sum(log.extraction_confidence for log in self.execution_logs) / 
            total_documents if total_documents > 0 else 0
        )
        
        total_time = sum(log.processing_time_seconds for log in self.execution_logs)
        
        return {
            "session_id": self.session_id,
            "session_start": self.session_start.isoformat(),
            "session_duration_seconds": (datetime.now() - self.session_start).total_seconds(),
            "summary": {
                "total_documents": total_documents,
                "successful": successful,
                "warnings": warnings,
                "failed": failed,
                "success_rate": f"{100 * successful / total_documents:.1f}%" if total_documents > 0 else "N/A",
                "average_confidence": f"{avg_confidence:.1f}%",
                "total_processing_time": f"{total_time:.2f}s"
            },
            "by_pipeline": pipeline_counts,
            "execution_logs": [asdict(log) for log in self.execution_logs]
        }
    
    def save_execution_log(self, output_path: Optional[Path] = None) -> Path:
        """Save execution log to JSON file"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.log_dir / f"execution_{timestamp}.json"
        
        report = self.generate_execution_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Execution log saved: {output_path}")
        return output_path
    
    def print_session_summary(self):
        """Print execution summary to console"""
        if not self.execution_logs:
            print("No execution logs recorded")
            return
        
        report = self.generate_execution_report()
        
        print(f"\n{'='*80}")
        print("PIPELINE EXECUTION SUMMARY")
        print(f"{'='*80}\n")
        
        print(f"Session ID: {report['session_id']}")
        print(f"Duration: {report['session_duration_seconds']:.2f}s\n")
        
        summary = report['summary']
        print("Statistics:")
        print(f"  Total Documents: {summary['total_documents']}")
        print(f"  ✅ Successful: {summary['successful']}")
        print(f"  🟡 Warnings: {summary['warnings']}")
        print(f"  ❌ Failed: {summary['failed']}")
        print(f"  Success Rate: {summary['success_rate']}")
        print(f"  Average Confidence: {summary['average_confidence']}")
        print(f"  Total Time: {summary['total_processing_time']}\n")
        
        if report['by_pipeline']:
            print("By Pipeline:")
            for pipeline, count in report['by_pipeline'].items():
                print(f"  • {pipeline}: {count} document(s)")
        
        print(f"\n{'='*80}\n")


def get_logger(log_dir: Path = None) -> PipelineLogger:
    """Factory function to get logger instance"""
    return PipelineLogger(log_dir)
