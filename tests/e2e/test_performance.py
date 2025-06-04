import pytest
import time
from unittest.mock import patch, Mock
from click.testing import CliRunner
from main import cli, stage_bundles_to_all_nodes

class TestPerformance:
    """Performance tests for deployment operations"""
    
    @pytest.mark.slow
    def test_config_loading_performance(self):
        """Test config loading performance with large configs"""
        from main import load_config
        
        # Create a large config with many nodes
        large_config = {
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
            'cluster': {'name': 'large-cluster'},
            'nodes': {
                'servers': [
                    {
                        'hostname': f'server-{i}',
                        'ip': f'10.0.1.{i}',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/key'
                    } for i in range(1, 11)  # 10 servers
                ],
                'agents': [
                    {
                        'hostname': f'agent-{i}',
                        'ip': f'10.0.2.{i}',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/key'
                    } for i in range(1, 101)  # 100 agents
                ]
            }
        }
        
        import tempfile
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(large_config, f)
            config_file = f.name
        
        try:
            start_time = time.time()
            config = load_config(config_file)
            load_time = time.time() - start_time
            
            # Should load large config quickly (< 1 second)
            assert load_time < 1.0
            assert len(config['nodes']['servers']) == 10
            assert len(config['nodes']['agents']) == 100
            
        finally:
            import os
            os.unlink(config_file)
    
    @patch('paramiko.SSHClient')
    def test_bundle_staging_parallel_simulation(self, mock_ssh_class):
        """Test bundle staging performance simulation"""
        mock_ssh = Mock()
        mock_ssh_class.return_value = mock_ssh
        mock_ssh.connect = Mock()
        mock_ssh.close = Mock()
        
        # Mock bundle manager
        with patch('deploy.airgap.bundle_manager.BundleManager') as mock_bundle_manager:
            mock_manager = Mock()
            mock_bundle_manager.return_value = mock_manager
            mock_manager.stage_bundles_to_node.return_value = True
            
            config = {
                'deployment': {'airgap': {'enabled': True}},
                'nodes': {
                    'servers': [{'hostname': f'server-{i}', 'ip': f'10.0.1.{i}', 
                               'user': 'test', 'ssh_key': 'key'} for i in range(5)],
                    'agents': [{'hostname': f'agent-{i}', 'ip': f'10.0.2.{i}', 
                              'user': 'test', 'ssh_key': 'key'} for i in range(10)]
                }
            }
            
            start_time = time.time()
            stage_bundles_to_all_nodes(config, Mock())
            staging_time = time.time() - start_time
            
            # Should complete staging simulation quickly
            assert staging_time < 5.0
            
            # Verify all nodes were processed
            expected_calls = len(config['nodes']['servers']) + len(config['nodes']['agents'])
            assert mock_manager.stage_bundles_to_node.call_count == expected_calls