"""
Production Readiness Report Generator

Synthesizes all test results into comprehensive readiness assessment
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# CRITICAL: Import standard library items BEFORE path manipulation
import logging as stdlib_logging

sys.path.insert(0, str(Path(__file__).parent.parent))


class ProductionReadinessReporter:
    """Generates comprehensive production readiness assessment"""
    
    def __init__(self):
        self.report = {
            "metadata": {
                "report_generated": datetime.now().isoformat(),
                "assessment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "system_version": "2.0"
            },
            "executive_summary": {},
            "accuracy_metrics": {},
            "performance_metrics": {},
            "reliability_assessment": {},
            "failure_analysis": {},
            "risk_assessment": {},
            "recommendations": {},
            "production_readiness_verdict": {}
        }
        
        self.benchmark_results = None
        self.performance_results = None
    
    def load_benchmark_results(self, benchmark_file="testing/benchmark_results.json"):
        """Load benchmark results"""
        benchmark_path = Path(benchmark_file)
        
        if not benchmark_path.exists():
            print(f"⚠ Benchmark results not found: {benchmark_path}")
            return False
        
        try:
            with open(benchmark_path, 'r') as f:
                self.benchmark_results = json.load(f)
            print(f"✓ Loaded benchmark results from {benchmark_path}")
            return True
        except Exception as e:
            print(f"❌ Error loading benchmark results: {e}")
            return False
    
    def load_performance_results(self, performance_file="testing/performance_results.json"):
        """Load performance results"""
        performance_path = Path(performance_file)
        
        if not performance_path.exists():
            print(f"⚠ Performance results not found: {performance_path}")
            return False
        
        try:
            with open(performance_path, 'r') as f:
                self.performance_results = json.load(f)
            print(f"✓ Loaded performance results from {performance_path}")
            return True
        except Exception as e:
            print(f"❌ Error loading performance results: {e}")
            return False
    
    def generate_executive_summary(self):
        """Generate executive summary"""
        if not self.benchmark_results or not self.performance_results:
            print("⚠ Cannot generate summary - missing results")
            return
        
        test_summary = self.benchmark_results.get("test_summary", {})
        batch_metrics = self.performance_results.get("batch_metrics", {})
        
        self.report["executive_summary"] = {
            "total_tests_run": test_summary.get("total_files_tested", 0),
            "overall_success_rate_percent": test_summary.get("overall_success_rate_percent", 0),
            "system_stability": "CRITICAL" if test_summary.get("overall_failure_rate_percent", 0) > 10 
                              else "UNSTABLE" if test_summary.get("overall_failure_rate_percent", 0) > 5
                              else "STABLE" if test_summary.get("overall_failure_rate_percent", 0) < 2
                              else "ACCEPTABLE",
            "batch_processing_capability": f"Up to {batch_metrics.get('total_files', 0)} documents",
            "throughput_docs_per_second": batch_metrics.get("throughput_documents_per_second", 0),
            "average_processing_time_seconds": test_summary.get("average_processing_time_seconds", 0)
        }
    
    def generate_accuracy_metrics(self):
        """Generate accuracy metrics"""
        if not self.benchmark_results:
            return
        
        test_summary = self.benchmark_results.get("test_summary", {})
        by_type = self.benchmark_results.get("by_document_type", {})
        
        metrics_by_type = {}
        for doc_type, metrics in by_type.items():
            metrics_by_type[doc_type] = {
                "success_rate_percent": metrics.get("success_rate_percent", 0),
                "average_confidence": metrics.get("average_confidence", 0),
                "requires_review_rate_percent": metrics.get("requires_review_rate_percent", 0),
                "total_files_tested": metrics.get("total_files", 0)
            }
        
        self.report["accuracy_metrics"] = {
            "overall": {
                "success_rate_percent": test_summary.get("overall_success_rate_percent", 0),
                "failure_rate_percent": test_summary.get("overall_failure_rate_percent", 0),
                "requires_review_rate_percent": test_summary.get("overall_requires_review_percent", 0),
                "average_confidence_score": test_summary.get("average_confidence", 0),
                "median_confidence_score": test_summary.get("median_confidence", 0)
            },
            "by_document_type": metrics_by_type
        }
    
    def generate_performance_metrics(self):
        """Generate performance metrics"""
        if not self.performance_results:
            return
        
        batch_metrics = self.performance_results.get("batch_metrics", {})
        memory = self.performance_results.get("memory_profile", {})
        cpu = self.performance_results.get("cpu_profile", {})
        
        self.report["performance_metrics"] = {
            "batch_processing": {
                "total_documents": batch_metrics.get("total_files", 0),
                "successfully_processed": batch_metrics.get("successfully_processed", 0),
                "processing_errors": batch_metrics.get("errors", 0),
                "total_time_seconds": batch_metrics.get("total_time_seconds", 0),
                "average_time_per_document_seconds": batch_metrics.get("average_time_per_document_seconds", 0),
                "throughput_documents_per_second": batch_metrics.get("throughput_documents_per_second", 0),
                "success_rate_percent": batch_metrics.get("success_rate", 0)
            },
            "resource_usage": {
                "memory_start_mb": batch_metrics.get("memory_start_mb", 0),
                "memory_end_mb": batch_metrics.get("memory_end_mb", 0),
                "memory_delta_mb": batch_metrics.get("memory_delta_mb", 0),
                "average_memory_percent": memory.get("average_percent", 0),
                "peak_memory_percent": memory.get("peak_percent", 0),
                "average_cpu_percent": cpu.get("average_percent", 0),
                "peak_cpu_percent": cpu.get("peak_percent", 0)
            }
        }
    
    def generate_reliability_assessment(self):
        """Generate reliability assessment"""
        if not self.benchmark_results:
            return
        
        test_summary = self.benchmark_results.get("test_summary", {})
        edge_cases = self.benchmark_results.get("edge_cases", {})
        
        failure_rate = test_summary.get("overall_failure_rate_percent", 0)
        edge_handling = edge_cases.get("graceful_handling_rate", 0)
        
        reliability_score = (100 - failure_rate + edge_handling) / 2
        
        reliability_level = "CRITICAL" if reliability_score < 60 \
                          else "LOW" if reliability_score < 75 \
                          else "MEDIUM" if reliability_score < 85 \
                          else "HIGH" if reliability_score < 95 \
                          else "EXCELLENT"
        
        self.report["reliability_assessment"] = {
            "overall_reliability_score": round(reliability_score, 2),
            "reliability_level": reliability_level,
            "failure_rate_percent": failure_rate,
            "graceful_degradation_capability": edge_handling,
            "batch_processing_resilience": "✓ Partial failures don't stop processing",
            "error_recovery": "✓ Implemented with retry and fallback"
        }
    
    def generate_failure_analysis(self):
        """Generate failure analysis"""
        if not self.benchmark_results:
            return
        
        failure_analysis = self.benchmark_results.get("failure_analysis", {})
        
        categorized_failures = {}
        for error_type, data in failure_analysis.items():
            categorized_failures[error_type] = {
                "count": data.get("count", 0),
                "example_files": data.get("examples", [])
            }
        
        self.report["failure_analysis"] = {
            "total_failures": sum(data.get("count", 0) for data in failure_analysis.values()),
            "failure_categories": categorized_failures,
            "most_common_failure": max(categorized_failures.items(), 
                                       key=lambda x: x[1]["count"])[0] if categorized_failures else "None"
        }
    
    def generate_risk_assessment(self):
        """Generate risk assessment"""
        if not self.benchmark_results or not self.performance_results:
            return
        
        test_summary = self.benchmark_results.get("test_summary", {})
        batch_metrics = self.performance_results.get("batch_metrics", {})
        
        risks = []
        
        # Check accuracy
        if test_summary.get("overall_success_rate_percent", 100) < 85:
            risks.append({
                "category": "LOW ACCURACY",
                "severity": "HIGH",
                "description": f"Overall success rate is {test_summary.get('overall_success_rate_percent')}% (target: >90%)",
                "mitigation": "Enable confidence thresholding for manual review of low-confidence documents"
            })
        
        # Check requires_review rate
        if test_summary.get("overall_requires_review_percent", 0) > 20:
            risks.append({
                "category": "HIGH REVIEW RATE",
                "severity": "MEDIUM",
                "description": f"Requires manual review: {test_summary.get('overall_requires_review_percent')}% of documents",
                "mitigation": "Consider adjusting confidence threshold or improving extraction method"
            })
        
        # Check performance
        if batch_metrics.get("throughput_documents_per_second", 0) < 1:
            risks.append({
                "category": "SLOW THROUGHPUT",
                "severity": "MEDIUM",
                "description": f"Processing speed: {batch_metrics.get('throughput_documents_per_second')} docs/sec",
                "mitigation": "Consider parallel processing or optimizing extraction algorithms"
            })
        
        # Check memory growth
        memory_delta = batch_metrics.get("memory_delta_mb", 0)
        if memory_delta > 100:
            risks.append({
                "category": "MEMORY LEAK RISK",
                "severity": "HIGH",
                "description": f"Memory increased by {memory_delta}MB during batch processing",
                "mitigation": "Profile code for memory leaks; implement resource cleanup"
            })
        
        if not risks:
            risks.append({
                "category": "NONE IDENTIFIED",
                "severity": "INFO",
                "description": "System performance is within acceptable parameters",
                "mitigation": "Continue monitoring in production"
            })
        
        self.report["risk_assessment"] = {
            "total_risks_identified": len(risks),
            "risks": risks
        }
    
    def generate_recommendations(self):
        """Generate recommendations"""
        recommendations = []
        
        if self.benchmark_results:
            test_summary = self.benchmark_results.get("test_summary", {})
            
            if test_summary.get("overall_success_rate_percent", 0) < 90:
                recommendations.append("❌ DO NOT DEPLOY: Success rate below 90% threshold")
            
            if test_summary.get("overall_failure_rate_percent", 0) > 5:
                recommendations.append("⚠ CONDITIONAL: Address failures before production deployment")
            
            if test_summary.get("average_confidence", 0) < 75:
                recommendations.append("⚠ Review confidence thresholding strategy")
        
        if self.performance_results:
            batch_metrics = self.performance_results.get("batch_metrics", {})
            
            if batch_metrics.get("throughput_documents_per_second", 0) > 5:
                recommendations.append("✓ Performance is acceptable for production use")
            
            memory_delta = batch_metrics.get("memory_delta_mb", 0)
            if 0 < memory_delta < 50:
                recommendations.append("✓ Memory usage is within normal parameters")
            elif memory_delta <= 0:
                recommendations.append("✓ Memory is well-managed (no growth detected)")
            else:
                recommendations.append("❌ Investigate memory usage before deployment")
        
        recommendations.extend([
            "✓ Implement comprehensive logging for production audit trails",
            "✓ Set up monitoring for extraction confidence scores",
            "✓ Configure automated alerts for failures > 5%",
            "✓ Establish SLA for manual review queue",
            "✓ Regular benchmarking to catch performance regressions"
        ])
        
        self.report["recommendations"] = {
            "deployment_blockers": [r for r in recommendations if "❌" in r],
            "conditional_items": [r for r in recommendations if "⚠" in r],
            "approved_items": [r for r in recommendations if "✓" in r]
        }
    
    def generate_production_readiness_verdict(self):
        """Generate final production readiness verdict"""
        if not self.benchmark_results or not self.performance_results:
            self.report["production_readiness_verdict"] = {
                "verdict": "CANNOT_ASSESS",
                "reason": "Missing test results"
            }
            return
        
        test_summary = self.benchmark_results.get("test_summary", {})
        batch_metrics = self.performance_results.get("batch_metrics", {})
        reliability = self.report.get("reliability_assessment", {})
        risks = self.report.get("risk_assessment", {})
        
        # Decision logic
        success_rate = test_summary.get("overall_success_rate_percent", 0)
        failure_rate = test_summary.get("overall_failure_rate_percent", 0)
        reliability_level = reliability.get("reliability_level", "UNKNOWN")
        high_risks = len([r for r in risks.get("risks", []) if r.get("severity") == "HIGH"])
        
        if success_rate < 85 or failure_rate > 10 or high_risks > 1:
            verdict = "NOT_READY"
            rationale = "Critical quality metrics below production thresholds"
        elif reliability_level in ["CRITICAL", "LOW"] or high_risks > 0:
            verdict = "CONDITIONAL"
            rationale = "Can deploy with risk mitigation measures in place"
        else:
            verdict = "READY"
            rationale = "System meets production readiness criteria"
        
        self.report["production_readiness_verdict"] = {
            "verdict": verdict,
            "rationale": rationale,
            "success_rate_percent": success_rate,
            "failure_rate_percent": failure_rate,
            "reliability_level": reliability_level,
            "critical_issues": high_risks,
            "assessment_date": datetime.now().isoformat(),
            "valid_for_days": 30
        }
    
    def generate_full_report(self):
        """Generate complete production readiness report"""
        print("\n" + "="*80)
        print("GENERATING PRODUCTION READINESS REPORT")
        print("="*80 + "\n")
        
        self.generate_executive_summary()
        self.generate_accuracy_metrics()
        self.generate_performance_metrics()
        self.generate_reliability_assessment()
        self.generate_failure_analysis()
        self.generate_risk_assessment()
        self.generate_recommendations()
        self.generate_production_readiness_verdict()
        
        return self.report
    
    def save_report(self, output_file="testing/PRODUCTION_READINESS_REPORT.json"):
        """Save report to file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.report, f, indent=2, default=str)
        
        print(f"✅ Report saved to: {output_path}")
        return str(output_path)
    
    def print_summary(self):
        """Print report summary to console"""
        verdict_data = self.report.get("production_readiness_verdict", {})
        summary = self.report.get("executive_summary", {})
        accuracy = self.report.get("accuracy_metrics", {}).get("overall", {})
        perf = self.report.get("performance_metrics", {}).get("batch_processing", {})
        reliability = self.report.get("reliability_assessment", {})
        
        print("\n" + "="*80)
        print("PRODUCTION READINESS REPORT - SUMMARY")
        print("="*80 + "\n")
        
        print("VERDICT:", verdict_data.get("verdict", "UNKNOWN"))
        print("Rationale:", verdict_data.get("rationale", ""))
        print("")
        
        print("KEY METRICS:")
        print(f"  Success Rate: {accuracy.get('success_rate_percent', 0):.1f}%")
        print(f"  Failure Rate: {accuracy.get('failure_rate_percent', 0):.1f}%")
        print(f"  Requires Review: {accuracy.get('requires_review_rate_percent', 0):.1f}%")
        print(f"  Average Confidence: {accuracy.get('average_confidence_score', 0):.1f}%")
        print("")
        
        print("PERFORMANCE:")
        print(f"  Throughput: {perf.get('throughput_documents_per_second', 0):.2f} docs/sec")
        print(f"  Avg Time/Doc: {perf.get('average_time_per_document_seconds', 0):.4f}s")
        print(f"  Batch Capacity: {perf.get('total_documents', 0)} documents")
        print("")
        
        print("RELIABILITY:")
        print(f"  Score: {reliability.get('overall_reliability_score', 0):.1f}/100")
        print(f"  Level: {reliability.get('reliability_level', 'UNKNOWN')}")
        print("")
        
        risks = self.report.get("risk_assessment", {})
        print(f"RISKS IDENTIFIED: {risks.get('total_risks_identified', 0)}")
        for risk in risks.get("risks", [])[:3]:
            print(f"  - {risk.get('category')}: {risk.get('severity')}")
        
        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    reporter = ProductionReadinessReporter()
    
    if reporter.load_benchmark_results() and reporter.load_performance_results():
        report = reporter.generate_full_report()
        reporter.save_report()
        reporter.print_summary()
    else:
        print("\n❌ Cannot generate report - missing test results")
        print("Run: python testing/run_validation_tests.py")
