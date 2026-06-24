#!/usr/bin/env python3
"""
Specification Pipeline Implementation

Handles extraction and validation of technical specifications, datasheets, 
product requirements. LENIENT validation mode - critical fields only.
"""

import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from .base_pipeline import BasePipeline


class SpecificationPipeline(BasePipeline):
    """Pipeline for specification documents (datasheets, technical sheets, requirements)"""
    
    def _get_pipeline_name(self) -> str:
        return "Specification Pipeline"
    
    def _get_pipeline_type(self) -> str:
        return "specification"
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract specification data from document"""
        # Import existing extraction logic
        try:
            from extract_procurement import ProcurementExtractor
            
            extractor = ProcurementExtractor(
                str(Path(pdf_path).parent.parent / 'output' / 'document_classifications.json')
            )
            
            # Extract single document
            result = extractor.extract_document(pdf_path)
            
            return {
                'document_name': Path(pdf_path).name,
                'supplier': result.get('supplier', ''),
                'invoice_or_po_number': result.get('invoice_or_po_number', ''),
                'issue_date': result.get('issue_date', ''),
                'currency': result.get('currency', ''),
                'line_items': result.get('line_items', []),
                'subtotal': result.get('subtotal', ''),
                'tax': result.get('tax', ''),
                'total_amount': result.get('total_amount', ''),
                'confidence_score': result.get('confidence_score', 0),
                'missing_fields': result.get('missing_fields', []),
                'extraction_method': result.get('extraction_method', ''),
                'technical_specifications': self._extract_technical_specs(result)
            }
            
        except Exception as e:
            self.log_error(f"Extraction failed: {str(e)}")
            return {
                'document_name': Path(pdf_path).name,
                'confidence_score': 0,
                'missing_fields': ['line_items - extraction failed'],
                'extraction_error': str(e),
                'technical_specifications': {}
            }
    
    def _extract_technical_specs(self, extraction_result: Dict) -> Dict[str, Any]:
        """Extract technical specification details from extraction result"""
        specs = {}
        
        # Extract from line items if they contain technical information
        line_items = extraction_result.get('line_items', [])
        
        for item in line_items:
            description = item.get('description', '').lower()
            
            # Detect technical keywords
            if any(kw in description for kw in 
                   ['standard', 'norm', 'requirement', 'specification', 'specification',
                    'complies', 'comply', 'feature', 'technical', 'temperature', 
                    'voltage', 'current', 'dimensions', 'weight', 'material']):
                specs['has_technical_requirements'] = True
        
        return specs if specs else {'has_technical_requirements': False}
    
    def validate(self, extracted_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate specification data using LENIENT rules
        
        Returns:
            (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Rule 1: Field Completeness (LENIENT - only critical fields)
        critical_fields = self.get_critical_fields()
        for field in critical_fields:
            if field == 'document_name':
                value = extracted_data.get(field, '')
                if not value:
                    errors.append(f"CRITICAL: Missing field '{field}'")
            elif field == 'line_items':
                value = extracted_data.get(field, [])
                if not value:
                    errors.append(f"CRITICAL: No technical specifications or line items found")
        
        # Rule 2: Optional fields - only warning if missing
        optional_fields = self.get_optional_fields()
        missing_optional = []
        for field in optional_fields:
            value = extracted_data.get(field, '')
            if not value:
                missing_optional.append(field)
        
        if missing_optional:
            warnings.append(
                f"Optional fields missing: {', '.join(missing_optional)} "
                f"(expected for specifications)"
            )
        
        # Rule 3: Line Items (required but lenient)
        line_items = extracted_data.get('line_items', [])
        if line_items:
            item_warnings = self._validate_line_items_lenient(line_items)
            if item_warnings:
                warnings.extend(item_warnings)
        
        # Rule 4: Confidence Score (lenient)
        confidence = extracted_data.get('confidence_score', 0)
        if confidence < 20:
            warnings.append(
                f"Very low extraction confidence: {confidence}% "
                f"(may indicate OCR or text quality issues)"
            )
        
        # Rule 5: Technical Specifications
        tech_specs = extracted_data.get('technical_specifications', {})
        if not tech_specs.get('has_technical_requirements'):
            warnings.append(
                "No explicit technical specifications detected - "
                "verify document contains specification content"
            )
        
        # Determine validity - LENIENT mode allows warnings
        is_valid = len(errors) == 0
        
        return is_valid, errors, warnings
    
    def _validate_line_items_lenient(self, line_items: List[Dict]) -> List[str]:
        """Validate line items with lenient rules (specs don't have pricing)"""
        warnings = []
        suspicious_threshold = 100000  # Higher threshold for specs
        
        for idx, item in enumerate(line_items, 1):
            quantity = self._parse_numeric(item.get('quantity', ''))
            
            # Only flag extremely high quantities
            if quantity and quantity > suspicious_threshold:
                warnings.append(
                    f"Line {idx}: Extremely high quantity ({quantity}) - "
                    f"likely regulation/article reference"
                )
            
            # Warn about missing descriptions
            description = item.get('description', '').strip()
            if not description:
                warnings.append(f"Line {idx}: Empty description")
        
        return warnings
    
    def finalize(self, extracted_data: Dict[str, Any], 
                validation_result: bool) -> Dict[str, Any]:
        """Finalize output for specification pipeline"""
        
        final_output = {
            'document_name': extracted_data.get('document_name', ''),
            'document_type': 'specification',
            'pipeline': self.pipeline_type,
            'processing_status': 'valid' if validation_result else 'invalid',
            'extraction_confidence': extracted_data.get('confidence_score', 0),
            
            # Specification-specific fields
            'supplier': extracted_data.get('supplier', ''),
            'invoice_or_po_number': extracted_data.get('invoice_or_po_number', ''),
            'issue_date': extracted_data.get('issue_date', ''),
            'currency': extracted_data.get('currency', ''),
            
            # Technical content
            'line_items': extracted_data.get('line_items', []),
            'line_item_count': len(extracted_data.get('line_items', [])),
            'technical_specifications': extracted_data.get('technical_specifications', {}),
            
            # Metadata
            'missing_fields': extracted_data.get('missing_fields', []),
            'extraction_method': extracted_data.get('extraction_method', ''),
            
            # Note: Pricing fields (subtotal, tax, total_amount) intentionally omitted
            # as specifications do not contain pricing information
        }
        
        return final_output
