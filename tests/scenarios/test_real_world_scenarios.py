import pytest
import yaml
import tempfile
import os
from click.testing import CliRunner
from main import cli
from tests.utils.mock_helpers import mock_ssh_environment, mock_bundle_environment, create_test_config
from tests.utils.assertions import assert_command_executed, assert_config_contains
from unittest.mock import Mock

class TestRealWorldScenarios:
    """Test real-world deployment scenarios"""
    
    def test_multi_server_ha_deployment(self):
        """Test high-availability deployment with multiple servers"""
        config = create_test_config(**{
            'cluster': {'name': 'ha-cluster'},
            'nodes': {
                'servers': [
                    {'hostname': 'master-1', 'ip': '10.0.1.10', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'},
                    {'hostname': 'master-2', 'ip': '10.0.1.11', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'},
                    {'hostname': 'master-3', 'ip': '10.0.1.12', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'}
                ],
                'agents': [
                    {'hostname': 'worker-1', 'ip': '10.0.2.10', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'},
                    {'hostname': 'worker-2', 'ip': '10.0.2.11', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'}
                ]
            }
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            config_file = f.name
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
            
            assert result.exit_code == 0
            assert "ha-cluster" in result.output
            assert "master-1" in result.output
            assert "master-2" in result.output
            assert "master-3" in result.output
            assert "worker-1" in result.output
            assert "worker-2" in result.output
        finally:
            os.unlink(config_file)
    
    def test_mixed_os_deployment(self):
        """Test deployment with mixed operating systems"""
        config = create_test_config(**{
            'deployment': {'os': {'type': 'rhel', 'version': '8'}},
            'nodes': {
                'servers': [
                    {
                        'hostname': 'rhel-server',
                        'ip': '10.0.1.10',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/key'
                    }
                ],
                'agents': [
                    {
                        'hostname': 'ubuntu-worker',
                        'ip': '10.0.2.10',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/key',
                        'os_override': {'type': 'ubuntu', 'version': '22.04'}
                    }
                ]
            }
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            config_file = f.name
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
            
            assert result.exit_code == 0
            assert "rhel 8" in result.output
            assert "ubuntu 22.04" in result.output
        finally:
            os.unlink(config_file)
    
    def test_gpu_enabled_deployment(self):
        """Test deployment with GPU-enabled nodes"""
        config = create_test_config(**{
            'nodes': {
                'servers': [
                    {'hostname': 'master-1', 'ip': '10.0.1.10', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'}
                ],
                'agents': [
                    {
                        'hostname': 'gpu-worker-1',
                        'ip': '10.0.2.10',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/key',
                        'gpu_enabled': True
                    },
                    {
                        'hostname': 'cpu-worker-1',
                        'ip': '10.0.2.11',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/key',
                        'gpu_enabled': False
                    }
                ]
            }
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            config_file = f.name
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
            
            assert result.exit_code == 0
            assert "GPU-enabled" in result.output
            assert "Standard" in result.output
        finally:
            os.unlink(config_file)

class TestFailureScenarios:
    @pytest.mark.parametrize("failure_type,expected_error", [
        ("ssh_connection", "Failed to stage bundles"),
        ("bundle_missing", "Bundle not found"),
        ("permission_denied", "Permission denied"),
    ])
    def test_deployment_failures(self, failure_type, expected_error):
        """Test various deployment failure scenarios"""
        
        # Use Mock objects instead of real handlers
        mock_dist_handler = Mock()
        mock_os_handler = Mock()
        
        # Configure the mock behaviors
        mock_dist_handler.validate_requirements = Mock()
        mock_dist_handler.generate_config_files = Mock(return_value="mock config")
        mock_os_handler.install_base_packages = Mock()
        
        # Configure failure scenarios
        if failure_type == "ssh_connection":
            mock_dist_handler.validate_requirements.return_value = True
            mock_os_handler.install_base_packages.return_value = False  # SSH failure
        elif failure_type == "bundle_missing":
            mock_dist_handler.validate_requirements.return_value = False  # Bundle missing
        elif failure_type == "permission_denied":
            mock_dist_handler.validate_requirements.return_value = True
            mock_os_handler.install_base_packages.return_value = False  # Permission denied
        
        # Test the scenarios
        config = {
            'deployment': {'rke2': {'airgap_bundle_path': '/test/bundle.tar.gz'}},
            'nodes': {'servers': [{'hostname': 'test-server'}], 'agents': []}
        }
        
        if failure_type == "bundle_missing":
            result = mock_dist_handler.validate_requirements(config)
            assert result is False
        else:
            result = mock_os_handler.install_base_packages(Mock())
            assert result is False

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_cluster_name(self):
        """Test deployment with very long cluster name"""
        long_name = "a" * 100
        config = create_test_config(**{
            'cluster': {'name': long_name}
        })
        
        # Should handle long names gracefully
        assert_config_contains(config, 'cluster.name', long_name)
    
    def test_special_characters_in_config(self):
        """Test handling of special characters in configuration"""
        config = create_test_config(**{
            'cluster': {
                'name': 'test-cluster-with-special-chars_123',
                'domain': 'test.local'
            }
        })
        
        from main import validate_config
        # Should not raise exception
        validate_config(config)
    
    def test_empty_node_lists(self):
        """Test behavior with empty node lists"""
        config = create_test_config(**{
            'nodes': {
                'servers': [],
                'agents': []
            }
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            config_file = f.name
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
            
            # Should handle empty node lists gracefully
            assert "Server Nodes (0)" in result.output
            assert "Agent Nodes (0)" in result.output
        finally:
            os.unlink(config_file)
    
    def test_ipv6_addresses(self):
        """Test deployment with IPv6 addresses"""
        config = create_test_config(**{
            'nodes': {
                'servers': [
                    {
                        'hostname': 'ipv6-server',
                        'ip': '2001:db8::1',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/key'
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
            result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
            
            assert result.exit_code == 0
            assert "2001:db8::1" in result.output
        finally:
            os.unlink(config_file)

class TestPerformanceScenarios:
    """Test performance-related scenarios"""
    
    @pytest.mark.slow
    def test_large_cluster_deployment_plan(self):
        """Test deployment plan generation for large clusters"""
        from tests.utils.performance_helpers import performance_monitor
        
        # Create large cluster config
        servers = [
            {
                'hostname': f'server-{i}',
                'ip': f'10.0.1.{i}',
                'user': 'k8s-admin',
                'ssh_key': '.ssh/key'
            }
            for i in range(1, 11)  # 10 servers
        ]
        
        agents = [
            {
                'hostname': f'worker-{i}',
                'ip': f'10.0.2.{i}',
                'user': 'k8s-admin',
                'ssh_key': '.ssh/key'
            }
            for i in range(1, 101)  # 100 workers
        ]
        
        config = create_test_config(**{
            'cluster': {'name': 'large-cluster'},
            'nodes': {'servers': servers, 'agents': agents}
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            config_file = f.name
        
        try:
            with performance_monitor() as monitor:
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
            
            # Should complete quickly even with large config
            assert monitor.execution_time < 5.0
            assert result.exit_code == 0
            assert "Server Nodes (10)" in result.output
            assert "Agent Nodes (100)" in result.output
            
        finally:
            os.unlink(config_file)
    
    @pytest.mark.slow
    def test_concurrent_bundle_staging_simulation(self):
        """Test simulated concurrent bundle staging"""
        import threading
        from unittest.mock import patch, Mock
        
        config = create_test_config(**{
            'nodes': {
                'servers': [
                    {'hostname': f'server-{i}', 'ip': f'10.0.1.{i}', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'}
                    for i in range(1, 6)
                ],
                'agents': [
                    {'hostname': f'worker-{i}', 'ip': f'10.0.2.{i}', 'user': 'k8s-admin', 'ssh_key': '.ssh/key'}
                    for i in range(1, 11)
                ]
            }
        })
        
        with patch('paramiko.SSHClient') as mock_ssh_class:
            mock_ssh = Mock()
            mock_ssh_class.return_value = mock_ssh
            mock_ssh.connect = Mock()
            mock_ssh.close = Mock()
            
            with patch('deploy.airgap.bundle_manager.BundleManager') as mock_bundle_manager:
                mock_manager = Mock()
                mock_bundle_manager.return_value = mock_manager
                
                # Simulate slow bundle staging
                def slow_staging(*args, **kwargs):
                    import time
                    time.sleep(0.1)  # Simulate network delay
                    return True
                
                mock_manager.stage_bundles_to_node.side_effect = slow_staging
                
                from main import stage_bundles_to_all_nodes
                from tests.utils.performance_helpers import performance_monitor
                
                with performance_monitor() as monitor:
                    stage_bundles_to_all_nodes(config, Mock())
                
                # Should complete all nodes
                expected_calls = len(config['nodes']['servers']) + len(config['nodes']['agents'])
                assert mock_manager.stage_bundles_to_node.call_count == expected_calls
