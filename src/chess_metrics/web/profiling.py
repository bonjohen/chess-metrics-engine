"""
Performance profiling utilities for the web application.
"""
import time
import functools
from typing import Callable, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store timing data
timing_data = {}


def profile_function(func: Callable) -> Callable:
    """Decorator to profile function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed = (end_time - start_time) * 1000  # Convert to milliseconds
        
        func_name = func.__name__
        if func_name not in timing_data:
            timing_data[func_name] = []
        timing_data[func_name].append(elapsed)
        
        logger.info(f"⏱️  {func_name}: {elapsed:.2f}ms")
        return result
    return wrapper


def profile_section(name: str):
    """Context manager to profile a code section."""
    class ProfileSection:
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            end_time = time.perf_counter()
            elapsed = (end_time - self.start_time) * 1000
            
            if name not in timing_data:
                timing_data[name] = []
            timing_data[name].append(elapsed)
            
            logger.info(f"⏱️  {name}: {elapsed:.2f}ms")
    
    return ProfileSection()


def get_timing_stats():
    """Get statistics for all profiled functions."""
    stats = {}
    for func_name, times in timing_data.items():
        if times:
            stats[func_name] = {
                'count': len(times),
                'total_ms': sum(times),
                'avg_ms': sum(times) / len(times),
                'min_ms': min(times),
                'max_ms': max(times)
            }
    return stats


def print_timing_report():
    """Print a formatted timing report."""
    stats = get_timing_stats()
    if not stats:
        print("No timing data collected.")
        return
    
    print("\n" + "="*80)
    print("PERFORMANCE PROFILING REPORT")
    print("="*80)
    
    # Sort by total time
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total_ms'], reverse=True)
    
    print(f"\n{'Function/Section':<40} {'Calls':>8} {'Total(ms)':>12} {'Avg(ms)':>12} {'Min(ms)':>12} {'Max(ms)':>12}")
    print("-"*80)
    
    for func_name, data in sorted_stats:
        print(f"{func_name:<40} {data['count']:>8} {data['total_ms']:>12.2f} {data['avg_ms']:>12.2f} {data['min_ms']:>12.2f} {data['max_ms']:>12.2f}")
    
    print("="*80 + "\n")


def clear_timing_data():
    """Clear all collected timing data."""
    timing_data.clear()

