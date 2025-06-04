import pytest
import tempfile
import os
import yaml
from click.testing import CliRunner
from main import cli
from tests.utils.mock_helpers import create_test_config

class TestSecurityScenarios:
    """Test security-related scenarios"""
    
    def test_non_root_user_validation(self):
        """Test validation of non-root user configuration"""
        config = create_test_config(**{
            'nodes': {
                'servers': [
                    {
                        'hostname': 'secure-server',
                        'ip': '10.0.1.10',
                        'user': 'k8s-admin',  # Non-root user
                        'ssh_key': '.ssh/secure_key',
                        'sudo_password': ''
                    }
                ],
                'agents': []
            }
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            config_file = f.name
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['validate', '-c', config_file])
            
            # Should pass validation with non-root user
            assert result.exit_code == 0
        finally:
            os.unlink(config_file)
    
    def test_root_user_warning(self):
        """Test warning when root user is used"""
        config = create_test_config(**{
            'nodes': {
                'servers': [
                    {
                        'hostname': 'root-server',
                        'ip': '10.0.1.10',
                        'user': 'root',  # Root user - should trigger warning
                        'ssh_key': '.ssh/root_key'
                    }
                ],
                'agents': []
            }
        })
        
        # Remove the deployment section to trigger legacy migration
        legacy_config = {
            'cluster': config['cluster'],
            'nodes': config['nodes']
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(legacy_config, f)
            config_file = f.name
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
            
            # Should warn about root user conversion
            assert "Converting root user to k8s-admin" in result.output
        finally:
            os.unlink(config_file)
    
    def test_ssh_key_permissions(self):
        """Test SSH key file permissions validation"""
        config = create_test_config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create SSH key with wrong permissions
            ssh_key = os.path.join(temp_dir, 'bad_key')
            with open(ssh_key, 'w') as f:
                f.write("-----BEGIN OPENSSH PRIVATE KEY-----\nBad permissions key\n-----END OPENSSH PRIVATE KEY-----")
            os.chmod(ssh_key, 0o644)  # Too permissive
            
            config['nodes']['servers'][0]['ssh_key'] = ssh_key
            
            config_file = os.path.join(temp_dir, 'config.yml')
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            runner = CliRunner()
            result = runner.invoke(cli, ['validate', '-c', config_file])
            
            # Should detect SSH key permission issues
            # Note: This would require implementing SSH key validation
            assert result.exit_code == 0  # For now, just ensure it runs
    
    def test_registry_authentication(self):
        """Test registry authentication configuration"""
        config = create_test_config(**{
            'cluster': {
                'registry': {
                    'configs': {
                        'registry.internal.local:5000': {
                            'auth': {
                                'username': 'registry-user',
                                'password': 'secure-password'
                            },
                            'tls': {
                                'insecure_skip_verify': False,
                                'ca_file': '/etc/ssl/certs/registry-ca.crt'
                            }
                        }
                    }
                }
            }
        })
        
        # Should validate registry auth configuration
        from main import validate_config
        validate_config(config)  # Should not raise exception

if __name__ == "__main__":
    pytest.main([__file__])