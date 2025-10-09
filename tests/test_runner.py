#!/usr/bin/env python3
"""
Comprehensive test runner for RKE2 installer project
Usage: python tests/test_runner.py [options]
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, description=""):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description or cmd}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=False)
    end_time = time.time()
    
    duration = end_time - start_time
    status = "✅ PASSED" if result.returncode == 0 else "❌ FAILED"
    print(f"\n{status} ({duration:.2f}s): {description or cmd}")
    
    return result.returncode == 0

def run_unit_tests(verbose=False):
    """Run unit tests"""
    cmd = "python -m pytest tests/unit/ -v"
    if verbose:
        cmd += " -s"
    cmd += " --tb=short"
    
    return run_command(cmd, "Unit Tests")

def run_integration_tests(verbose=False):
    """Run integration tests"""
    cmd = "python -m pytest tests/integration/ -v -m integration"
    if verbose:
        cmd += " -s"
    cmd += " --tb=short"
    
    return run_command(cmd, "Integration Tests")

def run_e2e_tests(verbose=False):
    """Run end-to-end tests"""
    cmd = "python -m pytest tests/e2e/ -v -m e2e"
    if verbose:
        cmd += " -s"
    cmd += " --tb=short"
    
    return run_command(cmd, "End-to-End Tests")

def run_scenario_tests(verbose=False):
    """Run scenario-based tests"""
    cmd = "python -m pytest tests/scenarios/ -v"
    if verbose:
        cmd += " -s"
    cmd += " --tb=short"
    
    return run_command(cmd, "Scenario Tests")

def run_performance_tests(verbose=False):
    """Run performance tests"""
    cmd = "python -m pytest tests/ -v -m performance"
    if verbose:
        cmd += " -s"
    cmd += " --tb=short"
    
    return run_command(cmd, "Performance Tests")

def run_security_tests(verbose=False):
    """Run security tests"""
    cmd = "python -m pytest tests/ -v -m security"
    if verbose:
        cmd += " -s"
    cmd += " --tb=short"
    
    return run_command(cmd, "Security Tests")

def run_smoke_tests(verbose=False):
    """Run smoke tests for quick validation"""
    cmd = "python -m pytest tests/ -v -m smoke"
    if verbose:
        cmd += " -s"
    cmd += " --tb=short"
    
    return run_command(cmd, "Smoke Tests")

def run_quick_tests():
    """Run the quick test script"""
    cmd = "python tests/quick_tests.py"
    return run_command(cmd, "Quick Tests")

def run_coverage_report():
    """Generate test coverage report"""
    print("\n" + "="*60)
    print("Generating Coverage Report")
    print("="*60)
    
    # Install coverage if not available
    subprocess.run([sys.executable, "-m", "pip", "install", "coverage"], 
                  capture_output=True)
    
    # Run tests with coverage
    cmd = f"python -m coverage run --source=. -m pytest tests/unit/ tests/integration/"
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        # Generate coverage report
        subprocess.run(["python", "-m", "coverage", "report", "-m"])
        subprocess.run(["python", "-m", "coverage", "html"])
        print("\n✅ Coverage report generated in htmlcov/index.html")
        return True
    else:
        print("\n❌ Coverage report generation failed")
        return False

def run_linting():
    """Run code linting"""
    print("\n" + "="*60)
    print("Running Code Linting")
    print("="*60)
    
    # Try to install flake8 if not available
    subprocess.run([sys.executable, "-m", "pip", "install", "flake8"], 
                  capture_output=True)
    
    cmd = "python -m flake8 --max-line-length=100 --ignore=E501,W503 main.py deploy/ tests/"
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print("\n✅ Linting passed")
        return True
    else:
        print("\n❌ Linting failed")
        return False

def run_all_tests(verbose=False, include_slow=False):
    """Run all test suites"""
    results = []
    
    print("\n" + "="*80)
    print("🧪 COMPREHENSIVE TEST SUITE - RKE2 INSTALLER")
    print("="*80)
    
    # Quick tests first
    results.append(("Quick Tests", run_quick_tests()))
    
    # Core test suites
    results.append(("Unit Tests", run_unit_tests(verbose)))
    results.append(("Integration Tests", run_integration_tests(verbose)))
    
    # Scenario tests
    results.append(("Scenario Tests", run_scenario_tests(verbose)))
    
    # Smoke tests
    results.append(("Smoke Tests", run_smoke_tests(verbose)))
    
    # Security tests
    results.append(("Security Tests", run_security_tests(verbose)))
    
    # Optional slow tests
    if include_slow:
        results.append(("E2E Tests", run_e2e_tests(verbose)))
        results.append(("Performance Tests", run_performance_tests(verbose)))
    
    # Code quality
    results.append(("Linting", run_linting()))
    results.append(("Coverage", run_coverage_report()))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status:<12} {test_name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📈 Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! The RKE2 installer is ready for deployment.")
        return True
    else:
        print(f"\n⚠️  {failed} test suite(s) failed. Please review and fix issues.")
        return False

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="RKE2 Installer Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--scenarios", action="store_true", help="Run scenario tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--security", action="store_true", help="Run security tests only")
    parser.add_argument("--smoke", action="store_true", help="Run smoke tests only")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--lint", action="store_true", help="Run linting only")
    parser.add_argument("--all", action="store_true", help="Run all test suites")
    parser.add_argument("--include-slow", action="store_true", help="Include slow tests (E2E, performance)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # If no specific test type is specified, run all
    if not any([args.unit, args.integration, args.e2e, args.scenarios, 
                args.performance, args.security, args.smoke, args.quick, 
                args.coverage, args.lint, args.all]):
        args.all = True
    
    success = True
    
    if args.quick:
        success = run_quick_tests()
    elif args.unit:
        success = run_unit_tests(args.verbose)
    elif args.integration:
        success = run_integration_tests(args.verbose)
    elif args.e2e:
        success = run_e2e_tests(args.verbose)
    elif args.scenarios:
        success = run_scenario_tests(args.verbose)
    elif args.performance:
        success = run_performance_tests(args.verbose)
    elif args.security:
        success = run_security_tests(args.verbose)
    elif args.smoke:
        success = run_smoke_tests(args.verbose)
    elif args.coverage:
        success = run_coverage_report()
    elif args.lint:
        success = run_linting()
    elif args.all:
        success = run_all_tests(args.verbose, args.include_slow)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
