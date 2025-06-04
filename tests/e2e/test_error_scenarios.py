import pytest
from click.testing import CliRunner
from main import cli
import yaml
import tempfile

class TestErrorScenarios:
    """Test error handling and edge cases"""
    
    def test_missing_config_file(self):
        """Test behavior with missing config file"""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['deploy'])
        
        print(result.exit_code)
        assert result.exit_code != 0
    
    def test_invalid_config_file_path_isolated(self):
        """Test with isolated filesystem to guarantee file doesn't exist"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # We're in a clean temporary directory
            result = runner.invoke(cli, ['deploy', '-c', 'nonexistent.yaml'])
            
            assert "No such file" in result.output or "Configuration error" in result.output
    
    def test_invalid_yaml_config(self):
        """Test behavior with invalid YAML"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            with open('invalid.yml', 'w') as f:
                f.write("invalid: yaml: content: [unclosed")
            
            result = runner.invoke(cli, ['deploy', '-c', 'invalid.yml'])
            
            assert "Configuration error" in result.output
    
    def test_unsupported_distribution(self):
        """Test behavior with unsupported distribution"""
        runner = CliRunner()
        
        config = {
            'deployment': {
                'k8s_distribution': 'unsupported-distro',
                'os': {'type': 'rhel', 'version': '8'}
            },
            'cluster': {'name': 'test'},
            'nodes': {'servers': [], 'agents': []}
        }
        
        with runner.isolated_filesystem():
            with open('bad-config.yml', 'w') as f:
                yaml.dump(config, f)
            
            result = runner.invoke(cli, ['deploy', '-c', 'bad-config.yml'])
            
            
            assert "Unsupported Kubernetes distribution" in result.output
    
    def test_missing_required_bundles(self):
        """Test validation with missing required bundles"""
        runner = CliRunner()
        
        config = {
            'deployment': {
                'k8s_distribution': 'rke2',
                'os': {'type': 'rhel', 'version': '8'},
                'airgap': {'enabled': True, 'local_registry': 'localhost:5000'},
                'rke2': {
                    'version': 'v1.32.3',
                    'airgap_bundle_path': '/nonexistent/bundle.tar.gz',
                    'images_bundle_path': '/nonexistent/images.tar.gz',
                    'install_script_path': '/nonexistent/install.sh'
                }
            },
            'cluster': {'name': 'test'},
            'nodes': {'servers': [], 'agents': []}
        }
        
        with runner.isolated_filesystem():
            with open('missing-bundles.yml', 'w') as f:
                yaml.dump(config, f)
            
            result = runner.invoke(cli, ['validate', '-c', 'missing-bundles.yml'])
            
            # Should fail validation due to missing bundles
            assert "Missing required bundles" in result.output or "Bundle not found" in result.output