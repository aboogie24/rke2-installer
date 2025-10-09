import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import yaml
import time

@pytest.mark.e2e
@pytest.mark.slow
class TestFullDeploymentScenarios:
    """End-to-end tests for complete deployment scenarios"""
    
    @pytest.fixture
    def production_cluster_config(self):
        """Production-like cluster configuration"""
        return {
            'deployment': {
                'k8s_distribution': 'rke2',
                'os': {'type': 'rhel', 'version': '8'},
                'airgap': {
                    'enabled': True,
                    'local_registry': 'harbor.internal.company.com:443',
                    'bundle_staging_path': '/opt/kubernetes/bundles',
                    'image_staging_path': '/opt/kubernetes/images'
                },
                'rke2': {
                    'version': 'v1.32.3',
                    'airgap_bundle_path': '/opt/kubernetes/bundles/rke2-airgap-bundle.tar.gz',
                    'images_bundle_path': '/opt/kubernetes/bundles/rke2-images.tar.gz',
                    'install_script_path': '/opt/kubernetes/bundles/install.sh'
                }
            },
            'cluster': {
                'rke2': {
                    'name': 'production-k8s-cluster',
                    'domain': 'k8s.company.com',
                    'token': 'K10a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6',
                    'cluster_cidr': '10.42.0.0/16',
                    'service_cidr': '10.43.0.0/16',
                    'write_kubeconfig_mode': '0644',
                    'disable': ['traefik'],  # Disable default ingress
                    'node_taint': {
                        'CriticalAddonsOnly': 'true:NoExecute'
                    }
                }
            },
            'nodes': {
                'servers': [
                    {
                        'hostname': 'k8s-control-01.company.com',
                        'ip': '10.10.10.11',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/k8s_rsa',
                        'sudo_password': '',
                        'roles': ['control-plane', 'etcd']
                    },
                    {
                        'hostname': 'k8s-control-02.company.com',
                        'ip': '10.10.10.12',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/k8s_rsa',
                        'sudo_password': '',
                        'roles': ['control-plane', 'etcd']
                    },
                    {
                        'hostname': 'k8s-control-03.company.com',
                        'ip': '10.10.10.13',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/k8s_rsa',
                        'sudo_password': '',
                        'roles': ['control-plane', 'etcd']
                    }
                ],
                'agents': [
                    {
                        'hostname': 'k8s-worker-01.company.com',
                        'ip': '10.10.10.21',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/k8s_rsa',
                        'gpu_enabled': False,
                        'labels': {
                            'node-type': 'compute',
                            'workload': 'general'
                        }
                    },
                    {
                        'hostname': 'k8s-worker-02.company.com',
                        'ip': '10.10.10.22',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/k8s_rsa',
                        'gpu_enabled': False,
                        'labels': {
                            'node-type': 'compute',
                            'workload': 'general'
                        }
                    },
                    {
                        'hostname': 'k8s-gpu-01.company.com',
                        'ip': '10.10.10.31',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/k8s_rsa',
                        'gpu_enabled': True,
                        'labels': {
                            'node-type': 'gpu',
                            'workload': 'ml',
                            'gpu-type': 'nvidia-a100'
                        }
                    },
                    {
                        'hostname': 'k8s-gpu-02.company.com',
                        'ip': '10.10.10.32',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/k8s_rsa',
                        'gpu_enabled': True,
                        'labels': {
                            'node-type': 'gpu',
                            'workload': 'ml',
                            'gpu-type': 'nvidia-a100'
                        }
                    }
                ]
            },
            'extra_tools': ['k9s', 'helm', 'flux'],
            'packages': {
                'rhel': {
                    'base_packages': [
                        'curl', 'wget', 'tar', 'unzip', 'git',
                        'container-selinux', 'iptables', 'socat'
                    ],
                    'gpu_packages': [
                        'nvidia-driver', 'nvidia-container-toolkit',
                        'nvidia-docker2'
                    ]
                }
            }
        }
    
    @pytest.fixture
    def mock_production_environment(self):
        """Mock production environment components"""
        with patch('deploy.node.paramiko.SSHClient') as mock_ssh_class, \
             patch('deploy.validation.airgap_validator.AirgapValidator') as mock_validator, \
             patch('deploy.airgap.bundle_manager.BundleManager') as mock_bundle_mgr, \
             patch('deploy.distributions.airgapped_rke2_handler.AirgappedRKE2Handler') as mock_rke2, \
             patch('deploy.os_handlers.airgapped_rhel_handler.AirgappedRHELHandler') as mock_rhel:
            
            # Setup SSH client mock
            mock_ssh = Mock()
            mock_ssh.connect.return_value = None
            mock_ssh.exec_command.return_value = (Mock(), Mock(), Mock())
            mock_ssh.close.return_value = None
            mock_ssh_class.return_value = mock_ssh
            
            # Setup validator mock
            mock_validator_instance = Mock()
            mock_validator_instance.run_full_validation.return_value = True
            mock_validator_instance.validate_bundle_files.return_value = True
            mock_validator_instance.validate_network_connectivity.return_value = True
            mock_validator_instance.validate_ssh_access.return_value = True
            mock_validator.return_value = mock_validator_instance
            
            # Setup bundle manager mock
            mock_bundle_instance = Mock()
            mock_bundle_instance.stage_bundles_to_node.return_value = True
            mock_bundle_instance.verify_bundle_integrity.return_value = True
            mock_bundle_mgr.return_value = mock_bundle_instance
            
            # Setup RKE2 handler mock
            mock_rke2_instance = Mock()
            mock_rke2_instance.validate_requirements.return_value = True
            mock_rke2_instance.prepare_server_node.return_value = True
            mock_rke2_instance.prepare_agent_node.return_value = True
            mock_rke2_instance.install_distribution.return_value = True
            mock_rke2_instance.start_services.return_value = True
            mock_rke2.return_value = mock_rke2_instance
            
            # Setup RHEL handler mock
            mock_rhel_instance = Mock()
            mock_rhel_instance.install_base_packages.return_value = True
            mock_rhel_instance.disable_swap.return_value = True
            mock_rhel_instance.configure_kernel_modules.return_value = True
            mock_rhel_instance.configure_selinux.return_value = True
            mock_rhel_instance.configure_firewall.return_value = True
            mock_rhel_instance.install_gpu_packages.return_value = True
            mock_rhel.return_value = mock_rhel_instance
            
            yield {
                'ssh': mock_ssh,
                'validator': mock_validator_instance,
                'bundle_manager': mock_bundle_instance,
                'rke2_handler': mock_rke2_instance,
                'rhel_handler': mock_rhel_instance
            }
    
    @patch('main.display_animated_logo')
    @patch('main.display_space_jam_logo4')
    @patch('main.log_success')
    def test_production_cluster_full_deployment(self, mock_log_success, mock_logo4, 
                                              mock_logo, production_cluster_config, 
                                              mock_production_environment):
        """Test complete production cluster deployment end-to-end"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(production_cluster_config, f)
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
                'deploy.airgap.bundle_manager': Mock(),
                'logo.space_jam_logo': Mock(),
                'uninstall.uninstall_cluster': Mock()
            }), \
            patch('main.setup_node') as mock_setup_node, \
            patch('main.install_gpu_stack') as mock_gpu_install, \
            patch('main.post_install_health_check') as mock_health_check, \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
            patch('main.get_airgapped_os_handler') as mock_get_os, \
            patch('main.AirgapValidator') as mock_validator_class, \
            patch('main.stage_bundles_to_all_nodes') as mock_stage_bundles:
                
                # Setup mocks
                mock_setup_node.return_value = True
                mock_gpu_install.return_value = True
                mock_health_check.return_value = True
                mock_stage_bundles.return_value = True
                
                mock_get_dist.return_value = mock_production_environment['rke2_handler']
                mock_get_os.return_value = mock_production_environment['rhel_handler']
                mock_validator_class.return_value = mock_production_environment['validator']
                
                from main import cli
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file, '--verbose'])
                
                # Verify successful deployment
                assert result.exit_code == 0
                mock_log_success.assert_called()
                
                # Verify all nodes were processed (3 servers + 4 agents)
                assert mock_setup_node.call_count == 7
                
                # Verify GPU installation was called for GPU nodes
                assert mock_gpu_install.call_count == 2
                
                # Verify health checks were performed on all server nodes
                assert mock_health_check.call_count == 3
                
                # Verify validation was performed
                mock_production_environment['validator'].run_full_validation.assert_called_once()
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_success')
    def test_production_cluster_with_bundle_staging(self, mock_log_success, mock_logo, 
                                                  production_cluster_config, 
                                                  mock_production_environment):
        """Test production deployment with separate bundle staging phase"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(production_cluster_config, f)
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
                'deploy.airgap.bundle_manager': Mock(),
                'logo.space_jam_logo': Mock(),
                'uninstall.uninstall_cluster': Mock()
            }), \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
            patch('main.stage_bundles_to_all_nodes') as mock_stage_bundles:
                
                mock_get_dist.return_value = mock_production_environment['rke2_handler']
                mock_stage_bundles.return_value = True
                
                from main import cli
                
                runner = CliRunner()
                
                # First, stage bundles only
                result = runner.invoke(cli, ['deploy', '-c', config_file, '--stage-only'])
                assert result.exit_code == 0
                mock_stage_bundles.assert_called_once()
                
                # Then, deploy without staging (would use pre-staged bundles)
                with patch('main.setup_node') as mock_setup_node, \
                     patch('main.install_gpu_stack') as mock_gpu_install, \
                     patch('main.post_install_health_check') as mock_health_check, \
                     patch('main.get_airgapped_os_handler') as mock_get_os, \
                     patch('main.AirgapValidator') as mock_validator_class:
                    
                    mock_setup_node.return_value = True
                    mock_gpu_install.return_value = True
                    mock_health_check.return_value = True
                    mock_get_os.return_value = mock_production_environment['rhel_handler']
                    mock_validator_class.return_value = mock_production_environment['validator']
                    
                    result = runner.invoke(cli, ['deploy', '-c', config_file])
                    assert result.exit_code == 0
                    mock_log_success.assert_called()
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_success')
    def test_production_cluster_health_monitoring(self, mock_log_success, mock_logo, 
                                                production_cluster_config, 
                                                mock_production_environment):
        """Test health check monitoring for production cluster"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(production_cluster_config, f)
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
            patch('main.post_install_health_check') as mock_health_check:
                
                mock_get_dist.return_value = mock_production_environment['rke2_handler']
                mock_health_check.return_value = True
                
                from main import cli
                
                runner = CliRunner()
                
                # Test health check for all nodes
                result = runner.invoke(cli, ['health-check', '-c', config_file])
                assert result.exit_code == 0
                
                # Should check all server nodes
                assert mock_health_check.call_count == 3
                
                # Test health check for specific node
                result = runner.invoke(cli, ['health-check', '-c', config_file, 
                                           '--node', 'k8s-control-01.company.com'])
                assert result.exit_code == 0
        
        finally:
            os.unlink(config_file)

@pytest.mark.e2e
@pytest.mark.slow
class TestDisasterRecoveryScenarios:
    """End-to-end tests for disaster recovery scenarios"""
    
    @pytest.fixture
    def disaster_recovery_config(self):
        """Configuration for disaster recovery testing"""
        return {
            'deployment': {
                'k8s_distribution': 'rke2',
                'os': {'type': 'rhel', 'version': '8'},
                'airgap': {
                    'enabled': True,
                    'local_registry': 'backup-registry.company.com:5000',
                    'bundle_staging_path': '/backup/k8s-bundles',
                    'image_staging_path': '/backup/container-images'
                },
                'rke2': {
                    'version': 'v1.32.3',
                    'airgap_bundle_path': '/backup/rke2-airgap-bundle.tar.gz',
                    'images_bundle_path': '/backup/rke2-images.tar.gz',
                    'install_script_path': '/backup/install.sh'
                }
            },
            'cluster': {
                'rke2': {
                    'name': 'disaster-recovery-cluster',
                    'domain': 'dr.company.com',
                    'token': 'DR-K10a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6',
                    'cluster_cidr': '10.44.0.0/16',
                    'service_cidr': '10.45.0.0/16'
                }
            },
            'nodes': {
                'servers': [
                    {
                        'hostname': 'dr-k8s-control-01.company.com',
                        'ip': '10.20.10.11',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/dr_k8s_rsa'
                    },
                    {
                        'hostname': 'dr-k8s-control-02.company.com',
                        'ip': '10.20.10.12',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/dr_k8s_rsa'
                    }
                ],
                'agents': [
                    {
                        'hostname': 'dr-k8s-worker-01.company.com',
                        'ip': '10.20.10.21',
                        'user': 'k8s-admin',
                        'ssh_key': '/home/deploy/.ssh/dr_k8s_rsa',
                        'gpu_enabled': False
                    }
                ]
            },
            'extra_tools': ['k9s', 'helm']
        }
    
    @patch('main.display_animated_logo')
    @patch('main.display_space_jam_logo4')
    @patch('main.log_success')
    def test_disaster_recovery_cluster_deployment(self, mock_log_success, mock_logo4, 
                                                mock_logo, disaster_recovery_config):
        """Test disaster recovery cluster deployment"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(disaster_recovery_config, f)
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
            patch('main.setup_node') as mock_setup_node, \
            patch('main.post_install_health_check') as mock_health_check, \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
            patch('main.get_airgapped_os_handler') as mock_get_os, \
            patch('main.AirgapValidator') as mock_validator:
                
                # Setup successful mocks
                mock_setup_node.return_value = True
                mock_health_check.return_value = True
                
                mock_dist_handler = Mock()
                mock_dist_handler.validate_requirements.return_value = True
                mock_get_dist.return_value = mock_dist_handler
                
                mock_os_handler = Mock()
                mock_get_os.return_value = mock_os_handler
                
                mock_validator_instance = Mock()
                mock_validator_instance.run_full_validation.return_value = True
                mock_validator.return_value = mock_validator_instance
                
                from main import cli
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                
                # Verify DR cluster deployment
                assert result.exit_code == 0
                mock_log_success.assert_called()
                
                # Verify all DR nodes were processed (2 servers + 1 agent)
                assert mock_setup_node.call_count == 3
                
                # Verify health checks on server nodes
                assert mock_health_check.call_count == 2
        
        finally:
            os.unlink(config_file)

@pytest.mark.e2e
@pytest.mark.performance
class TestPerformanceScenarios:
    """End-to-end performance tests"""
    
    @pytest.fixture
    def large_cluster_config(self):
        """Large cluster configuration for performance testing"""
        config = {
            'deployment': {
                'k8s_distribution': 'rke2',
                'os': {'type': 'rhel', 'version': '8'},
                'airgap': {
                    'enabled': True,
                    'local_registry': 'registry.perf.local:5000',
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
                    'name': 'large-performance-cluster',
                    'domain': 'perf.local',
                    'token': 'PERF-TOKEN-123456789',
                    'cluster_cidr': '10.42.0.0/16',
                    'service_cidr': '10.43.0.0/16'
                }
            },
            'nodes': {
                'servers': [],
                'agents': []
            },
            'extra_tools': ['k9s', 'helm', 'flux']
        }
        
        # Generate 5 server nodes
        for i in range(1, 6):
            config['nodes']['servers'].append({
                'hostname': f'perf-server-{i:02d}.perf.local',
                'ip': f'10.100.1.{10 + i}',
                'user': 'k8s-admin',
                'ssh_key': '/home/deploy/.ssh/perf_key'
            })
        
        # Generate 20 worker nodes
        for i in range(1, 21):
            config['nodes']['agents'].append({
                'hostname': f'perf-worker-{i:02d}.perf.local',
                'ip': f'10.100.2.{10 + i}',
                'user': 'k8s-admin',
                'ssh_key': '/home/deploy/.ssh/perf_key',
                'gpu_enabled': i % 5 == 0  # Every 5th node has GPU
            })
        
        return config
    
    @patch('main.display_animated_logo')
    @patch('main.log_success')
    def test_large_cluster_deployment_performance(self, mock_log_success, mock_logo, 
                                                large_cluster_config):
        """Test deployment performance with large cluster"""
        from click.testing import CliRunner
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(large_cluster_config, f)
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
            patch('main.setup_node') as mock_setup_node, \
            patch('main.install_gpu_stack') as mock_gpu_install, \
            patch('main.post_install_health_check') as mock_health_check, \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
            patch('main.get_airgapped_os_handler') as mock_get_os, \
            patch('main.AirgapValidator') as mock_validator:
                
                # Setup mocks with slight delays to simulate real deployment
                def slow_setup_node(*args, **kwargs):
                    time.sleep(0.01)  # Simulate deployment time
                    return True
                
                def slow_gpu_install(*args, **kwargs):
                    time.sleep(0.02)  # Simulate GPU installation time
                    return True
                
                def slow_health_check(*args, **kwargs):
                    time.sleep(0.005)  # Simulate health check time
                    return True
                
                mock_setup_node.side_effect = slow_setup_node
                mock_gpu_install.side_effect = slow_gpu_install
                mock_health_check.side_effect = slow_health_check
                
                mock_dist_handler = Mock()
                mock_dist_handler.validate_requirements.return_value = True
                mock_get_dist.return_value = mock_dist_handler
                
                mock_os_handler = Mock()
                mock_get_os.return_value = mock_os_handler
                
                mock_validator_instance = Mock()
                mock_validator_instance.run_full_validation.return_value = True
                mock_validator.return_value = mock_validator_instance
                
                from main import cli
                
                runner = CliRunner()
                
                # Measure deployment time
                start_time = time.time()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                end_time = time.time()
                
                deployment_time = end_time - start_time
                
                # Verify successful deployment
                assert result.exit_code == 0
                mock_log_success.assert_called()
                
                # Verify all nodes were processed (5 servers + 20 agents)
                assert mock_setup_node.call_count == 25
                
                # Verify GPU installation for GPU nodes (4 nodes)
                assert mock_gpu_install.call_count == 4
                
                # Verify health checks on server nodes
                assert mock_health_check.call_count == 5
                
                # Performance assertion (should complete within reasonable time)
                # This is a mock test, so times will be very fast
                assert deployment_time < 5.0, f"Deployment took too long: {deployment_time}s"
        
        finally:
            os.unlink(config_file)
    
    @patch('main.display_animated_logo')
    @patch('main.log_success')
    def test_concurrent_node_deployment_simulation(self, mock_log_success, mock_logo, 
                                                 large_cluster_config):
        """Test simulated concurrent node deployment"""
        from click.testing import CliRunner
        import threading
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(large_cluster_config, f)
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
            patch('main.setup_node') as mock_setup_node, \
            patch('main.get_airgapped_distribution_handler') as mock_get_dist, \
            patch('main.get_airgapped_os_handler') as mock_get_os, \
            patch('main.AirgapValidator') as mock_validator:
                
                # Track concurrent calls
                concurrent_calls = []
                call_lock = threading.Lock()
                
                def concurrent_setup_node(*args, **kwargs):
                    with call_lock:
                        concurrent_calls.append(time.time())
                    time.sleep(0.01)  # Simulate work
                    return True
                
                mock_setup_node.side_effect = concurrent_setup_node
                
                mock_dist_handler = Mock()
                mock_dist_handler.validate_requirements.return_value = True
                mock_get_dist.return_value = mock_dist_handler
                
                mock_os_handler = Mock()
                mock_get_os.return_value = mock_os_handler
                
                mock_validator_instance = Mock()
                mock_validator_instance.run_full_validation.return_value = True
                mock_validator.return_value = mock_validator_instance
                
                from main import cli
                
                runner = CliRunner()
                result = runner.invoke(cli, ['deploy', '-c', config_file])
                
                # Verify successful deployment
                assert result.exit_code == 0
                mock_log_success.assert_called()
                
                # Verify concurrent execution patterns
                assert len(concurrent_calls) == 25  # All nodes processed
                
                # Check that calls happened in reasonable time window
                if len(concurrent_calls) > 1:
                    time_span = max(concurrent_calls) - min(concurrent_calls)
                    assert time_span < 2.0, f"Deployment calls took too long: {time_span}s"
        
        finally:
            os.unlink(config_file)
