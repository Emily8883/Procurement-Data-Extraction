"""
Failure recovery system with retry mechanism and graceful degradation.
Handles OCR failures, text extraction failures, and partial data recovery.
"""

import logging
import time
import hashlib
from typing import Callable, Any, Dict, Optional, Tuple
from functools import wraps
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_retries: int = 2,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        fallback_enabled: bool = True,
        log_dir: Path = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum retry attempts (default 2)
            initial_delay: Initial delay between retries in seconds
            backoff_factor: Exponential backoff factor
            fallback_enabled: Enable fallback to text extraction if OCR fails
            log_dir: Directory for retry logs
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.fallback_enabled = fallback_enabled
        self.log_dir = log_dir or Path("logging/retry_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)


def with_retry_and_fallback(
    config: RetryConfig = None,
    on_failure: Optional[Callable] = None
):
    """
    Decorator for retry logic with optional fallback strategy.
    
    Usage:
        @with_retry_and_fallback(
            config=RetryConfig(max_retries=2),
            on_failure=fallback_to_text_extraction
        )
        def extract_with_ocr(pdf_path):
            ...
    
    Args:
        config: RetryConfig instance
        on_failure: Fallback function to call if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
            """
            Execute with retry logic.
            
            Returns:
                (result, metadata) where metadata contains:
                - attempts: Number of attempts made
                - success: Whether succeeded
                - method: "original", "retry", or "fallback"
                - failure_details: Error information if retried
            """
            metadata = {
                "function_name": func.__name__,
                "attempts": 0,
                "success": False,
                "method": "original",
                "failure_details": [],
                "started_at": datetime.utcnow().isoformat()
            }
            
            # Try original function
            for attempt in range(config.max_retries + 1):
                metadata["attempts"] = attempt + 1
                
                try:
                    result = func(*args, **kwargs)
                    metadata["success"] = True
                    if attempt > 0:
                        metadata["method"] = "retry"
                    metadata["ended_at"] = datetime.utcnow().isoformat()
                    return result, metadata
                
                except Exception as e:
                    metadata["failure_details"].append({
                        "attempt": attempt + 1,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Log retry attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries + 1} failed for {func.__name__}: {e}",
                        extra={
                            "attempt": attempt + 1,
                            "function": func.__name__,
                            "error_type": type(e).__name__
                        }
                    )
                    
                    # If not last attempt, wait and retry
                    if attempt < config.max_retries:
                        delay = config.initial_delay * (config.backoff_factor ** attempt)
                        logger.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
            
            # All retries exhausted - try fallback
            if config.fallback_enabled and on_failure:
                try:
                    logger.info(f"All retries exhausted for {func.__name__}. Using fallback...")
                    metadata["method"] = "fallback"
                    result = on_failure(*args, **kwargs)
                    metadata["success"] = True
                    metadata["ended_at"] = datetime.utcnow().isoformat()
                    return result, metadata
                
                except Exception as e:
                    metadata["failure_details"].append({
                        "attempt": "fallback",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    logger.error(
                        f"Fallback also failed for {func.__name__}: {e}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__
                        }
                    )
            
            metadata["success"] = False
            metadata["ended_at"] = datetime.utcnow().isoformat()
            
            # Return None, metadata on complete failure
            return None, metadata
        
        return wrapper
    return decorator


class GracefulDegradationMode:
    """
    Graceful degradation for extraction failures.
    System continues with partial data rather than blocking on errors.
    """
    
    def __init__(self, log_dir: Path = None):
        """Initialize degradation mode logger"""
        self.log_dir = log_dir or Path("logging/degradation_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.degradation_events = []
    
    def handle_extraction_failure(
        self,
        document_name: str,
        extraction_method: str,
        error: Exception,
        partial_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle extraction failure gracefully.
        
        Args:
            document_name: PDF filename
            extraction_method: Method that failed ("text_parser", "ocr_extract", etc.)
            error: Exception that occurred
            partial_data: Any partial data that was extracted before failure
            
        Returns:
            Degraded result with available data + degradation flags
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "document_name": document_name,
            "extraction_method": extraction_method,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "partial_data_available": partial_data is not None
        }
        
        self.degradation_events.append(event)
        
        # Log to file
        import json
        log_file = (
            self.log_dir / 
            f"degradation_{document_name.replace('.pdf', '')}.json"
        )
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(event, f, indent=2, ensure_ascii=False)
        
        logger.warning(
            f"Graceful degradation for {document_name}: using partial data",
            extra={
                "document_name": document_name,
                "extraction_method": extraction_method,
                "error": str(error)
            }
        )
        
        # Return result with degradation flag
        return {
            "document_name": document_name,
            "extraction_confidence": 0.0,  # Zero confidence for degraded data
            "extraction_method": f"{extraction_method}_degraded",
            "partial_data": partial_data or {},
            "degradation_mode": True,
            "degradation_reason": str(error),
            "missing_fields": ["all_fields"],  # Mark all as potentially unreliable
            "line_items": [],
            "validation_errors": [
                f"Extraction failed: {type(error).__name__}",
                "Using degraded/partial data - manual review required"
            ]
        }
    
    def get_degradation_summary(self) -> Dict[str, Any]:
        """Get summary of all degradation events"""
        return {
            "total_degradation_events": len(self.degradation_events),
            "degraded_documents": [e["document_name"] for e in self.degradation_events],
            "methods_failed": list(set(e["extraction_method"] for e in self.degradation_events)),
            "log_directory": str(self.log_dir)
        }


class RecoveryStrategy:
    """Implements different recovery strategies for extraction failures"""
    
    @staticmethod
    def calculate_input_hash(pdf_path: str) -> str:
        """
        Calculate SHA256 hash of PDF file for audit trail.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            SHA256 hex hash
        """
        sha256 = hashlib.sha256()
        with open(pdf_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @staticmethod
    def extract_with_fallback(
        primary_extractor: Callable,
        fallback_extractor: Callable,
        pdf_path: str,
        document_name: str
    ) -> Tuple[Dict[str, Any], str]:
        """
        Try primary extraction, fallback to secondary if primary fails.
        
        Args:
            primary_extractor: Primary extraction function (e.g., OCR)
            fallback_extractor: Fallback extraction function (e.g., text parsing)
            pdf_path: Path to PDF
            document_name: Document filename
            
        Returns:
            (extracted_data, method_used) - tuple with data and which method succeeded
        """
        try:
            logger.info(f"Attempting primary extraction for {document_name}")
            result = primary_extractor(pdf_path)
            return result, "primary"
        
        except Exception as e:
            logger.warning(
                f"Primary extraction failed for {document_name}: {e}. Trying fallback...",
                extra={"document_name": document_name, "error": str(e)}
            )
            
            try:
                result = fallback_extractor(pdf_path)
                return result, "fallback"
            
            except Exception as fallback_error:
                logger.error(
                    f"Fallback extraction also failed for {document_name}: {fallback_error}",
                    extra={"document_name": document_name, "error": str(fallback_error)}
                )
                raise
