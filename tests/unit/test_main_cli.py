import pytest
import tempfile
import os
import yaml
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
import sys
import importlib.util

class TestMainCLI:
    """Test main CLI functionality"""
    
    @pytest.fixture
    def runner(self):
        """CLI test runner"""
        return CliRunner()
    
    @pytest.fixture
    def mock_main_functions(self):
        """Mock main module functions to avoid import issues"""
        with patch('main.load_config') as mock_load, \
             patch('main.validate_config') as mock_validate, \
             patch('main.get_distribution_handler') as mock_get_dist, \
             patch('main.get_os_handler') as mock_get_os, \
             patch('main.setup_node') as mock_setup, \
             patch('main.post_install_health_check') as mock_health:
            
            mock_load.return_value = {
                'deployment': {
                    'k8s_distribution': 'rke2',
                    'os': {'type': 'rhel', 'version': '8'},
                    'airgap': {'enabled': True, 'local_registry': 'localhost:5000'}
                },
                'cluster': {'rke2': {'name': 'test-cluster'}},
                'nodes': {'servers': [], 'agents': []}
            }
            
            yield {
                'load_config': mock_load,
                'validate_config': mock_validate,
                'get_distribution_handler': mock_get_dist,
                'get_os_handler': mock_get_os,
                'setup_node': mock_setup,
                'post_install_health_check': mock_health
            }
    
    def test_load_config_valid_file(self, sample_config, temp_config_file):
        """Test loading valid configuration file"""
        # Import main functions directly to test logic
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        # Mock the dependencies that might cause import issues
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            spec.loader.exec_module(main_module)
            
            config = main_module.load_config(temp_config_file)
            assert config['cluster']['name'] == 'test-cluster'
            assert config['deployment']['k8s_distribution'] == 'rke2'
    
    def test_validate_config_valid(self, sample_config):
        """Test configuration validation with valid config"""
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            spec.loader.exec_module(main_module)
            
            # Should not raise any exceptions
            main_module.validate_config(sample_config)
    
    def test_validate_config_invalid_distribution(self, sample_config):
        """Test validation failure with invalid distribution"""
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            spec.loader.exec_module(main_module)
            
            sample_config['deployment']['k8s_distribution'] = 'invalid'
            
            with pytest.raises(Exception) as exc_info:
                main_module.validate_config(sample_config)
            assert "Unsupported Kubernetes distribution" in str(exc_info.value)
    
    def test_migrate_legacy_config(self):
        """Test legacy configuration migration"""
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            spec.loader.exec_module(main_module)
            
            legacy_config = {
                'cluster': {
                    'name': 'legacy-cluster',
                    'version': 'v1.30.0',
                    'registry': {
                        'mirrors': {
                            'registry.example.com': {
                                'endpoints': ['https://registry.example.com:5000']
                            }
                        }
                    }
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
            
            migrated = main_module.migrate_legacy_config(legacy_config)
            
            # Check migration results
            assert migrated['deployment']['k8s_distribution'] == 'rke2'
            assert migrated['deployment']['os']['type'] == 'rhel'
            assert migrated['deployment']['airgap']['enabled'] is True
            assert migrated['nodes']['servers'][0]['user'] == 'k8s-admin'  # Root converted
            assert migrated['cluster']['name'] == 'legacy-cluster'
    
    def test_get_cluster_config_success(self, sample_config):
        """Test successful cluster config retrieval"""
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            spec.loader.exec_module(main_module)
            
            # Add cluster config for rke2
            sample_config['cluster']['rke2'] = {'name': 'test-rke2-cluster'}
            
            cluster_config = main_module.get_cluster_config(sample_config)
            assert cluster_config['name'] == 'test-rke2-cluster'
    
    def test_get_cluster_config_missing(self, sample_config):
        """Test cluster config retrieval with missing config"""
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            spec.loader.exec_module(main_module)
            
            # Remove cluster config for rke2
            if 'rke2' in sample_config.get('cluster', {}):
                del sample_config['cluster']['rke2']
            
            with pytest.raises(ValueError) as exc_info:
                main_module.get_cluster_config(sample_config)
            assert "Missing cluster configuration" in str(exc_info.value)
    
    @patch('main.display_animated_logo')
    @patch('main.log_error')
    def test_cli_deploy_config_error(self, mock_log_error, mock_logo, runner, temp_config_file):
        """Test deploy command with configuration error"""
        # Create invalid config
        invalid_config = {'invalid': 'config'}
        with open(temp_config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            from main import cli
            result = runner.invoke(cli, ['deploy', '-c', temp_config_file])
            
            # Should handle the error gracefully
            assert result.exit_code == 0  # CLI doesn't exit with error code
            mock_log_error.assert_called()
    
    def test_supported_distributions_and_os(self):
        """Test supported distributions and OS constants"""
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        with patch.dict('sys.modules', {
            'deploy': Mock(),
            'deploy.config_generator': Mock(),
            'deploy.node': Mock(),
            'deploy.health': Mock(),
            'deploy.utils': Mock(),
            'deploy.distributions': Mock(),
            'deploy.os_handlers': Mock(),
            'deploy.validation.airgap_validator': Mock(),
            'logo.space_jam_logo': Mock(),
            'uninstall.uninstall_cluster': Mock()
        }):
            spec.loader.exec_module(main_module)
            
            # Check supported distributions
            expected_distributions = ['rke2', 'eks-a', 'vanilla', 'k3s', 'kubeadm']
            assert main_module.SUPPORTED_DISTRIBUTIONS == expected_distributions
            
            # Check supported OS
            expected_os = ['rhel', 'ubuntu', 'centos', 'rocky', 'debian']
            assert main_module.SUPPORTED_OS == expected_os
