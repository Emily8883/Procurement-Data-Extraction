#!/usr/bin/env python3
"""
Base Pipeline Class for Deterministic Extraction

Abstract base class defining the pipeline interface and shared functionality.
"""

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class BasePipeline(ABC):
    """Abstract base class for extraction pipelines"""
    
    def __init__(self, rules_config: Dict[str, Any], pipeline_config: Dict[str, Any], 
                 logger=None):
        """Initialize base pipeline"""
        self.rules_config = rules_config
        self.pipeline_config = pipeline_config
        self.logger = logger
        self.pipeline_name = self._get_pipeline_name()
        self.pipeline_type = self._get_pipeline_type()
        self.validation_rules = self._load_validation_rules()
    
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
        Complete document processing flow
        
        Returns:
            Dictionary with processing results including:
            - document_name
            - pipeline_used
            - extraction_confidence
            - validation_result
            - extracted_data
            - processing_time_seconds
            - status (SUCCESS/WARNING/FAILED)
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        try:
            # Stage 1: Extract
            extracted_data = self.extract(str(pdf_path))
            extraction_confidence = extracted_data.get('confidence_score', 0)
            
            # Stage 2: Validate
            is_valid, errors, warnings = self.validate(extracted_data)
            validation_result = "PASS" if is_valid else "FAIL" if errors else "WARNING"
            
            # Stage 3: Finalize
            final_data = self.finalize(extracted_data, is_valid)
            
            # Determine status
            if errors:
                status = "FAILED"
            elif warnings:
                status = "WARNING"
            else:
                status = "SUCCESS"
            
            processing_time = time.time() - start_time
            
            return {
                "document_name": pdf_path.name,
                "pipeline_used": self.pipeline_name,
                "pipeline_type": self.pipeline_type,
                "extraction_confidence": extraction_confidence,
                "validation_result": validation_result,
                "validation_errors": errors,
                "validation_warnings": warnings,
                "extracted_data": final_data,
                "processing_time_seconds": processing_time,
                "status": status,
                "failure_reason": errors[0] if errors else None,
                "failure_details": json.dumps(errors) if errors else None
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "document_name": pdf_path.name,
                "pipeline_used": self.pipeline_name,
                "pipeline_type": self.pipeline_type,
                "extraction_confidence": 0,
                "validation_result": "FAIL",
                "validation_errors": [str(e)],
                "validation_warnings": [],
                "extracted_data": {},
                "processing_time_seconds": processing_time,
                "status": "FAILED",
                "failure_reason": f"Exception: {str(e)}",
                "failure_details": str(e)
            }
    
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
