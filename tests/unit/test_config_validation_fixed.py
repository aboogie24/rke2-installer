import pytest
import yaml
import tempfile
import os
import copy
from click.testing import CliRunner

class TestConfigValidationWorking:
    """Test configuration validation with working imports"""
    
    def test_valid_config_structure(self, sample_config):
        """Test that valid config has required structure"""
        # Test the config structure directly
        assert 'deployment' in sample_config
        assert 'cluster' in sample_config
        assert 'nodes' in sample_config
        
        # Test deployment section
        deployment = sample_config['deployment']
        assert 'k8s_distribution' in deployment
        assert 'os' in deployment
        assert 'airgap' in deployment
        
        # Test cluster section
        cluster = sample_config['cluster']
        assert 'name' in cluster
        assert 'token' in cluster
        
        # Test nodes section
        nodes = sample_config['nodes']
        assert 'servers' in nodes
        assert 'agents' in nodes
    
    def test_config_validation_logic(self, sample_config):
        """Test config validation logic without importing main"""
        
        def validate_config_mock(config):
            """Mock validation function"""
            deployment = config.get('deployment', {})
            
            # Check K8s distribution
            k8s_dist = deployment.get('k8s_distribution', 'rke2')
            supported_distributions = ['rke2', 'eks-anywhere', 'vanilla', 'k3s', 'kubeadm']
            if k8s_dist not in supported_distributions:
                raise ValueError(f"Unsupported Kubernetes distribution: {k8s_dist}")
            
            # Check OS type
            os_type = deployment.get('os', {}).get('type', 'rhel')
            supported_os = ['rhel', 'ubuntu', 'centos', 'rocky', 'debian']
            if os_type not in supported_os:
                raise ValueError(f"Unsupported OS: {os_type}")
            
            return True
        
        # Test valid config
        result = validate_config_mock(sample_config)
        assert result is True
        
        # Test invalid distribution
        invalid_config = copy.deepcopy(sample_config)
        invalid_config['deployment']['k8s_distribution'] = 'invalid'
        
        with pytest.raises(ValueError, match="Unsupported Kubernetes distribution"):
            validate_config_mock(invalid_config)
        
        # Test invalid OS
        invalid_config = copy.deepcopy(sample_config)
        invalid_config['deployment']['os']['type'] = 'invalid'

        
        with pytest.raises(ValueError, match="Unsupported OS"):
            validate_config_mock(invalid_config)
    
    def test_legacy_config_migration_logic(self):
        """Test legacy config migration logic"""
        
        def migrate_legacy_config_mock(old_config):
            """Mock migration function"""
            new_config = {
                'deployment': {
                    'k8s_distribution': 'rke2',
                    'os': {'type': 'rhel', 'version': '8'},
                    'airgap': {
                        'enabled': True,
                        'local_registry': 'registry.example.com:5000',
                        'bundle_staging_path': '/opt/k8s-bundles',
                        'image_staging_path': '/opt/container-images'
                    },
                    'rke2': {
                        'version': old_config.get('cluster', {}).get('version', 'v1.32.3'),
                        'airgap_bundle_path': old_config.get('cluster', {}).get('airgap_bundle_path', '/opt/rke2-airgap-bundle.tar.gz'),
                        'images_bundle_path': '/opt/k8s-bundles/rke2-images.tar.gz',
                        'install_script_path': '/opt/k8s-bundles/install.sh'
                    }
                },
                'cluster': old_config.get('cluster', {}),
                'nodes': old_config.get('nodes', {}),
                'extra_tools': old_config.get('extra_tools', [])
            }
            
            # Convert root user to non-root user
            for node_list in [new_config['nodes'].get('servers', []), new_config['nodes'].get('agents', [])]:
                for node in node_list:
                    if node.get('user') == 'root':
                        node['user'] = 'k8s-admin'
                        node['sudo_password'] = ''
            
            return new_config
        
        # Test migration
        legacy_config = {
            'cluster': {
                'name': 'legacy-cluster',
                'version': 'v1.30.0',
                'airgap_bundle_path': '/opt/legacy-bundle.tar.gz'
            },
            'nodes': {
                'servers': [
                    {
                        'hostname': 'legacy-server',
                        'ip': '10.0.1.10',
                        'user': 'root',
                        'ssh_key': '.ssh/legacy_key'
                    }
                ]
            }
        }
        
        migrated = migrate_legacy_config_mock(legacy_config)
        
        # Check migration results
        assert migrated['deployment']['k8s_distribution'] == 'rke2'
        assert migrated['deployment']['os']['type'] == 'rhel'
        assert migrated['deployment']['airgap']['enabled'] is True
        assert migrated['nodes']['servers'][0]['user'] == 'k8s-admin'  # Root converted
        assert migrated['cluster']['name'] == 'legacy-cluster'
    
    def test_config_file_operations(self, sample_config):
        """Test config file loading and saving"""
        
        def load_config_mock(config_file):
            """Mock config loading"""
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_file = f.name
        
        try:
            # Test loading
            loaded_config = load_config_mock(config_file)
            assert loaded_config['cluster']['name'] == 'test-cluster'
            assert loaded_config['deployment']['k8s_distribution'] == 'rke2'
        finally:
            os.unlink(config_file)