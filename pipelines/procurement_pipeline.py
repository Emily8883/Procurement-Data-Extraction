#!/usr/bin/env python3
"""
Procurement Pipeline Implementation

Handles extraction and validation of invoices and purchase orders.
STRICT validation mode - all critical fields required.
"""

import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from .base_pipeline import BasePipeline


class ProcurementPipeline(BasePipeline):
    """Pipeline for procurement documents (invoices, POs)"""
    
    def _get_pipeline_name(self) -> str:
        return "Procurement Pipeline"
    
    def _get_pipeline_type(self) -> str:
        return "procurement"
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract procurement data from document"""
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
                'extraction_method': result.get('extraction_method', 'unknown')
            }
            
        except Exception as e:
            self.log_error(f"Extraction failed: {str(e)}")
            return {
                'document_name': Path(pdf_path).name,
                'confidence_score': 0,
                'missing_fields': ['all fields - extraction failed'],
                'extraction_error': str(e)
            }
    
    def validate(self, extracted_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate procurement data using STRICT rules
        
        Returns:
            (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Rule 1: Field Completeness (STRICT)
        critical_fields = self.get_critical_fields()
        for field in critical_fields:
            value = extracted_data.get(field, '')
            if not value or value == '':
                errors.append(f"CRITICAL: Missing field '{field}'")
        
        # Rule 2: Math Consistency (if enabled and data present)
        if self.is_math_validation_enabled():
            math_errors = self._validate_math(extracted_data)
            if math_errors:
                errors.extend(math_errors)
        
        # Rule 3: Line Items (required)
        line_items = extracted_data.get('line_items', [])
        if not line_items:
            errors.append("CRITICAL: No line items found")
        else:
            item_warnings = self._validate_line_items(line_items)
            if item_warnings:
                warnings.extend(item_warnings)
        
        # Rule 4: Confidence Score
        confidence = extracted_data.get('confidence_score', 0)
        if confidence < 30:
            warnings.append(
                f"Low extraction confidence: {confidence}% "
                f"(minimum recommended: 30%)"
            )
        
        # Determine validity
        is_valid = len(errors) == 0
        
        return is_valid, errors, warnings
    
    def _validate_math(self, data: Dict[str, Any]) -> List[str]:
        """Validate mathematical consistency"""
        errors = []
        
        subtotal = self._parse_numeric(data.get('subtotal', ''))
        tax = self._parse_numeric(data.get('tax', ''))
        total_amount = self._parse_numeric(data.get('total_amount', ''))
        
        if subtotal is not None and tax is not None and total_amount is not None:
            calculated_total = subtotal + tax
            tolerance = self.get_math_tolerance()
            
            if calculated_total > 0:
                percentage_diff = abs(calculated_total - total_amount) / calculated_total
                if percentage_diff > tolerance:
                    errors.append(
                        f"MATH ERROR: subtotal ({subtotal}) + tax ({tax}) = "
                        f"{calculated_total}, but total_amount = {total_amount} "
                        f"({percentage_diff*100:.1f}% difference, tolerance: {tolerance*100:.1f}%)"
                    )
        
        return errors
    
    def _validate_line_items(self, line_items: List[Dict]) -> List[str]:
        """Validate line items"""
        warnings = []
        tolerance = self.get_math_tolerance()
        suspicious_threshold = 10000
        
        for idx, item in enumerate(line_items, 1):
            quantity = self._parse_numeric(item.get('quantity', ''))
            unit_price = self._parse_numeric(item.get('unit_price', ''))
            total_price = self._parse_numeric(item.get('total_price', ''))
            
            # Check for suspicious quantities
            if quantity and quantity > suspicious_threshold:
                warnings.append(
                    f"Line {idx}: Suspicious quantity ({quantity}) - "
                    f"may be metadata (regulation/article number)"
                )
            
            # Check price calculation
            if quantity is not None and unit_price is not None and total_price is not None:
                calculated = quantity * unit_price
                if calculated > 0:
                    pct_diff = abs(calculated - total_price) / calculated
                    if pct_diff > tolerance:
                        warnings.append(
                            f"Line {idx}: Price mismatch - "
                            f"qty({quantity}) × unit_price({unit_price}) = "
                            f"{calculated}, but total_price = {total_price}"
                        )
        
        return warnings
    
    def finalize(self, extracted_data: Dict[str, Any], 
                validation_result: bool) -> Dict[str, Any]:
        """Finalize output for procurement pipeline"""
        
        final_output = {
            'document_name': extracted_data.get('document_name', ''),
            'document_type': 'invoice_or_po',
            'pipeline': self.pipeline_type,
            'processing_status': 'valid' if validation_result else 'invalid',
            'extraction_confidence': extracted_data.get('confidence_score', 0),
            
            # Core procurement fields
            'supplier': extracted_data.get('supplier', ''),
            'invoice_or_po_number': extracted_data.get('invoice_or_po_number', ''),
            'issue_date': extracted_data.get('issue_date', ''),
            'currency': extracted_data.get('currency', ''),
            
            # Financial fields
            'subtotal': extracted_data.get('subtotal', ''),
            'tax': extracted_data.get('tax', ''),
            'total_amount': extracted_data.get('total_amount', ''),
            
            # Line items
            'line_items': extracted_data.get('line_items', []),
            'line_item_count': len(extracted_data.get('line_items', [])),
            
            # Metadata
            'missing_fields': extracted_data.get('missing_fields', []),
            'extraction_method': extracted_data.get('extraction_method', ''),
        }
        
        return final_output
