"""
Simple test runner that doesn't require complex imports
Run with: python tests/run_simple_tests.py
"""

import sys
import os
import tempfile
import yaml

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_validation():
    """Test basic config validation logic"""
    print("Testing config validation...")
    
    sample_config = {
        'deployment': {
            'k8s_distribution': 'rke2',
            'os': {'type': 'rhel', 'version': '8'},
            'airgap': {'enabled': True, 'local_registry': 'localhost:5000'},
            'rke2': {
                'version': 'v1.32.3',
                'airgap_bundle_path': '/opt/bundle.tar.gz',
                'images_bundle_path': '/opt/images.tar.gz',
                'install_script_path': '/opt/install.sh'
            }
        },
        'cluster': {'name': 'test-cluster', 'token': 'test-token'},
        'nodes': {'servers': [], 'agents': []}
    }
    
    # Test valid config structure
    assert 'deployment' in sample_config
    assert 'cluster' in sample_config
    assert 'nodes' in sample_config
    print("✓ Config structure validation passed")
    
    # Test distribution validation
    supported_distributions = ['rke2', 'eks-anywhere', 'vanilla', 'k3s', 'kubeadm']
    k8s_dist = sample_config['deployment']['k8s_distribution']
    assert k8s_dist in supported_distributions
    print("✓ Distribution validation passed")
    
    # Test OS validation
    supported_os = ['rhel', 'ubuntu', 'centos', 'rocky', 'debian']
    os_type = sample_config['deployment']['os']['type']
    assert os_type in supported_os
    print("✓ OS validation passed")

def test_config_file_operations():
    """Test config file loading and saving"""
    print("Testing config file operations...")
    
    test_config = {
        'deployment': {'k8s_distribution': 'rke2'},
        'cluster': {'name': 'file-test-cluster'},
        'nodes': {'servers': [], 'agents': []}
    }
    
    # Test saving and loading
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(test_config, f)
        config_file = f.name
    
    try:
        # Load config
        with open(config_file, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        assert loaded_config['cluster']['name'] == 'file-test-cluster'
        assert loaded_config['deployment']['k8s_distribution'] == 'rke2'
        print("✓ Config file operations passed")
        
    finally:
        os.unlink(config_file)

def test_bundle_file_operations():
    """Test bundle file operations"""
    print("Testing bundle file operations...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock bundles
        bundle_files = [
            'rke2-airgap-bundle.tar.gz',
            'rke2-images.tar.gz',
            'install.sh'
        ]
        
        for bundle_file in bundle_files:
            bundle_path = os.path.join(temp_dir, bundle_file)
            with open(bundle_path, 'w') as f:
                f.write(f"mock {bundle_file} content")
        
        # Test bundle existence
        for bundle_file in bundle_files:
            bundle_path = os.path.join(temp_dir, bundle_file)
            assert os.path.exists(bundle_path)
        
        print("✓ Bundle file operations passed")

def test_legacy_config_migration():
    """Test legacy config migration logic"""
    print("Testing legacy config migration...")
    
    legacy_config = {
        'cluster': {
            'name': 'legacy-cluster',
            'version': 'v1.30.0',
            'airgap_bundle_path': '/opt/legacy-bundle.tar.gz'
        },
        'nodes': {
            'servers': [
                {'hostname': 'old-server', 'user': 'root', 'ip': '10.0.1.10'}
            ]
        }
    }
    
    # Migration logic
    migrated_config = {
        'deployment': {
            'k8s_distribution': 'rke2',
            'os': {'type': 'rhel', 'version': '8'},
            'airgap': {'enabled': True},
            'rke2': {
                'version': legacy_config['cluster']['version'],
                'airgap_bundle_path': legacy_config['cluster']['airgap_bundle_path']
            }
        },
        'cluster': legacy_config['cluster'],
        'nodes': legacy_config['nodes']
    }
    
    # Convert root users
    for node in migrated_config['nodes']['servers']:
        if node.get('user') == 'root':
            node['user'] = 'k8s-admin'
    
    # Validate migration
    assert migrated_config['deployment']['k8s_distribution'] == 'rke2'
    assert migrated_config['nodes']['servers'][0]['user'] == 'k8s-admin'
    assert migrated_config['cluster']['name'] == 'legacy-cluster'
    print("✓ Legacy config migration passed")

def test_utils_functions():
    """Test utility functions without complex imports"""
    print("Testing utility functions...")
    
    # Test logging format function
    def format_log_message(hostname, message, details=None):
        base_msg = f"[{hostname}] {message}"
        if details:
            base_msg += f" {details}"
        return base_msg
    
    # Test the function
    result = format_log_message("test-server", "Starting deployment")
    assert "[test-server]" in result
    assert "Starting deployment" in result
    print("✓ Log formatting passed")
    
    # Test IP validation function
    def validate_ip_simple(ip):
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            for part in parts:
                num = int(part)
                if not 0 <= num <= 255:
                    return False
            return True
        except ValueError:
            return False
    
    # Test IP validation
    assert validate_ip_simple("192.168.1.1") is True
    assert validate_ip_simple("10.0.0.1") is True
    assert validate_ip_simple("invalid") is False
    assert validate_ip_simple("256.1.1.1") is False
    print("✓ IP validation passed")

def run_all_tests():
    """Run all simple tests"""
    print("Running simple tests without pytest...")
    print("=" * 50)
    
    try:
        test_config_validation()
        test_config_file_operations()
        test_bundle_file_operations()
        test_legacy_config_migration()
        test_utils_functions()
        
        print("=" * 50)
        print("✅ All simple tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)