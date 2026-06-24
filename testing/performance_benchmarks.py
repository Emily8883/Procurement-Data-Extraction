"""
Performance Testing Module

Measures:
- Batch processing speed (100 documents)
- Memory usage patterns
- CPU utilization
- Throughput (documents/second)
"""

import json
import os
import sys
import time
import psutil
import threading
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics

# CRITICAL: Import standard library logging BEFORE adding paths
import logging as stdlib_logging

sys.path.insert(0, str(Path(__file__).parent.parent))


class PerformanceProfiler:
    """Profiles system performance during batch processing"""
    
    def __init__(self, test_data_dir="testing/test_data"):
        self.test_data_dir = Path(test_data_dir)
        self.process = psutil.Process(os.getpid())
        
        self.metrics = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "batch_performance"
            },
            "batch_metrics": {},
            "memory_profile": {},
            "cpu_profile": {},
            "throughput_metrics": {},
            "resource_usage": {}
        }
        
        self.monitoring_active = False
        self.memory_samples = []
        self.cpu_samples = []
    
    def collect_test_files(self, max_files=100):
        """Collect test files for batch processing"""
        test_files = sorted(self.test_data_dir.glob("*.txt"))[:max_files]
        
        if not test_files:
            print(f"❌ No test files found in {self.test_data_dir}")
            return []
        
        print(f"✓ Found {len(test_files)} test files for batch processing")
        return test_files
    
    def start_resource_monitoring(self):
        """Start background thread to monitor resources"""
        self.monitoring_active = True
        self.memory_samples = []
        self.cpu_samples = []
        
        def monitor():
            while self.monitoring_active:
                try:
                    memory_percent = self.process.memory_percent()
                    cpu_percent = self.process.cpu_percent(interval=0.1)
                    
                    self.memory_samples.append(memory_percent)
                    self.cpu_samples.append(cpu_percent)
                    
                    time.sleep(0.5)  # Sample every 500ms
                except:
                    pass
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def stop_resource_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring_active = False
        time.sleep(0.5)  # Let thread finish
    
    def simulate_batch_processing(self, test_files):
        """Simulate batch processing of files"""
        print(f"\nProcessing {len(test_files)} files...")
        
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        self.start_resource_monitoring()
        
        processed = 0
        errors = 0
        
        try:
            for filepath in test_files:
                try:
                    # Simulate document processing
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Simulate extraction work
                    lines = content.split('\n')
                    markers = sum(1 for line in lines if any(m in line for m in ["Invoice", "Total", "Date"]))
                    
                    # Simulate validation
                    is_valid = len(content) > 20 and markers > 0
                    
                    processed += 1
                    
                    if (processed % 10) == 0:
                        elapsed = time.time() - start_time
                        throughput = processed / elapsed if elapsed > 0 else 0
                        print(f"  ✓ Processed {processed}/{len(test_files)} " +
                              f"({throughput:.2f} docs/sec)")
                except Exception as e:
                    errors += 1
                    print(f"  ✗ Error processing {filepath.name}: {e}")
        
        finally:
            self.stop_resource_monitoring()
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        total_time = end_time - start_time
        
        return {
            "total_files": len(test_files),
            "successfully_processed": processed,
            "errors": errors,
            "success_rate": (processed / len(test_files) * 100) if test_files else 0,
            "total_time_seconds": round(total_time, 2),
            "average_time_per_document_seconds": round(total_time / processed if processed > 0 else 0, 4),
            "throughput_documents_per_second": round(processed / total_time if total_time > 0 else 0, 2),
            "memory_start_mb": round(start_memory, 2),
            "memory_end_mb": round(end_memory, 2),
            "memory_delta_mb": round(end_memory - start_memory, 2)
        }
    
    def analyze_resource_usage(self):
        """Analyze resource usage samples"""
        memory_stats = {}
        cpu_stats = {}
        
        if self.memory_samples:
            memory_stats = {
                "average_percent": round(statistics.mean(self.memory_samples), 2),
                "peak_percent": round(max(self.memory_samples), 2),
                "min_percent": round(min(self.memory_samples), 2),
                "stdev": round(statistics.stdev(self.memory_samples) if len(self.memory_samples) > 1 else 0, 2)
            }
        
        if self.cpu_samples:
            cpu_stats = {
                "average_percent": round(statistics.mean(self.cpu_samples), 2),
                "peak_percent": round(max(self.cpu_samples), 2),
                "min_percent": round(min(self.cpu_samples), 2),
                "stdev": round(statistics.stdev(self.cpu_samples) if len(self.cpu_samples) > 1 else 0, 2)
            }
        
        return memory_stats, cpu_stats
    
    def run_performance_tests(self):
        """Run complete performance test suite"""
        print("\n" + "="*70)
        print("RUNNING PERFORMANCE BENCHMARKS")
        print("="*70)
        
        test_files = self.collect_test_files(max_files=100)
        
        if not test_files:
            print("❌ Cannot run performance tests - no test files")
            return None
        
        print(f"\nBatch Size: {len(test_files)} documents")
        
        # Run batch processing
        batch_results = self.simulate_batch_processing(test_files)
        self.metrics["batch_metrics"] = batch_results
        
        # Analyze resource usage
        memory_stats, cpu_stats = self.analyze_resource_usage()
        self.metrics["memory_profile"] = memory_stats
        self.metrics["cpu_profile"] = cpu_stats
        
        # Print summary
        print("\n" + "-"*70)
        print("PERFORMANCE TEST RESULTS")
        print("-"*70)
        print(f"Total Files: {batch_results['total_files']}")
        print(f"Successfully Processed: {batch_results['successfully_processed']}")
        print(f"Success Rate: {batch_results['success_rate']:.1f}%")
        print(f"Total Time: {batch_results['total_time_seconds']:.2f}s")
        print(f"Throughput: {batch_results['throughput_documents_per_second']:.2f} docs/sec")
        print(f"Avg Time/Doc: {batch_results['average_time_per_document_seconds']:.4f}s")
        print(f"\nMemory - Start: {batch_results['memory_start_mb']:.2f}MB, " +
              f"End: {batch_results['memory_end_mb']:.2f}MB, " +
              f"Delta: {batch_results['memory_delta_mb']:.2f}MB")
        
        if memory_stats:
            print(f"\nMemory (during processing):")
            print(f"  Average: {memory_stats['average_percent']:.2f}%")
            print(f"  Peak: {memory_stats['peak_percent']:.2f}%")
        
        print("-"*70 + "\n")
        
        return self.metrics
    
    def save_results(self, output_file="testing/performance_results.json"):
        """Save performance results"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)
        
        print(f"✅ Performance results saved to: {output_path}")
        return str(output_path)


if __name__ == "__main__":
    profiler = PerformanceProfiler()
    results = profiler.run_performance_tests()
    profiler.save_results()
