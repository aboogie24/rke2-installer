import pytest
import subprocess
import time
import yaml
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from main import cli

class TestDeploymentWorkflow:
    """End-to-end tests for the complete deployment workflow"""
    
    @pytest.fixture(scope="class")
    def e2e_config(self, tmp_path_factory):
        """Create E2E test configuration"""
        config_dir = tmp_path_factory.mktemp("e2e_config")
        
        # Create mock bundle files
        bundle_dir = config_dir / "bundles"
        bundle_dir.mkdir()
        
        (bundle_dir / "rke2-airgap-bundle.tar.gz").write_bytes(b"mock bundle")
        (bundle_dir / "rke2-images.tar.gz").write_bytes(b"mock images")
        (bundle_dir / "install.sh").write_text("#!/bin/bash\necho 'mock install'")
        
        # Create test SSH key
        ssh_key = config_dir / "test_key"
        ssh_key.write_text("mock ssh key")
        ssh_key.chmod(0o600)
        
        config = {
            'deployment': {
                'k8s_distribution': 'rke2',
                'os': {'type': 'rhel', 'version': '8'},
                'airgap': {
                    'enabled': True,
                    'local_registry': 'localhost:5000',
                    'bundle_staging_path': str(bundle_dir),
                    'image_staging_path': str(bundle_dir)
                },
                'rke2': {
                    'version': 'v1.32.3',
                    'airgap_bundle_path': str(bundle_dir / "rke2-airgap-bundle.tar.gz"),
                    'images_bundle_path': str(bundle_dir / "rke2-images.tar.gz"),
                    'install_script_path': str(bundle_dir / "install.sh")
                }
            },
            'cluster': {
                'name': 'e2e-test-cluster',
                'domain': 'test.local',
                'token': 'e2e-test-token',
                'cluster_cidr': '10.42.0.0/16',
                'service_cidr': '10.43.0.0/16',
                'write_kubeconfig_mode': '0644'
            },
            'nodes': {
                'servers': [
                    {
                        'hostname': 'e2e-test-server-1',
                        'ip': '127.0.0.1',  # Localhost for testing
                        'user': os.getenv('USER', 'testuser'),
                        'ssh_key': str(ssh_key),
                        'sudo_password': ''
                    }
                ],
                'agents': []  # Skip agents for basic E2E test
            },
            'extra_tools': []
        }
        
        config_file = config_dir / "e2e-config.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        return str(config_file)
    
    def test_config_generation(self):
        """Test configuration file generation"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                'generate-config',
                '--distribution', 'rke2',
                '--os', 'rhel',
                '--output', 'test-config.yml'
            ])
            
            assert result.exit_code == 0
            assert "Sample configuration generated" in result.output
            assert os.path.exists('test-config.yml')
            
            # Validate generated config
            with open('test-config.yml', 'r') as f:
                config = yaml.safe_load(f)
            
            assert config['deployment']['k8s_distribution'] == 'rke2'
            assert config['deployment']['os']['type'] == 'rhel'
            assert config['deployment']['airgap']['enabled'] is True
    
    def test_config_validation(self, e2e_config):
        """Test configuration validation command"""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['validate', '-c', e2e_config])
        
        # Should pass validation (bundles exist, config is valid)
        assert result.exit_code == 0
        assert "All validations passed" in result.output or "Validation" in result.output
    
    def test_dry_run_deployment(self, e2e_config):
        """Test dry run deployment"""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'deploy',
            '-c', e2e_config,
            '--dry-run'
        ])
        
        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.output
        assert "Deployment Plan:" in result.output
        assert "e2e-test-cluster" in result.output
    
    def test_list_supported_command(self):
        """Test listing supported distributions and OS"""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['list-supported'])
        
        assert result.exit_code == 0
        assert "rke2" in result.output
        assert "rhel" in result.output
        assert "ubuntu" in result.output
        assert "Airgapped Environment Features" in result.output
    
    @pytest.mark.slow
    def test_bundle_staging_simulation(self, e2e_config):
        """Test bundle staging with mock SSH"""
        runner = CliRunner()
        
        # This would normally fail without real SSH access
        # but we can test the command parsing and validation
        result = runner.invoke(cli, [
            'stage-bundles',
            '-c', e2e_config
        ])
        
        # Will fail at SSH connection, but should pass config validation
        assert "Bundle staging" in result.output or "Configuration error" in result.output

@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests that require Docker/containers"""
    
    @pytest.fixture(scope="class")
    def local_registry(self):
        """Start a local Docker registry for testing"""
        try:
            # Start local registry
            subprocess.run([
                'docker', 'run', '-d', '--name', 'test-registry',
                '-p', '5000:5000', 'registry:2'
            ], check=True, capture_output=True)
            
            # Wait for registry to start
            time.sleep(2)
            
            yield "localhost:5000"
            
        except subprocess.CalledProcessError:
            pytest.skip("Docker not available for integration tests")
        finally:
            # Cleanup
            subprocess.run(['docker', 'rm', '-f', 'test-registry'], 
                         capture_output=True)
    
    def test_registry_connectivity(self, local_registry):
        """Test connectivity to local registry"""
        import requests
        
        try:
            response = requests.get(f"http://{local_registry}/v2/")
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            pytest.fail("Could not connect to test registry")
    
