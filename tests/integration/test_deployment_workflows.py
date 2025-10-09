import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import yaml

@pytest.mark.integration
class TestDeploymentWorkflows:
    """Integration tests for complete deployment workflows"""
    
    @pytest.fixture
    def full_cluster_config(self):
        """Full cluster configuration for integration testing"""
        return {
            'deployment': {
                'k8s_distribution': 'rke2',
                'os': {'type': 'rhel', 'version': '8'},
                'airgap': {
                    'enabled': True,
                    'local_registry': 'registry.internal.local:5000',
                    'bundle_staging_path': '/opt/k8s-bundles',
                    'image_staging_path': '/opt/container-images'
                },
                'rke2': {
                    'version': 'v1.32.3',
                    'airgap_bundle_path': '/opt/rke2-airgap-bundle.tar.gz',
                    'images_bundle_path': '/opt/k8s-bundles/rke2-images.tar.gz',
                    'install_script_path': '/opt/k8s-bundles/install.sh'
                }
            },
            'cluster': {
                'rke2': {
                    'name': 'production-cluster',
                    'domain': 'prod.local',
                    'token': 'secure-cluster-token',
                    'cluster_cidr': '10.42.0.0/16',
                    'service_cidr': '10.43.0.0/16',
                    'write_kubeconfig_mode': '0644'
                }
            },
            'nodes': {
                'servers': [
                    {
                        'hostname': 'k8s-master-1',
                        'ip': '10.0.1.10',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/prod_key',
                        'sudo_password': ''
                    },
                    {
                        'hostname': 'k8s-master-2',
                        'ip': '10.0.1.11',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/prod_key',
                        'sudo_password': ''
                    },
                    {
                        'hostname': 'k8s-master-3',
                        'ip': '10.0.1.12',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/prod_key',
                        'sudo_password': ''
                    }
                ],
                'agents': [
                    {
                        'hostname': 'k8s-worker-1',
                        'ip': '10.0.1.20',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/prod_key',
                        'gpu_enabled': False
                    },
                    {
                        'hostname': 'k8s-worker-2',
                        'ip': '10.0.1.21',
                        'user': 'k8s-admin',
                        'ssh_key': '.ssh/prod_key',
                        'gpu_enabled': True
                    }
                ]
            },
            'extra_tools': ['k9s', 'helm', 'flux']
        }
    
    @pytest.fixture
    def mock_deployment_components(self):
        """Mock all deployment components"""
        with patch('deploy.node.paramiko.SSHClient') as mock_ssh_class, \
             patch('deploy.node.setup_node') as mock_setup_node, \
             patch('deploy.node.install_gpu_stack') as mock_gpu_install, \
             patch('deploy.health.post_install_health_check') as mock_health_check, \
             patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
             patch('main.get_airgapped_os_handler') as mock_get_os, \
             patch('main.AirgapValidator') as mock_validator, \
             patch('main.stage_bundles_to_all_nodes') as mock_stage_bundles:
            
            # Setup successful mocks
            mock_setup_node.return_value = True
            mock_gpu_install.return_value = True
            mock_health_check.return_value = True
            
            mock_dist_handler = Mock()
            mock_dist_handler.validate_requirements.return_value = True
            mock_get_dist.return_value = mock_dist_handler
            
            mock_os_handler = Mock()
            mock_get_os.return_value = mock_os_handler
            
            mock_validator_instance = Mock()
            mock_validator_instance.run_full_validation.return_value = True
            mock_validator.return_value = mock_validator_instance
            
            mock_stage_bundles.return_value = True
            
            yield {
                'ssh_class': mock_ssh_class,
                'setup_node': mock_setup_node,
                'gpu_install': mock_gpu_install,
                'health_check': mock_health_check,
                'dist_handler': mock_dist_handler,
                'os_handler': mock_os_handler,
                'validator': mock_validator_instance,
                'stage_bundles': mock_stage_bundles
            }
    
    @patch('main.display_animated_logo')
    @patch('main.display_space_jam_logo4')
    @patch('main.log_success')
    def test_full_cluster_deployment_success(self, mock_log_success, mock_logo4, 
                                           mock_logo, full_cluster_config, 
                                           mock_deployment_components):
        """Test complete successful cluster deployment"""
        from click.testing import CliRunner
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(full_cluster_config, f)
            config_file = f.name
        
        try:
            # Mock all the imports to avoid import issues
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
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                
                # Verify deployment completed successfully
                assert result.exit_code == 0
                mock_log_success.assert_called()
                
                # Verify all nodes were processed
                setup_calls = mock_deployment_components['setup_node'].call_args_list
                assert len(setup_calls) == 5  # 3 servers + 2 agents
                
                # Verify GPU installation was called for GPU-enabled node
                mock_deployment_components['gpu_install'].assert_called()
                
                # Verify health checks were performed
                health_calls = mock_deployment_components['health_check'].call_args_list
                assert len(health_calls) == 3  # Only server nodes
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_error')
    def test_deployment_validation_failure(self, mock_log_error, mock_logo, 
                                         full_cluster_config, mock_deployment_components):
        """Test deployment failure during validation"""
        from click.testing import CliRunner
        
        # Make validation fail
        mock_deployment_components['validator'].run_full_validation.return_value = False
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(full_cluster_config, f)
            config_file = f.name
        
        try:
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
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                
                # Should not proceed with deployment
                mock_deployment_components['setup_node'].assert_not_called()
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_error')
    def test_deployment_node_setup_failure(self, mock_log_error, mock_logo, 
                                         full_cluster_config, mock_deployment_components):
        """Test deployment failure during node setup"""
        from click.testing import CliRunner
        
        # Make first server node setup fail
        mock_deployment_components['setup_node'].side_effect = [False, True, True, True, True]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(full_cluster_config, f)
            config_file = f.name
        
        try:
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
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                
                # Should stop deployment after first failure
                mock_log_error.assert_called()
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_success')
    def test_dry_run_deployment(self, mock_log_success, mock_logo, 
                              full_cluster_config, mock_deployment_components):
        """Test dry run deployment mode"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(full_cluster_config, f)
            config_file = f.name
        
        try:
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
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file, '--dry-run'])
                
                # Should not actually deploy anything
                mock_deployment_components['setup_node'].assert_not_called()
                mock_deployment_components['health_check'].assert_not_called()
                
                # Should show deployment plan
                assert "Deployment Plan:" in result.output
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_success')
    def test_stage_only_deployment(self, mock_log_success, mock_logo, 
                                 full_cluster_config, mock_deployment_components):
        """Test stage-only deployment mode"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(full_cluster_config, f)
            config_file = f.name
        
        try:
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
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file, '--stage-only'])
                
                # Should only stage bundles, not deploy
                mock_deployment_components['stage_bundles'].assert_called()
                mock_deployment_components['setup_node'].assert_not_called()
                
                assert "Bundle staging completed" in result.output
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.display_space_jam_logo4')
    @patch('main.log_success')
    def test_uninstall_workflow(self, mock_log_success, mock_logo4, mock_logo, 
                              full_cluster_config):
        """Test complete uninstall workflow"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(full_cluster_config, f)
            config_file = f.name
        
        try:
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
            }), \
            patch('main.uninstall_cluster') as mock_uninstall, \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist:
                
                mock_dist_handler = Mock()
                mock_get_dist.return_value = mock_dist_handler
                
                from main import cli
                
                runner = CliRunner()
                result = runner.invoke(cli, ['uninstall', '-c', config_file, '--force'])
                
                # Should call uninstall function
                mock_uninstall.assert_called_once()
                mock_log_success.assert_called()
        
        finally:
            os.unlink(config_file)

@pytest.mark.integration
class TestMultiDistributionWorkflows:
    """Integration tests for multi-distribution deployments"""
    
    @pytest.fixture
    def eks_anywhere_config(self):
        """EKS Anywhere configuration"""
        return {
            'deployment': {
                'k8s_distribution': 'eks-a',
                'os': {'type': 'ubuntu', 'version': '20.04'},
                'airgap': {'enabled': False},
                'eks_anywhere': {
                    'version': 'v0.18.0',
                    'cluster_config_path': '/opt/eks-a-cluster.yaml'
                }
            },
            'cluster': {
                'eks-a': {
                    'name': 'eks-anywhere-cluster',
                    'kubernetes_version': '1.28'
                }
            },
            'nodes': {
                'servers': [
                    {
                        'hostname': 'eks-control-1',
                        'ip': '10.0.2.10',
                        'user': 'ubuntu',
                        'ssh_key': '.ssh/eks_key'
                    }
                ],
                'agents': [
                    {
                        'hostname': 'eks-worker-1',
                        'ip': '10.0.2.20',
                        'user': 'ubuntu',
                        'ssh_key': '.ssh/eks_key'
                    }
                ]
            }
        }
    
    @patch('main.display_animated_logo')
    @patch('main.log_success')
    def test_eks_anywhere_deployment(self, mock_log_success, mock_logo, eks_anywhere_config):
        """Test EKS Anywhere deployment workflow"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(eks_anywhere_config, f)
            config_file = f.name
        
        try:
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
            }), \
            patch('main.get_distribution_handler') as mock_get_dist, \
            patch('main.get_os_handler') as mock_get_os, \
            patch('main.setup_node') as mock_setup_node, \
            patch('main.post_install_health_check') as mock_health:
                
                # Setup mocks for EKS Anywhere
                mock_dist_handler = Mock()
                mock_dist_handler.validate_requirements.return_value = True
                mock_get_dist.return_value = mock_dist_handler
                
                mock_os_handler = Mock()
                mock_get_os.return_value = mock_os_handler
                
                mock_setup_node.return_value = True
                mock_health.return_value = True
                
                from main import cli
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file, '--skip-validation'])
                
                # Verify EKS Anywhere specific handlers were used
                mock_get_dist.assert_called_with('eks-a')
                mock_get_os.assert_called_with('ubuntu')
        
        finally:
            os.unlink(config_file)

@pytest.mark.integration
class TestErrorRecoveryWorkflows:
    """Integration tests for error recovery scenarios"""
    
    @pytest.fixture
    def partial_failure_config(self, full_cluster_config):
        """Configuration for testing partial failures"""
        return full_cluster_config
    
    @patch('main.display_animated_logo')
    @patch('main.log_error')
    @patch('main.log_warning')
    def test_partial_deployment_failure_recovery(self, mock_log_warning, mock_log_error, 
                                               mock_logo, partial_failure_config):
        """Test recovery from partial deployment failures"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(partial_failure_config, f)
            config_file = f.name
        
        try:
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
            }), \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
            patch('main.get_airgapped_os_handler') as mock_get_os, \
            patch('main.setup_node') as mock_setup_node, \
            patch('main.post_install_health_check') as mock_health, \
            patch('main.AirgapValidator') as mock_validator:
                
                # Setup mocks
                mock_dist_handler = Mock()
                mock_dist_handler.validate_requirements.return_value = True
                mock_get_dist.return_value = mock_dist_handler
                
                mock_os_handler = Mock()
                mock_get_os.return_value = mock_os_handler
                
                mock_validator_instance = Mock()
                mock_validator_instance.run_full_validation.return_value = True
                mock_validator.return_value = mock_validator_instance
                
                # Simulate partial failure: first two servers succeed, third fails
                mock_setup_node.side_effect = [True, True, False, True, True]
                mock_health.return_value = False  # Health check fails
                
                from main import cli
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                
                # Should log error for failed node
                mock_log_error.assert_called()
                
                # Should still attempt to continue with remaining nodes
                # (depending on implementation)
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_warning')
    def test_gpu_installation_failure_handling(self, mock_log_warning, mock_logo, 
                                              partial_failure_config):
        """Test handling of GPU installation failures"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(partial_failure_config, f)
            config_file = f.name
        
        try:
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
            }), \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
            patch('main.get_airgapped_os_handler') as mock_get_os, \
            patch('main.setup_node') as mock_setup_node, \
            patch('main.install_gpu_stack') as mock_gpu_install, \
            patch('main.post_install_health_check') as mock_health, \
            patch('main.AirgapValidator') as mock_validator:
                
                # Setup successful deployment but GPU failure
                mock_dist_handler = Mock()
                mock_dist_handler.validate_requirements.return_value = True
                mock_get_dist.return_value = mock_dist_handler
                
                mock_os_handler = Mock()
                mock_get_os.return_value = mock_os_handler
                
                mock_validator_instance = Mock()
                mock_validator_instance.run_full_validation.return_value = True
                mock_validator.return_value = mock_validator_instance
                
                mock_setup_node.return_value = True
                mock_gpu_install.return_value = False  # GPU installation fails
                mock_health.return_value = True
                
                from main import cli
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                
                # Should warn about GPU failure but continue
                mock_log_warning.assert_called()
        
        finally:
            os.unlink(config_file)
