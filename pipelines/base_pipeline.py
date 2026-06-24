#!/usr/bin/env python3
"""
Base Pipeline Class for Deterministic Extraction

Abstract base class defining the pipeline interface and shared functionality.
Includes schema validation, failure recovery, and audit-grade logging.
"""

import json
import time
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Optional: Only import if Pydantic is available
try:
    from schemas.schema_validator import SchemaValidator
    SCHEMA_VALIDATION_ENABLED = True
except ImportError:
    SCHEMA_VALIDATION_ENABLED = False


class BasePipeline(ABC):
    """Abstract base class for extraction pipelines"""
    
    PIPELINE_VERSION = "2.0"  # Version for audit logging
    
    def __init__(self, rules_config: Dict[str, Any], pipeline_config: Dict[str, Any], 
                 logger=None, enable_schema_validation: bool = True):
        """Initialize base pipeline with validation and recovery support"""
        self.rules_config = rules_config
        self.pipeline_config = pipeline_config
        self.logger = logger
        self.pipeline_name = self._get_pipeline_name()
        self.pipeline_type = self._get_pipeline_type()
        self.validation_rules = self._load_validation_rules()
        
        # Schema validation
        self.enable_schema_validation = enable_schema_validation and SCHEMA_VALIDATION_ENABLED
        if self.enable_schema_validation:
            self.schema_validator = SchemaValidator()
        
        # Confidence threshold for REQUIRES_REVIEW flag
        self.confidence_threshold = rules_config.get('global_settings', {}).get(
            'confidence_threshold_requires_review', 
            70
        )
    
    @abstractmethod
    def _get_pipeline_name(self) -> str:
        """Return pipeline name"""
        pass
    
    @abstractmethod
    def _get_pipeline_type(self) -> str:
        """Return pipeline type (procurement/specification)"""
        pass
    
    @abstractmethod
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract data from document"""
        pass
    
    @abstractmethod
    def validate(self, extracted_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """Validate extracted data against rules"""
        pass
    
    @abstractmethod
    def finalize(self, extracted_data: Dict[str, Any], 
                validation_result: bool) -> Dict[str, Any]:
        """Finalize output for this pipeline"""
        pass
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for this pipeline type"""
        if self.pipeline_type == "procurement":
            return self.rules_config.get("procurement_pipeline", {})
        elif self.pipeline_type == "specification":
            return self.rules_config.get("specification_pipeline", {})
        else:
            raise ValueError(f"Unknown pipeline type: {self.pipeline_type}")
    
    def process_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        Complete document processing flow with schema validation and audit logging.
        
        Returns:
            Dictionary with complete processing details:
            - document_name, pipeline_used, pipeline_version
            - input_hash (SHA256 for audit)
            - extraction_confidence
            - validation_result
            - schema_validation_status
            - requires_review (if confidence < threshold)
            - extracted_data
            - processing_time_seconds
            - status (SUCCESS/WARNING/FAILED/REQUIRES_REVIEW)
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        # Calculate input hash for audit trail
        input_hash = self._calculate_file_hash(str(pdf_path))
        
        try:
            # Stage 1: Extract
            extracted_data = self.extract(str(pdf_path))
            extraction_confidence = extracted_data.get('confidence_score', 0)
            extraction_method = extracted_data.get('extraction_method', 'unknown')
            
            # Stage 2: Validate
            is_valid, errors, warnings = self.validate(extracted_data)
            validation_result = "PASS" if is_valid else "FAIL" if errors else "WARNING"
            
            # Stage 2.5: Schema Validation (if enabled)
            schema_valid = True
            schema_errors = []
            if self.enable_schema_validation:
                extracted_data['document_name'] = pdf_path.name
                schema_valid, schema_errors = self._apply_schema_validation(
                    extracted_data, 
                    pdf_path.name
                )
                if not schema_valid:
                    errors.extend(schema_errors)
                    validation_result = "FAIL"
            
            # Stage 3: Check confidence threshold
            requires_review = extraction_confidence < self.confidence_threshold
            if requires_review:
                warnings.append(
                    f"Low confidence ({extraction_confidence:.0f}%) - marked for review"
                )
            
            # Stage 4: Finalize
            final_data = self.finalize(extracted_data, is_valid)
            
            # Determine status
            if errors:
                status = "FAILED"
            elif requires_review:
                status = "REQUIRES_REVIEW"
            elif warnings:
                status = "WARNING"
            else:
                status = "SUCCESS"
            
            processing_time = time.time() - start_time
            
            result = {
                "document_name": pdf_path.name,
                "pipeline_used": self.pipeline_name,
                "pipeline_type": self.pipeline_type,
                "pipeline_version": self.PIPELINE_VERSION,
                "input_hash": input_hash,
                "extraction_confidence": extraction_confidence,
                "extraction_method": extraction_method,
                "validation_result": validation_result,
                "schema_validation_enabled": self.enable_schema_validation,
                "schema_validation_passed": schema_valid if self.enable_schema_validation else None,
                "validation_errors": errors,
                "validation_warnings": warnings,
                "requires_review": requires_review,
                "confidence_threshold": self.confidence_threshold,
                "extracted_data": final_data,
                "processing_time_seconds": processing_time,
                "status": status,
                "failure_reason": errors[0] if errors else None,
                "failure_details": json.dumps(errors) if errors else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            import traceback
            return {
                "document_name": pdf_path.name,
                "pipeline_used": self.pipeline_name,
                "pipeline_type": self.pipeline_type,
                "pipeline_version": self.PIPELINE_VERSION,
                "input_hash": input_hash,
                "extraction_confidence": 0,
                "extraction_method": "failed",
                "validation_result": "FAIL",
                "schema_validation_enabled": self.enable_schema_validation,
                "schema_validation_passed": False,
                "validation_errors": [str(e)],
                "validation_warnings": [],
                "requires_review": True,
                "confidence_threshold": self.confidence_threshold,
                "extracted_data": {},
                "processing_time_seconds": processing_time,
                "status": "FAILED",
                "failure_reason": f"Exception: {type(e).__name__}",
                "failure_details": traceback.format_exc(),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of input file for audit trail"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _apply_schema_validation(
        self,
        extracted_data: Dict[str, Any],
        document_name: str
    ) -> Tuple[bool, List[str]]:
        """
        Apply Pydantic schema validation to extracted data.
        
        Returns:
            (is_valid, error_messages)
        """
        if not self.enable_schema_validation or not hasattr(self, 'schema_validator'):
            return True, []
        
        if self.pipeline_type == "procurement":
            doc, errors = self.schema_validator.validate_procurement_document(
                extracted_data,
                document_name
            )
            if errors:
                error_messages = [
                    f"Schema validation - {field}: {msg}"
                    for field, msg in errors.items()
                ]
                return False, error_messages
            return True, []
        
        elif self.pipeline_type == "specification":
            doc, errors = self.schema_validator.validate_specification_document(
                extracted_data,
                document_name
            )
            if errors:
                error_messages = [
                    f"Schema validation - {field}: {msg}"
                    for field, msg in errors.items()
                ]
                return False, error_messages
            return True, []
        
        return True, []
    
    def get_critical_fields(self) -> List[str]:
        """Get critical fields for this pipeline"""
        field_config = self.validation_rules.get('field_completeness', {})
        return field_config.get('critical_fields', [])
    
    def get_optional_fields(self) -> List[str]:
        """Get optional fields for this pipeline"""
        field_config = self.validation_rules.get('field_completeness', {})
        return field_config.get('optional_fields', [])
    
    def is_math_validation_enabled(self) -> bool:
        """Check if math validation is enabled for this pipeline"""
        return self.validation_rules.get('math_validation', {}).get('enabled', False)
    
    def get_math_tolerance(self) -> float:
        """Get math validation tolerance"""
        checks = self.validation_rules.get('math_validation', {}).get('checks', [])
        if checks:
            return checks[0].get('tolerance', 0.05)
        return 0.05
    
    def is_strict_mode(self) -> bool:
        """Check if strict validation mode"""
        pass_criteria = self.validation_rules.get('pass_criteria', {})
        return not pass_criteria.get('allow_warnings', False)
    
    def get_enforcement_mode(self) -> str:
        """Get enforcement mode (STRICT or LENIENT)"""
        return self.validation_rules.get('field_completeness', {}).get('enforcement', 'STRICT')
    
    def _parse_numeric(self, value: Any) -> Optional[float]:
        """Safely parse numeric value"""
        if not value or value == "":
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            import re
            value = value.strip()
            value = re.sub(r'[^\d\.,\-]', '', value)
            
            if ',' in value and '.' in value:
                if value.rfind(',') > value.rfind('.'):
                    value = value.replace('.', '').replace(',', '.')
                else:
                    value = value.replace(',', '')
            else:
                value = value.replace(',', '.')
            
            try:
                return float(value)
            except ValueError:
                return None
        
        return None
    
    def log_info(self, message: str):
        """Log info message"""
        if self.logger:
            self.logger.logger.info(message)
    
    def log_warning(self, message: str):
        """Log warning message"""
        if self.logger:
            self.logger.logger.warning(message)
    
    def log_error(self, message: str):
        """Log error message"""
        if self.logger:
            self.logger.logger.error(message)
