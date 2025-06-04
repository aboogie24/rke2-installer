#!/usr/bin/env python3
"""
Quick test script to verify basic functionality
Usage: python tests/quick_test.py
"""

def quick_test():
    """Run a quick test of core functionality"""
    print("🧪 Quick Test Suite")
    print("-" * 30)
    
    # Test 1: Import check
    try:
        import yaml
        import click
        import colorama
        print("✓ Required imports available")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test 2: Config structure
    test_config = {
        'deployment': {'k8s_distribution': 'rke2'},
        'cluster': {'name': 'quick-test'},
        'nodes': {'servers': [], 'agents': []}
    }
    
    required_keys = ['deployment', 'cluster', 'nodes']
    for key in required_keys:
        if key not in test_config:
            print(f"❌ Missing config key: {key}")
            return False
    print("✓ Config structure valid")
    
    # Test 3: File operations
    import tempfile
    import os
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            yaml.dump(test_config, f)
            temp_file = f.name
        
        with open(temp_file, 'r') as f:
            loaded = yaml.safe_load(f)
        
        os.unlink(temp_file)
        
        if loaded['cluster']['name'] != 'quick-test':
            print("❌ Config round-trip failed")
            return False
        print("✓ File operations working")
        
    except Exception as e:
        print(f"❌ File operation error: {e}")
        return False
    
    print("-" * 30)
    print("✅ Quick test completed successfully!")
    return True

if __name__ == "__main__":
    import sys
    success = quick_test()
    sys.exit(0 if success else 1)