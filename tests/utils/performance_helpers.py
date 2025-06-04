import time
import psutil
import threading
from contextlib import contextmanager

class PerformanceMonitor:
    """Monitor performance metrics during test execution"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.peak_memory = 0
        self.initial_memory = 0
        self._monitoring = False
        self._monitor_thread = None
    
    def start(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.initial_memory = psutil.Process().memory_info().rss
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_memory)
        self._monitor_thread.start()
    
    def stop(self):
        """Stop performance monitoring"""
        self.end_time = time.time()
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join()
    
    def _monitor_memory(self):
        """Monitor memory usage in background thread"""
        while self._monitoring:
            current_memory = psutil.Process().memory_info().rss
            self.peak_memory = max(self.peak_memory, current_memory)
            time.sleep(0.1)
    
    @property
    def execution_time(self):
        """Get execution time in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def memory_increase(self):
        """Get memory increase in bytes"""
        return self.peak_memory - self.initial_memory

@contextmanager
def performance_monitor():
    """Context manager for performance monitoring"""
    monitor = PerformanceMonitor()
    monitor.start()
    try:
        yield monitor
    finally:
        monitor.stop()

def benchmark_function(func, *args, iterations=1, **kwargs):
    """Benchmark a function's performance"""
    times = []
    
    for _ in range(iterations):
        with performance_monitor() as monitor:
            result = func(*args, **kwargs)
        times.append(monitor.execution_time)
    
    return {
        'result': result,
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'iterations': iterations
    }
