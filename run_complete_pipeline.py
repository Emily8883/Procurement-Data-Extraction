#!/usr/bin/env python3
"""
Complete Procurement Extraction Pipeline Orchestrator

Executes the full procurement data extraction pipeline with all stages:
  1. Document Classification (TEXT vs SCANNED)
  2. Data Extraction (dual-method: text parser + OCR)
  3. Data Normalization (JSON structure)
  4. Data Cleaning (standardization + QA)
  5. Validation & Quality Control (NEW)

Usage: python run_complete_pipeline.py
"""

import sys
import time
from pathlib import Path


def print_banner(title: str):
    """Print formatted banner"""
    width = 80
    print(f"\n{'='*width}")
    print(f"  {title}".center(width))
    print(f"{'='*width}\n")


def print_stage(stage_num: int, name: str, status: str = ""):
    """Print stage header"""
    marker = f"[{stage_num}/5]"
    if status:
        print(f"{marker} {name}: {status}\n")
    else:
        print(f"{marker} {name}\n")


def run_stage(stage_num: int, name: str, module_path: str, description: str):
    """Run a pipeline stage"""
    print_stage(stage_num, name)
    print(f"   {description}\n")
    
    try:
        # Import and execute the module's main function
        spec = __import__('importlib.util').util.spec_from_file_location("module", module_path)
        module = __import__('importlib.util').util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'main'):
            module.main()
        
        print(f"✅ {name} COMPLETE\n")
        return True
        
    except Exception as e:
        print(f"❌ {name} FAILED: {str(e)}\n")
        return False


def main():
    """Execute complete pipeline"""
    
    print_banner("COMPLETE PROCUREMENT EXTRACTION PIPELINE")
    print("Executing all 5 pipeline stages with validation layer\n")
    
    workspace = Path(__file__).parent
    results = []
    
    start_time = time.time()
    
    # === STAGE 1: DOCUMENT CLASSIFICATION ===
    success = run_stage(
        1, 
        "DOCUMENT CLASSIFICATION",
        str(workspace / 'classify_documents.py'),
        "Detect TEXT-BASED (selectable) vs SCANNED (image) documents"
    )
    results.append(('Classification', success))
    
    if not success:
        print("⚠️  Pipeline halted - classification required for extraction\n")
        return
    
    # === STAGE 2: PROCUREMENT EXTRACTION ===
    success = run_stage(
        2,
        "PROCUREMENT DATA EXTRACTION",
        str(workspace / 'extract_procurement.py'),
        "Extract structured fields using appropriate method per document type"
    )
    results.append(('Extraction', success))
    
    if not success:
        print("⚠️  Pipeline halted - extraction failed\n")
        return
    
    # === STAGE 3: DATA NORMALIZATION ===
    success = run_stage(
        3,
        "DATA NORMALIZATION",
        str(workspace / 'normalize_to_json.py'),
        "Convert raw extraction to required JSON schema with null fields"
    )
    results.append(('Normalization', success))
    
    # === STAGE 4: DATA CLEANING ===
    success = run_stage(
        4,
        "DATA CLEANING & STANDARDIZATION",
        str(workspace / 'clean_dataset.py'),
        "Standardize data, fix OCR errors, preserve originals in raw_value fields"
    )
    results.append(('Cleaning', success))
    
    # === STAGE 5: VALIDATION & QUALITY CONTROL (NEW) ===
    success = run_stage(
        5,
        "VALIDATION & QUALITY CONTROL",
        str(workspace / 'validate_and_qa.py'),
        "Apply strict financial consistency checks without auto-correction"
    )
    results.append(('Validation', success))
    
    # === SUMMARY ===
    elapsed = time.time() - start_time
    
    print_banner("PIPELINE EXECUTION SUMMARY")
    
    print("Stage Results:\n")
    for stage_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}  {stage_name}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} stages completed successfully")
    print(f"Execution time: {elapsed:.2f}s")
    
    if passed == total:
        print("\n✅ PIPELINE COMPLETE - ALL STAGES SUCCESSFUL")
        print("\nOutput files generated:")
        
        output_dir = workspace / 'output'
        if output_dir.exists():
            print("\n  JSON Data:")
            for json_file in sorted(output_dir.glob('*.json')):
                size_kb = json_file.stat().st_size / 1024
                print(f"    • {json_file.name} ({size_kb:.1f}KB)")
            
            print("\n  Reports:")
            for md_file in sorted(output_dir.glob('*.md')):
                size_kb = md_file.stat().st_size / 1024
                print(f"    • {md_file.name} ({size_kb:.1f}KB)")
            
            print("\n  CSV Files:")
            for csv_file in sorted(output_dir.glob('*.csv')):
                size_kb = csv_file.stat().st_size / 1024
                print(f"    • {csv_file.name} ({size_kb:.1f}KB)")
        
        print("\n" + "="*80)
        print("\n✅ Ready for downstream processing")
        print("\nNext steps:")
        print("  1. Review VALIDATION_REPORT.md for data quality assessment")
        print("  2. Check validated_procurement.json for validation results")
        print("  3. Filter records by is_valid flag for processing")
        print("  4. Investigate records with errors or warnings")
        print("\n" + "="*80 + "\n")
        
    else:
        print(f"\n❌ PIPELINE INCOMPLETE - {total-passed} stage(s) failed")
        print("\nReview error messages above for details")
        print("=" * 80 + "\n")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
