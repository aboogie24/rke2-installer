import pytest
from main import validate_config, load_config, migrate_legacy_config
import yaml
import tempfile
import os
from click.testing import CliRunner

class TestConfigValidation:
    """Test configuration validation logic"""
    
    def test_valid_config(self, sample_config):
        """Test that valid config passes validation"""
        # Should not raise any exceptions
        validate_config(sample_config)
    
    def test_invalid_distribution(self, sample_config):
        """Test that invalid distribution raises exception"""
        sample_config['deployment']['k8s_distribution'] = 'invalid'
        
        with pytest.raises(Exception) as exc_info:
            validate_config(sample_config)
        assert "Unsupported Kubernetes distribution" in str(exc_info.value)
    
    def test_invalid_os(self, sample_config):
        """Test that invalid OS raises exception"""
        sample_config['deployment']['os']['type'] = 'invalid'
        
        with pytest.raises(Exception) as exc_info:
            validate_config(sample_config)
        assert "Unsupported OS" in str(exc_info.value)
    
    def test_missing_rke2_config(self, sample_config):
        """Test that missing RKE2 config raises exception"""
        del sample_config['deployment']['rke2']
        
        with pytest.raises(Exception) as exc_info:
            validate_config(sample_config)
        assert "RKE2 configuration section missing" in str(exc_info.value)
    
    def test_load_config_file(self, temp_config_file):
        """Test loading config from file"""
        config = load_config(temp_config_file)
        assert config['cluster']['name'] == 'test-cluster'
        assert config['deployment']['k8s_distribution'] == 'rke2'
    
    def test_legacy_config_migration(self):
        """Test migration of legacy RKE2 config"""
        legacy_config = {
            'cluster': {
                'name': 'legacy-cluster',
                'version': 'v1.30.0',
                'airgap_bundle_path': '/opt/legacy-bundle.tar.gz',
                'registry': {
                    'mirrors': {
                        'registry.example.com': {
                            'endpoints': ['https://registry.example.com']
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
        
        migrated = migrate_legacy_config(legacy_config)
        
        # Check migration results
        assert migrated['deployment']['k8s_distribution'] == 'rke2'
        assert migrated['deployment']['os']['type'] == 'rhel'
        assert migrated['deployment']['airgap']['enabled'] is True
        assert migrated['nodes']['servers'][0]['user'] == 'k8s-admin'  # Root converted
        assert migrated['cluster']['name'] == 'legacy-cluster'