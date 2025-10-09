#!/usr/bin/env python3
"""
Basic structure test for RKE2 installer project
Tests that don't require external dependencies
"""

import sys
import os
import importlib
from pathlib import Path

def test_project_structure():
    """Test that the project has the expected structure"""
    print("🧪 Testing Project Structure")
    print("-" * 40)
    
    project_root = Path(__file__).parent.parent
    
    # Check main files exist
    required_files = [
        'main.py',
        'README.md',
        'requirements.txt',
        'pytest.ini'
    ]
    
    for file in required_files:
        file_path = project_root / file
        if file_path.exists():
            print(f"✓ {file} exists")
        else:
            print(f"❌ {file} missing")
            return False
    
    # Check main directories exist
    required_dirs = [
        'deploy',
        'tests',
        'uninstall',
        'logo'
    ]
    
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"✓ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
            return False
    
    return True

def test_module_imports():
    """Test that main modules can be imported"""
    print("\n🧪 Testing Module Imports")
    print("-" * 40)
    
    modules_to_test = [
        'deploy',
        'uninstall',
        'logo'
    ]
    
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"✓ {module_name} module imports successfully")
        except ImportError as e:
            print(f"❌ {module_name} import failed: {e}")
            return False
    
    return True

def test_deploy_submodules():
    """Test that deploy submodules exist"""
    print("\n🧪 Testing Deploy Submodules")
    print("-" * 40)
    
    project_root = Path(__file__).parent.parent
    deploy_dir = project_root / 'deploy'
    
    expected_files = [
        '__init__.py',
        'config_generator.py',
        'health.py',
        'node.py',
        'utils.py'
    ]
    
    for file in expected_files:
        file_path = deploy_dir / file
        if file_path.exists():
            print(f"✓ deploy/{file} exists")
        else:
            print(f"❌ deploy/{file} missing")
            return False
    
    # Check subdirectories
    expected_subdirs = [
        'distributions',
        'os_handlers',
        'validation',
        'airgap'
    ]
    
    for subdir in expected_subdirs:
        subdir_path = deploy_dir / subdir
        if subdir_path.exists() and subdir_path.is_dir():
            print(f"✓ deploy/{subdir}/ directory exists")
        else:
            print(f"❌ deploy/{subdir}/ directory missing")
            return False
    
    return True

def test_test_structure():
    """Test that test structure is correct"""
    print("\n🧪 Testing Test Structure")
    print("-" * 40)
    
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / 'tests'
    
    expected_files = [
        '__init__.py',
        'conftest.py',
        'quick_tests.py',
        'test_runner.py',
        'README.md'
    ]
    
    for file in expected_files:
        file_path = tests_dir / file
        if file_path.exists():
            print(f"✓ tests/{file} exists")
        else:
            print(f"❌ tests/{file} missing")
            return False
    
    # Check test subdirectories
    expected_subdirs = [
        'unit',
        'integration',
        'e2e',
        'scenarios'
    ]
    
    for subdir in expected_subdirs:
        subdir_path = tests_dir / subdir
        if subdir_path.exists() and subdir_path.is_dir():
            print(f"✓ tests/{subdir}/ directory exists")
        else:
            print(f"❌ tests/{subdir}/ directory missing")
            return False
    
    return True

def test_main_module_structure():
    """Test main.py structure without importing it"""
    print("\n🧪 Testing Main Module Structure")
    print("-" * 40)
    
    project_root = Path(__file__).parent.parent
    main_file = project_root / 'main.py'
    
    try:
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Check for key functions/classes
        expected_elements = [
            'def load_config',
            'def validate_config',
            'def migrate_legacy_config',
            'def cli(',
            '@cli.command()',
            'SUPPORTED_DISTRIBUTIONS',
            'SUPPORTED_OS'
        ]
        
        for element in expected_elements:
            if element in content:
                print(f"✓ Found {element}")
            else:
                print(f"❌ Missing {element}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
        return False

def run_all_tests():
    """Run all basic structure tests"""
    print("🚀 RKE2 Installer - Basic Structure Tests")
    print("=" * 50)
    
    tests = [
        ("Project Structure", test_project_structure),
        ("Module Imports", test_module_imports),
        ("Deploy Submodules", test_deploy_submodules),
        ("Test Structure", test_test_structure),
        ("Main Module Structure", test_main_module_structure)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
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
        print("\n🎉 All basic structure tests passed!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
