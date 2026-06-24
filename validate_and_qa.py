#!/usr/bin/env python3
"""
Procurement Data Validation & Quality Control Layer

Validates extracted procurement data with strict financial consistency checks.
Does NOT auto-correct - only detects and flags issues.

Rules:
  - Field Completeness: Check for critical missing fields
  - Math Consistency: subtotal + tax ≈ total_amount
  - Line Item Validation: quantity × unit_price ≈ total_price
  - OCR Quality: Detect issues in scanned documents
  - Output: Enhanced JSON with validation results
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    math_checks: Dict[str, bool]
    field_checks: Dict[str, bool]
    line_item_checks: List[Dict[str, Any]]
    ocr_checks: Dict[str, Any] = None


class ProcurementValidator:
    """Validates procurement extraction data with strict financial rules"""
    
    # Critical fields that must be present for text-based documents
    CRITICAL_FIELDS = [
        'supplier',
        'invoice_or_po_number',
        'issue_date',
        'total_amount'
    ]
    
    # Tolerance for numeric comparisons (5% = 0.05)
    TOLERANCE = 0.05
    
    def __init__(self, extracted_json_path: str):
        """Initialize validator with extracted data"""
        self.extracted_json_path = Path(extracted_json_path)
        self.records = self._load_data()
        self.validated_records = []
        
    def _load_data(self) -> List[Dict]:
        """Load extracted procurement data"""
        if not self.extracted_json_path.exists():
            raise FileNotFoundError(
                f"Extracted data not found: {self.extracted_json_path}"
            )
        
        with open(self.extracted_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_all(self) -> List[Dict]:
        """Validate all records and return enhanced JSON"""
        print(f"\n{'='*80}")
        print("VALIDATION & QUALITY CONTROL - PROCUREMENT EXTRACTION")
        print(f"{'='*80}\n")
        
        for idx, record in enumerate(self.records, 1):
            print(f"Document {idx}/{len(self.records)}: {record['document_name']}")
            print("-" * 80)
            
            validation = self.validate_record(record)
            enhanced_record = self._enhance_record(record, validation)
            self.validated_records.append(enhanced_record)
            
            self._print_validation(validation)
        
        return self.validated_records
    
    def validate_record(self, record: Dict) -> ValidationResult:
        """Validate single record"""
        errors = []
        warnings = []
        math_checks = {}
        field_checks = {}
        line_item_checks = []
        ocr_checks = None
        
        # === FIELD COMPLETENESS CHECK ===
        field_checks = self._check_field_completeness(record, errors, warnings)
        
        # === MATH CONSISTENCY CHECK ===
        if record['document_type'] == 'text':
            math_checks = self._check_math_consistency(record, errors, warnings)
        else:
            # Scanned documents - expect missing fields
            if record['confidence_score'] == 0 or not record['line_items']:
                warnings.append(
                    "Scanned document: No data extracted. OCR not available."
                )
        
        # === LINE ITEM VALIDATION ===
        if record['line_items']:
            line_item_checks = self._validate_line_items(
                record['line_items'], errors, warnings
            )
        
        # === OCR QUALITY CHECK ===
        if record['document_type'] == 'scanned':
            ocr_checks = self._check_ocr_quality(record, warnings)
        
        # === DETERMINE VALIDITY ===
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            math_checks=math_checks,
            field_checks=field_checks,
            line_item_checks=line_item_checks,
            ocr_checks=ocr_checks
        )
    
    def _check_field_completeness(
        self, 
        record: Dict, 
        errors: List[str], 
        warnings: List[str]
    ) -> Dict[str, bool]:
        """Check for missing critical fields"""
        field_checks = {}
        
        # Only check critical fields for text-based documents
        if record['document_type'] == 'text':
            for field in self.CRITICAL_FIELDS:
                is_present = bool(record.get(field)) and record[field] != ""
                field_checks[field] = is_present
                
                if not is_present:
                    errors.append(f"CRITICAL: Missing field '{field}'")
        else:
            # Scanned documents
            for field in self.CRITICAL_FIELDS:
                is_present = bool(record.get(field)) and record[field] != ""
                field_checks[field] = is_present
                
                if not is_present:
                    warnings.append(f"Scanned: Missing field '{field}' (expected)")
        
        # Check line items
        has_line_items = bool(record.get('line_items')) and len(record['line_items']) > 0
        field_checks['line_items'] = has_line_items
        
        if record['document_type'] == 'text' and not has_line_items:
            errors.append("CRITICAL: No line items extracted from text document")
        
        return field_checks
    
    def _check_math_consistency(
        self, 
        record: Dict, 
        errors: List[str], 
        warnings: List[str]
    ) -> Dict[str, bool]:
        """Verify: subtotal + tax ≈ total_amount"""
        math_checks = {
            'subtotal_match': False,
            'line_item_accuracy': False
        }
        
        # Extract numeric values
        subtotal = self._parse_numeric(record.get('subtotal', ''))
        tax = self._parse_numeric(record.get('tax', ''))
        total_amount = self._parse_numeric(record.get('total_amount', ''))
        
        # Check subtotal + tax = total_amount
        if subtotal is not None and tax is not None and total_amount is not None:
            calculated_total = subtotal + tax
            
            # Check if they match within tolerance
            if calculated_total == 0 and total_amount == 0:
                math_checks['subtotal_match'] = True
            elif calculated_total > 0:
                percentage_diff = abs(calculated_total - total_amount) / calculated_total
                
                if percentage_diff <= self.TOLERANCE:
                    math_checks['subtotal_match'] = True
                else:
                    errors.append(
                        f"MATH ERROR: subtotal ({subtotal}) + tax ({tax}) = "
                        f"{calculated_total}, but total_amount = {total_amount} "
                        f"({percentage_diff*100:.1f}% difference)"
                    )
            else:
                if calculated_total == total_amount:
                    math_checks['subtotal_match'] = True
                else:
                    warnings.append(
                        f"Math check: subtotal + tax ({calculated_total}) "
                        f"≠ total_amount ({total_amount})"
                    )
        else:
            if record['document_type'] == 'text':
                warnings.append(
                    "Cannot verify math: missing numeric values for "
                    "subtotal/tax/total_amount"
                )
        
        return math_checks
    
    def _validate_line_items(
        self, 
        line_items: List[Dict], 
        errors: List[str], 
        warnings: List[str]
    ) -> List[Dict[str, Any]]:
        """Check: quantity × unit_price ≈ total_price"""
        checks = []
        
        for idx, item in enumerate(line_items, 1):
            check = {
                'line_number': idx,
                'description': item.get('description', '')[:50],  # First 50 chars
                'is_valid': True,
                'issues': []
            }
            
            quantity = self._parse_numeric(item.get('quantity', ''))
            unit_price = self._parse_numeric(item.get('unit_price', ''))
            total_price = self._parse_numeric(item.get('total_price', ''))
            
            # Check if quantity looks like metadata
            if quantity and quantity > 10000:
                check['issues'].append(
                    f"Suspicious quantity: {quantity} (may be article/regulation number)"
                )
                check['is_valid'] = False
                warnings.append(
                    f"Line {idx}: Suspicious quantity ({quantity}) - "
                    f"likely metadata not item quantity"
                )
            
            # Check quantity × unit_price ≈ total_price
            if quantity is not None and unit_price is not None and total_price is not None:
                calculated_total = quantity * unit_price
                
                if total_price == 0 and calculated_total == 0:
                    check['matches_price'] = True
                elif calculated_total > 0:
                    percentage_diff = abs(calculated_total - total_price) / calculated_total
                    
                    if percentage_diff <= self.TOLERANCE:
                        check['matches_price'] = True
                    else:
                        check['matches_price'] = False
                        check['issues'].append(
                            f"qty({quantity}) × unit_price({unit_price}) = "
                            f"{calculated_total}, but total_price = {total_price} "
                            f"({percentage_diff*100:.1f}% diff)"
                        )
                        check['is_valid'] = False
                else:
                    check['matches_price'] = (calculated_total == total_price)
                    if not check['matches_price']:
                        check['issues'].append(
                            f"Price mismatch: calculated={calculated_total}, "
                            f"total_price={total_price}"
                        )
                        check['is_valid'] = False
            elif (quantity or unit_price or total_price) and not (quantity and unit_price and total_price):
                check['issues'].append(
                    "Incomplete price data: missing one or more of "
                    "[quantity, unit_price, total_price]"
                )
            
            checks.append(check)
        
        return checks
    
    def _check_ocr_quality(
        self, 
        record: Dict, 
        warnings: List[str]
    ) -> Dict[str, Any]:
        """Detect OCR issues in scanned documents"""
        checks = {
            'has_garbled_text': False,
            'has_missing_rows': False,
            'confidence_very_low': False,
            'issues': []
        }
        
        # Check confidence score
        confidence = record.get('confidence_score', 0)
        if confidence == 0:
            checks['confidence_very_low'] = True
            checks['issues'].append(
                f"Confidence score is 0% - no data extracted via OCR"
            )
            warnings.append("OCR: No extraction - confidence 0%")
        elif confidence < 20:
            checks['confidence_very_low'] = True
            checks['issues'].append(
                f"Very low confidence score: {confidence}% - quality concerns"
            )
            warnings.append(f"OCR: Very low confidence {confidence}%")
        
        # Check for garbled text patterns
        if record.get('line_items'):
            for item in record['line_items']:
                description = item.get('description', '')
                
                # Garbled text patterns
                garbled_patterns = [
                    r'[^\w\s\-\.,áéíóúñü():/]',  # Non-standard characters
                    r'[\x00-\x1F]',  # Control characters
                ]
                
                for pattern in garbled_patterns:
                    if re.search(pattern, description):
                        checks['has_garbled_text'] = True
                        checks['issues'].append(
                            f"Potential garbled text detected: '{description[:30]}...'"
                        )
                        break
        
        # Check if line_items seems incomplete
        if record.get('line_items') and len(record['line_items']) == 1:
            checks['has_missing_rows'] = True
            checks['issues'].append(
                "Very few line items (1) - may indicate incomplete OCR extraction"
            )
        
        return checks
    
    def _parse_numeric(self, value: Any) -> float:
        """Safely parse numeric value"""
        if not value or value == "":
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            value = value.strip()
            
            # Remove currency symbols and whitespace
            value = re.sub(r'[^\d\.,\-]', '', value)
            
            # Handle different decimal separators
            if ',' in value and '.' in value:
                # Format like 1,234.56 or 1.234,56
                if value.rfind(',') > value.rfind('.'):
                    # 1.234,56 format
                    value = value.replace('.', '').replace(',', '.')
                else:
                    # 1,234.56 format
                    value = value.replace(',', '')
            else:
                # Use whichever separator exists
                value = value.replace(',', '.')
            
            try:
                return float(value)
            except ValueError:
                return None
        
        return None
    
    def _enhance_record(
        self, 
        record: Dict, 
        validation: ValidationResult
    ) -> Dict:
        """Add validation results to record"""
        enhanced = record.copy()
        enhanced['validation'] = {
            'is_valid': validation.is_valid,
            'errors': validation.errors,
            'warnings': validation.warnings,
            'math_checks': validation.math_checks,
            'field_checks': validation.field_checks,
            'line_item_checks': validation.line_item_checks,
        }
        
        if validation.ocr_checks:
            enhanced['validation']['ocr_checks'] = validation.ocr_checks
        
        return enhanced
    
    def _print_validation(self, validation: ValidationResult):
        """Print validation results"""
        status = "✅ VALID" if validation.is_valid else "❌ INVALID"
        print(f"Status: {status}\n")
        
        # Errors
        if validation.errors:
            print(f"🔴 ERRORS ({len(validation.errors)}):")
            for error in validation.errors:
                print(f"   • {error}")
            print()
        
        # Warnings
        if validation.warnings:
            print(f"🟡 WARNINGS ({len(validation.warnings)}):")
            for warning in validation.warnings:
                print(f"   • {warning}")
            print()
        
        # Field checks
        if validation.field_checks:
            complete_fields = sum(1 for v in validation.field_checks.values() if v)
            total_fields = len(validation.field_checks)
            print(f"📋 FIELDS: {complete_fields}/{total_fields} present")
            for field, present in validation.field_checks.items():
                status_icon = "✓" if present else "✗"
                print(f"   {status_icon} {field}")
            print()
        
        # Math checks
        if validation.math_checks:
            print(f"🧮 MATH CHECKS:")
            for check, result in validation.math_checks.items():
                status_icon = "✓" if result else "✗"
                check_label = check.replace('_', ' ').title()
                print(f"   {status_icon} {check_label}")
            print()
        
        # Line item validation
        if validation.line_item_checks:
            valid_items = sum(1 for c in validation.line_item_checks if c['is_valid'])
            total_items = len(validation.line_item_checks)
            print(f"📦 LINE ITEMS: {valid_items}/{total_items} valid")
            
            # Only print items with issues
            for check in validation.line_item_checks:
                if check['issues']:
                    print(f"   Line {check['line_number']}: {check['description']}")
                    for issue in check['issues']:
                        print(f"      ⚠️ {issue}")
            print()
        
        # OCR checks
        if validation.ocr_checks:
            print(f"🔬 OCR QUALITY:")
            has_issues = bool(validation.ocr_checks.get('issues'))
            if has_issues:
                for issue in validation.ocr_checks['issues']:
                    print(f"   ⚠️ {issue}")
            else:
                print(f"   ✓ No OCR issues detected")
            print()
        
        print()
    
    def generate_report(self, output_path: str = None) -> str:
        """Generate comprehensive validation report"""
        if output_path is None:
            output_path = str(
                self.extracted_json_path.parent / 'VALIDATION_REPORT.md'
            )
        
        total_records = len(self.validated_records)
        valid_records = sum(
            1 for r in self.validated_records 
            if r.get('validation', {}).get('is_valid', False)
        )
        total_errors = sum(
            len(r.get('validation', {}).get('errors', []))
            for r in self.validated_records
        )
        total_warnings = sum(
            len(r.get('validation', {}).get('warnings', []))
            for r in self.validated_records
        )
        
        report = f"""# Procurement Data Validation Report

**Generated:** {self._get_timestamp()}

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Records** | {total_records} |
| **Valid Records** | {valid_records}/{total_records} ({100*valid_records//total_records}%) |
| **Total Errors** | {total_errors} |
| **Total Warnings** | {total_warnings} |
| **Validation Pass Rate** | {100*valid_records//total_records}% |

## Validation Rules Applied

### 1. Field Completeness Check
- Critical fields checked: supplier, invoice_or_po_number, issue_date, total_amount
- Text-based documents: STRICT (all fields required)
- Scanned documents: LENIENT (fields expected but not required due to OCR limitations)

### 2. Math Consistency Check
- Rule: `subtotal + tax ≈ total_amount`
- Tolerance: ±{self.TOLERANCE*100}%
- Applied to: Text-based documents only

### 3. Line Item Validation
- Rule: `quantity × unit_price ≈ total_price`
- Tolerance: ±{self.TOLERANCE*100}%
- Metadata detection: Flags suspicious quantities (>10,000)

### 4. OCR Quality Check
- Confidence score assessment
- Garbled text detection
- Missing rows indication
- Applied to: Scanned documents only

---

## Detailed Results

"""
        
        for idx, record in enumerate(self.validated_records, 1):
            validation = record.get('validation', {})
            status = "✅ VALID" if validation.get('is_valid') else "❌ INVALID"
            
            report += f"### Document {idx}: {record['document_name']}\n\n"
            report += f"**Status:** {status}\n\n"
            report += f"**Type:** {record['document_type']}\n"
            report += f"**Confidence:** {record['confidence_score']}%\n\n"
            
            # Errors
            if validation.get('errors'):
                report += f"**Errors ({len(validation['errors'])}):**\n"
                for error in validation['errors']:
                    report += f"- 🔴 {error}\n"
                report += "\n"
            
            # Warnings
            if validation.get('warnings'):
                report += f"**Warnings ({len(validation['warnings'])}):**\n"
                for warning in validation['warnings']:
                    report += f"- 🟡 {warning}\n"
                report += "\n"
            
            # Field checks
            if validation.get('field_checks'):
                report += f"**Field Completeness:**\n"
                for field, present in validation['field_checks'].items():
                    icon = "✓" if present else "✗"
                    report += f"- {icon} {field}\n"
                report += "\n"
            
            # Math checks
            if validation.get('math_checks'):
                report += f"**Math Consistency:**\n"
                for check, result in validation['math_checks'].items():
                    icon = "✓" if result else "✗"
                    label = check.replace('_', ' ').title()
                    report += f"- {icon} {label}\n"
                report += "\n"
            
            # Line item checks
            if validation.get('line_item_checks'):
                items_with_issues = [
                    c for c in validation['line_item_checks'] 
                    if c.get('issues')
                ]
                if items_with_issues:
                    report += f"**Line Item Issues ({len(items_with_issues)}):**\n"
                    for check in items_with_issues:
                        report += f"- Line {check['line_number']}: {check['description']}\n"
                        for issue in check['issues']:
                            report += f"  - {issue}\n"
                    report += "\n"
            
            # OCR checks
            if validation.get('ocr_checks'):
                if validation['ocr_checks'].get('issues'):
                    report += f"**OCR Quality Issues:**\n"
                    for issue in validation['ocr_checks']['issues']:
                        report += f"- {issue}\n"
                    report += "\n"
            
            report += "---\n\n"
        
        # Recommendations
        report += f"## Recommendations\n\n"
        
        if total_errors > 0:
            report += f"### 🔴 Critical Issues ({total_errors})\n"
            report += f"- Review and correct {total_errors} validation error(s) before proceeding\n"
            report += f"- Do NOT auto-correct - investigate root cause\n"
            report += f"- May require re-extraction or manual review\n\n"
        
        if total_warnings > 0:
            report += f"### 🟡 Warnings ({total_warnings})\n"
            report += f"- {total_warnings} warning(s) detected\n"
            report += f"- Review for data quality issues\n"
            report += f"- May indicate incomplete OCR or missing fields\n\n"
        
        if valid_records == total_records:
            report += f"### ✅ All Records Valid\n"
            report += f"- All {total_records} record(s) passed validation\n"
            report += f"- Ready for downstream processing\n"
        else:
            invalid_count = total_records - valid_records
            report += f"### ⚠️ Invalid Records ({invalid_count})\n"
            report += f"- {invalid_count}/{total_records} record(s) require attention\n"
            report += f"- Success rate: {100*valid_records//total_records}%\n"
        
        # Write report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n{'='*80}")
        print(f"✅ Validation report saved: {output_path}")
        print(f"{'='*80}\n")
        
        return output_path
    
    def save_validated_json(self, output_path: str = None) -> str:
        """Save validated records to JSON"""
        if output_path is None:
            output_path = str(
                self.extracted_json_path.parent / 'validated_procurement.json'
            )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.validated_records, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Validated JSON saved: {output_path}")
        return output_path
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    """Main execution"""
    # Path to extracted procurement data
    extracted_path = Path(__file__).parent / 'output' / 'extracted_procurement.json'
    
    # Initialize validator
    validator = ProcurementValidator(str(extracted_path))
    
    # Validate all records
    validated_records = validator.validate_all()
    
    # Save validated JSON
    json_output = validator.save_validated_json()
    
    # Generate report
    report_output = validator.generate_report()
    
    print(f"\n{'='*80}")
    print("VALIDATION COMPLETE")
    print(f"{'='*80}")
    print(f"📊 Validated JSON: {json_output}")
    print(f"📄 Validation Report: {report_output}")
    print(f"{'='*80}\n")
    
    return validated_records


if __name__ == '__main__':
    main()
