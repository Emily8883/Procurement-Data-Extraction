"""
Pydantic models for strict schema validation of procurement documents.
Ensures all extracted data conforms to expected format and types.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


class LineItem(BaseModel):
    """Individual line item in document (invoice or specification)"""
    
    description: str = Field(..., min_length=1, description="Item description")
    quantity: Optional[float] = Field(None, ge=0, description="Quantity ordered/specified")
    unit_price: Optional[float] = Field(None, ge=0, description="Price per unit")
    total_price: Optional[float] = Field(None, ge=0, description="Total for line item")
    unit: Optional[str] = Field(None, description="Unit of measurement (pcs, kg, hrs, etc.)")
    raw_value: Optional[str] = Field(None, description="Original text for this line item")
    
    class Config:
        allow_mutation = True
        arbitrary_types_allowed = True


class ProcurementDocument(BaseModel):
    """Validated procurement document (invoice or purchase order)"""
    
    document_name: str = Field(..., min_length=1, description="PDF filename")
    document_type: str = Field("invoice_or_po", pattern="^(invoice_or_po)$")
    
    supplier: Optional[str] = Field(None, description="Vendor/supplier name")
    invoice_or_po_number: Optional[str] = Field(None, description="Invoice or PO number")
    issue_date: Optional[str] = Field(None, description="Date issued (ISO format or raw)")
    currency: Optional[str] = Field(None, max_length=3, description="Currency code (USD, PEN, etc.)")
    
    subtotal: Optional[float] = Field(None, ge=0, description="Subtotal before tax")
    tax: Optional[float] = Field(None, ge=0, description="Tax amount")
    total_amount: Optional[float] = Field(None, ge=0, description="Grand total")
    
    line_items: List[LineItem] = Field(default_factory=list, description="Extracted line items")
    line_item_count: int = Field(default=0, ge=0, description="Number of line items")
    
    extraction_confidence: float = Field(..., ge=0, le=100, description="Confidence 0-100")
    extraction_method: Optional[str] = Field(None, pattern="^(text_parser|ocr_extract)$")
    
    missing_fields: List[str] = Field(default_factory=list, description="Critical fields missing")
    
    processing_status: str = Field("invalid", pattern="^(valid|invalid|requires_review)$")
    
    pipeline: str = Field("procurement", pattern="^procurement$")
    
    validation_errors: List[str] = Field(default_factory=list, description="Validation failures")
    validation_warnings: List[str] = Field(default_factory=list, description="Non-blocking issues")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_extraction_data: Optional[Dict[str, Any]] = Field(None, description="Original extracted data")
    
    @validator('extraction_confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 100:
            raise ValueError(f"Confidence must be 0-100, got {v}")
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        if v and not re.match(r'^[A-Z]{3}$', v):
            raise ValueError(f"Currency must be 3-letter code, got {v}")
        return v
    
    @validator('line_item_count')
    def sync_line_item_count(cls, v, values):
        if 'line_items' in values:
            return len(values['line_items'])
        return v
    
    class Config:
        allow_mutation = True
        arbitrary_types_allowed = True


class SpecificationDocument(BaseModel):
    """Validated specification document (datasheet, technical spec, requirements)"""
    
    document_name: str = Field(..., min_length=1, description="PDF filename")
    document_type: str = Field("specification", pattern="^(specification)$")
    
    supplier: Optional[str] = Field(None, description="Vendor/manufacturer (optional)")
    invoice_or_po_number: Optional[str] = Field(None, description="Reference number if any")
    issue_date: Optional[str] = Field(None, description="Date issued (optional)")
    currency: Optional[str] = Field(None, max_length=3, description="Currency (if pricing present)")
    
    line_items: List[LineItem] = Field(default_factory=list, description="Technical specs/requirements")
    line_item_count: int = Field(default=0, ge=0, description="Number of spec items")
    
    technical_specifications: Optional[Dict[str, Any]] = Field(
        None, 
        description="Detected technical specs (standards, requirements, etc.)"
    )
    
    extraction_confidence: float = Field(..., ge=0, le=100, description="Confidence 0-100")
    extraction_method: Optional[str] = Field(None, pattern="^(text_parser|ocr_extract)$")
    
    missing_fields: List[str] = Field(default_factory=list, description="Important missing fields")
    
    processing_status: str = Field("invalid", pattern="^(valid|invalid|requires_review)$")
    
    pipeline: str = Field("specification", pattern="^specification$")
    
    validation_errors: List[str] = Field(default_factory=list, description="Validation failures")
    validation_warnings: List[str] = Field(default_factory=list, description="Non-blocking issues")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_extraction_data: Optional[Dict[str, Any]] = Field(None, description="Original extracted data")
    
    @validator('extraction_confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 100:
            raise ValueError(f"Confidence must be 0-100, got {v}")
        return v
    
    @validator('line_item_count')
    def sync_line_item_count(cls, v, values):
        if 'line_items' in values:
            return len(values['line_items'])
        return v
    
    class Config:
        allow_mutation = True
        arbitrary_types_allowed = True


class SchemaValidationError(BaseModel):
    """Schema validation failure record"""
    
    document_name: str
    document_type: str
    error_type: str = "schema_validation_error"
    validation_errors: List[str] = Field(default_factory=list, description="Pydantic validation errors")
    attempted_data: Optional[Dict[str, Any]] = Field(None, description="Data that failed validation")
    failure_reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True
