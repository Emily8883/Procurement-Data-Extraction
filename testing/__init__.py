"""
Testing and Validation Module

Provides comprehensive validation framework for procurement extraction system:
- Test data generation (realistic documents + edge cases)
- Accuracy benchmarking (extraction, validation, routing)
- Performance profiling (throughput, memory, CPU)
- Production readiness assessment
"""

# Lazy imports to avoid namespace collisions
def get_test_data_generator():
    from testing.test_data_generator import TestDataGenerator
    return TestDataGenerator

def get_benchmark_harness():
    from testing.benchmark_harness import BenchmarkHarness
    return BenchmarkHarness

def get_performance_profiler():
    from testing.performance_benchmarks import PerformanceProfiler
    return PerformanceProfiler

def get_readiness_reporter():
    from testing.readiness_reporter import ProductionReadinessReporter
    return ProductionReadinessReporter

__all__ = [
    'get_test_data_generator',
    'get_benchmark_harness',
    'get_performance_profiler',
    'get_readiness_reporter'
]
