"""
Schema validator module - applies Pydantic models to extracted data.
Ensures strict validation with detailed error logging.
"""

import logging
from typing import Tuple, Dict, Any, Union, Optional
from pydantic import ValidationError
import json
from datetime import datetime
from pathlib import Path

from schemas.procurement_schema import (
    ProcurementDocument, 
    SpecificationDocument,
    SchemaValidationError
)


logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates extracted data against Pydantic schemas"""
    
    def __init__(self, validation_log_dir: Path = None):
        """
        Initialize validator with optional logging directory.
        
        Args:
            validation_log_dir: Directory to save validation errors
        """
        self.validation_log_dir = validation_log_dir or Path("logging/validation_errors")
        self.validation_log_dir.mkdir(parents=True, exist_ok=True)
        
        self.validation_failures = []
    
    def validate_procurement_document(
        self, 
        data: Dict[str, Any], 
        document_name: str
    ) -> Tuple[Optional[ProcurementDocument], Optional[Dict[str, str]]]:
        """
        Validate extracted data against procurement schema.
        
        Args:
            data: Extracted procurement data dictionary
            document_name: Source document filename
            
        Returns:
            (valid_document, error_dict) - One will be None
            - If valid: (ProcurementDocument, None)
            - If invalid: (None, {field: error_message, ...})
        """
        try:
            # Try to validate
            document = ProcurementDocument(
                document_name=document_name,
                **data
            )
            return document, None
            
        except ValidationError as e:
            # Extract field-level errors
            error_dict = {}
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_dict[field] = message
            
            # Log validation failure
            self._log_validation_failure(
                document_name=document_name,
                document_type="procurement",
                validation_errors=list(error_dict.values()),
                attempted_data=data,
                failure_reason=f"{len(error_dict)} field validation error(s)"
            )
            
            return None, error_dict
    
    def validate_specification_document(
        self, 
        data: Dict[str, Any], 
        document_name: str
    ) -> Tuple[Optional[SpecificationDocument], Optional[Dict[str, str]]]:
        """
        Validate extracted data against specification schema.
        
        Args:
            data: Extracted specification data dictionary
            document_name: Source document filename
            
        Returns:
            (valid_document, error_dict) - One will be None
            - If valid: (SpecificationDocument, None)
            - If invalid: (None, {field: error_message, ...})
        """
        try:
            document = SpecificationDocument(
                document_name=document_name,
                **data
            )
            return document, None
            
        except ValidationError as e:
            error_dict = {}
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_dict[field] = message
            
            self._log_validation_failure(
                document_name=document_name,
                document_type="specification",
                validation_errors=list(error_dict.values()),
                attempted_data=data,
                failure_reason=f"{len(error_dict)} field validation error(s)"
            )
            
            return None, error_dict
        
        return None, {}
    
    def _log_validation_failure(
        self,
        document_name: str,
        document_type: str,
        validation_errors: list,
        attempted_data: Dict[str, Any],
        failure_reason: str
    ) -> None:
        """
        Log schema validation failure to file.
        
        Args:
            document_name: Document filename
            document_type: "procurement" or "specification"
            validation_errors: List of validation error messages
            attempted_data: The data that failed
            failure_reason: Summary of failure
        """
        error_record = SchemaValidationError(
            document_name=document_name,
            document_type=document_type,
            validation_errors=validation_errors,
            attempted_data=attempted_data,
            failure_reason=failure_reason
        )
        
        # Store in memory
        self.validation_failures.append(error_record)
        
        # Log to file
        log_file = (
            self.validation_log_dir / 
            f"validation_failure_{document_name.replace('.pdf', '')}.json"
        )
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(
                json.loads(error_record.json()),
                indent=2,
                ensure_ascii=False
            ))
        
        logger.error(
            f"Schema validation failed: {document_name} - {failure_reason}",
            extra={
                "document_name": document_name,
                "document_type": document_type,
                "error_count": len(validation_errors),
                "log_file": str(log_file)
            }
        )
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation failures"""
        return {
            "total_failures": len(self.validation_failures),
            "failures_by_type": {
                doc_type: len([f for f in self.validation_failures if f.document_type == doc_type])
                for doc_type in ["procurement", "specification"]
            },
            "failure_documents": [f.document_name for f in self.validation_failures],
            "validation_error_log_dir": str(self.validation_log_dir)
        }
