"""
Production Readiness Validation Test Suite

Orchestrates:
1. Test data generation (40 realistic documents + edge cases)
2. Accuracy benchmarks (extraction, validation, routing)
3. Performance tests (100 document batch)
4. Edge case testing (corrupted, rotated, multi-language)
5. Production readiness report (metrics + verdict)
"""

import sys
import time
from pathlib import Path

# CRITICAL: Import standard library logging FIRST before path manipulation
# This prevents the local logging/ directory from shadowing it
import logging as stdlib_logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly without going through __init__ to avoid namespace collision
from testing.test_data_generator import TestDataGenerator
from testing.benchmark_harness import BenchmarkHarness
from testing.performance_benchmarks import PerformanceProfiler
from testing.readiness_reporter import ProductionReadinessReporter


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def run_validation_suite():
    """Run complete validation test suite"""
    
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  PROCUREMENT EXTRACTION SYSTEM - PRODUCTION READINESS VALIDATION".center(78) + "█")
    print("█" + "  Comprehensive Test Suite v2.0".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    # ========================================================================
    # PHASE 1: TEST DATA GENERATION
    # ========================================================================
    print_section("PHASE 1: TEST DATA GENERATION")
    
    print("Generating realistic test dataset...")
    print("  • 20 clean, well-formatted invoices")
    print("  • 10 degraded scanned documents")
    print("  • 10 specification sheets")
    print("  • 5 edge case files (corrupted, rotated, minimal, multilingual)\n")
    
    generator = TestDataGenerator(output_dir="testing/test_data")
    dataset_info = generator.generate_all()
    
    if dataset_info["total_files"] < 40:
        print(f"❌ FAILED: Expected ≥40 files, got {dataset_info['total_files']}")
        return False
    
    # ========================================================================
    # PHASE 2: ACCURACY BENCHMARKS
    # ========================================================================
    print_section("PHASE 2: ACCURACY BENCHMARKS")
    
    print("Running accuracy benchmarks on all document types...")
    print("Measuring: extraction confidence, validation results, routing decisions\n")
    
    harness = BenchmarkHarness(test_data_dir="testing/test_data")
    benchmark_results = harness.run_all_benchmarks()
    
    if not benchmark_results:
        print("❌ FAILED: Could not run accuracy benchmarks")
        return False
    
    harness.save_results()
    
    # Extract key metrics
    test_summary = benchmark_results.get("test_summary", {})
    overall_success = test_summary.get("overall_success_rate_percent", 0)
    overall_failure = test_summary.get("overall_failure_rate_percent", 0)
    
    print(f"\n📊 ACCURACY SUMMARY:")
    print(f"   Files Tested: {test_summary.get('total_files_tested', 0)}")
    print(f"   Success Rate: {overall_success:.1f}%")
    print(f"   Failure Rate: {overall_failure:.1f}%")
    print(f"   Avg Confidence: {test_summary.get('average_confidence', 0):.1f}%")
    print(f"   Requires Review: {test_summary.get('overall_requires_review_percent', 0):.1f}%")
    
    # ========================================================================
    # PHASE 3: PERFORMANCE BENCHMARKS
    # ========================================================================
    print_section("PHASE 3: PERFORMANCE BENCHMARKS")
    
    print("Running batch processing performance test...")
    print("Testing: throughput, memory usage, CPU utilization\n")
    
    profiler = PerformanceProfiler(test_data_dir="testing/test_data")
    performance_results = profiler.run_performance_tests()
    
    if not performance_results:
        print("❌ FAILED: Could not run performance benchmarks")
        return False
    
    profiler.save_results()
    
    batch_metrics = performance_results.get("batch_metrics", {})
    
    print(f"\n⚡ PERFORMANCE SUMMARY:")
    print(f"   Documents: {batch_metrics.get('total_files', 0)}")
    print(f"   Processed: {batch_metrics.get('successfully_processed', 0)}")
    print(f"   Throughput: {batch_metrics.get('throughput_documents_per_second', 0):.2f} docs/sec")
    print(f"   Total Time: {batch_metrics.get('total_time_seconds', 0):.2f}s")
    print(f"   Avg/Doc: {batch_metrics.get('average_time_per_document_seconds', 0):.4f}s")
    print(f"   Memory Delta: {batch_metrics.get('memory_delta_mb', 0):.2f}MB")
    
    # ========================================================================
    # PHASE 4: EDGE CASE ANALYSIS
    # ========================================================================
    print_section("PHASE 4: EDGE CASE ANALYSIS")
    
    edge_cases = benchmark_results.get("edge_cases", {})
    
    print(f"Edge Cases Tested: {edge_cases.get('total', 0)}")
    print(f"Gracefully Handled: {edge_cases.get('handled_gracefully', 0)}")
    print(f"Handling Rate: {edge_cases.get('graceful_handling_rate', 0):.1f}%\n")
    
    print("Edge Case Results:")
    edge_results = [r for r in harness.test_results if r["category"] == "edge_cases"]
    for result in edge_results:
        status_icon = "✓" if result["status"] != "FAILED" else "✗"
        print(f"  {status_icon} {result['file']}: {result['status']}")
    
    # ========================================================================
    # PHASE 5: FAILURE ANALYSIS
    # ========================================================================
    print_section("PHASE 5: FAILURE ANALYSIS")
    
    failure_analysis = benchmark_results.get("failure_analysis", {})
    total_failures = sum(data.get("count", 0) for data in failure_analysis.values())
    
    print(f"Total Failures: {total_failures}\n")
    
    if total_failures > 0:
        print("Failure Categories:")
        for error_type, data in failure_analysis.items():
            print(f"  • {error_type}: {data.get('count', 0)} occurrences")
    else:
        print("✅ No failures recorded!")
    
    # ========================================================================
    # PHASE 6: PRODUCTION READINESS REPORT
    # ========================================================================
    print_section("PHASE 6: PRODUCTION READINESS ASSESSMENT")
    
    print("Synthesizing all test results...")
    print("Generating production readiness verdict...\n")
    
    reporter = ProductionReadinessReporter()
    
    if not (reporter.load_benchmark_results() and reporter.load_performance_results()):
        print("❌ FAILED: Could not load test results for final report")
        return False
    
    report = reporter.generate_full_report()
    reporter.save_report()
    reporter.print_summary()
    
    # ========================================================================
    # FINAL VERDICT
    # ========================================================================
    print_section("FINAL PRODUCTION READINESS VERDICT")
    
    verdict_data = report.get("production_readiness_verdict", {})
    verdict = verdict_data.get("verdict", "UNKNOWN")
    rationale = verdict_data.get("rationale", "")
    
    if verdict == "READY":
        status_icon = "✅"
        print(f"{status_icon} VERDICT: PRODUCTION READY\n")
    elif verdict == "CONDITIONAL":
        status_icon = "⚠"
        print(f"{status_icon} VERDICT: CONDITIONAL (Risk mitigation required)\n")
    else:
        status_icon = "❌"
        print(f"{status_icon} VERDICT: NOT READY\n")
    
    print(f"Rationale: {rationale}\n")
    
    print("CRITICAL METRICS:")
    print(f"  • Success Rate: {verdict_data.get('success_rate_percent', 0):.1f}% (target: >90%)")
    print(f"  • Failure Rate: {verdict_data.get('failure_rate_percent', 0):.1f}% (target: <5%)")
    print(f"  • Reliability: {verdict_data.get('reliability_level', 'UNKNOWN')} (target: HIGH+)")
    print(f"  • Critical Issues: {verdict_data.get('critical_issues', 0)} (target: 0)")
    
    print("\nDEPLOYMENT RECOMMENDATIONS:")
    recommendations = report.get("recommendations", {})
    
    blockers = recommendations.get("deployment_blockers", [])
    if blockers:
        print("\n  ❌ BLOCKERS (Must address before deployment):")
        for blocker in blockers:
            print(f"    {blocker}")
    
    conditionals = recommendations.get("conditional_items", [])
    if conditionals:
        print("\n  ⚠ CONDITIONAL (Address if possible):")
        for item in conditionals[:3]:
            print(f"    {item}")
    
    approved = recommendations.get("approved_items", [])
    if approved:
        print("\n  ✓ APPROVED (Ready to proceed):")
        for item in approved[:5]:
            print(f"    {item}")
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
    print(f"\nDetailed Report: testing/PRODUCTION_READINESS_REPORT.json")
    print(f"Benchmark Results: testing/benchmark_results.json")
    print(f"Performance Results: testing/performance_results.json")
    print("\n" + "="*80 + "\n")
    
    # Return success if report was generated
    return True


if __name__ == "__main__":
    try:
        start_time = time.time()
        success = run_validation_suite()
        elapsed = time.time() - start_time
        
        print(f"\n✅ VALIDATION COMPLETE in {elapsed:.1f}s")
        
        if not success:
            print("\n❌ VALIDATION FAILED - Check errors above")
            sys.exit(1)
        else:
            print("\n✅ All validation tests completed successfully")
            print("📄 Review the Production Readiness Report for deployment decision")
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\n⚠ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
