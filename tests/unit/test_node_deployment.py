import pytest
from unittest.mock import Mock, patch, MagicMock
import paramiko

class TestNodeDeployment:
    """Test node deployment functionality"""
    
    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client for testing"""
        mock_ssh = Mock(spec=paramiko.SSHClient)
        mock_ssh.connect = Mock()
        mock_ssh.exec_command = Mock()
        mock_ssh.close = Mock()
        
        # Setup default successful command execution
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"success"
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        
        mock_ssh.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
        
        return mock_ssh
    
    @pytest.fixture
    def mock_handlers(self):
        """Mock distribution and OS handlers"""
        mock_dist_handler = Mock()
        mock_dist_handler.prepare_server_node.return_value = True
        mock_dist_handler.prepare_agent_node.return_value = True
        mock_dist_handler.install_distribution.return_value = True
        mock_dist_handler.start_services.return_value = True
        
        mock_os_handler = Mock()
        mock_os_handler.install_base_packages.return_value = True
        mock_os_handler.disable_swap.return_value = True
        mock_os_handler.configure_kernel_modules.return_value = True
        mock_os_handler.configure_selinux.return_value = True
        mock_os_handler.configure_firewall.return_value = True
        mock_os_handler.get_os_name.return_value = 'rhel'
        
        return mock_dist_handler, mock_os_handler
    
    @pytest.fixture
    def sample_node(self):
        """Sample node configuration"""
        return {
            'hostname': 'test-server-1',
            'ip': '10.0.4.10',
            'user': 'k8s-admin',
            'ssh_key': '.ssh/test_key',
            'sudo_password': ''
        }
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_message')
    @patch('deploy.node.log_success')
    def test_setup_node_server_success(self, mock_log_success, mock_log_message, 
                                     mock_ssh_class, sample_node, sample_config, 
                                     mock_handlers, mock_ssh_client):
        """Test successful server node setup"""
        from deploy.node import setup_node
        
        mock_ssh_class.return_value = mock_ssh_client
        mock_dist_handler, mock_os_handler = mock_handlers
        
        result = setup_node(
            sample_node, 
            sample_config, 
            mock_dist_handler, 
            mock_os_handler, 
            is_server=True, 
            is_first_server=True
        )
        
        assert result is True
        mock_ssh_client.connect.assert_called_once()
        mock_os_handler.install_base_packages.assert_called_once()
        mock_os_handler.disable_swap.assert_called_once()
        mock_os_handler.configure_kernel_modules.assert_called_once()
        mock_os_handler.configure_selinux.assert_called_once()
        mock_os_handler.configure_firewall.assert_called_once()
        mock_dist_handler.prepare_server_node.assert_called_once()
        mock_dist_handler.install_distribution.assert_called_once()
        mock_dist_handler.start_services.assert_called_once()
        mock_ssh_client.close.assert_called_once()
        mock_log_success.assert_called()
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_message')
    @patch('deploy.node.log_success')
    def test_setup_node_agent_success(self, mock_log_success, mock_log_message, 
                                    mock_ssh_class, sample_node, sample_config, 
                                    mock_handlers, mock_ssh_client):
        """Test successful agent node setup"""
        from deploy.node import setup_node
        
        mock_ssh_class.return_value = mock_ssh_client
        mock_dist_handler, mock_os_handler = mock_handlers
        
        result = setup_node(
            sample_node, 
            sample_config, 
            mock_dist_handler, 
            mock_os_handler, 
            is_server=False
        )
        
        assert result is True
        mock_dist_handler.prepare_agent_node.assert_called_once()
        mock_dist_handler.install_distribution.assert_called_with(
            mock_ssh_client, sample_config, 'agent'
        )
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_error')
    def test_setup_node_ssh_connection_failure(self, mock_log_error, mock_ssh_class, 
                                             sample_node, sample_config, mock_handlers):
        """Test node setup failure due to SSH connection error"""
        from deploy.node import setup_node
        
        mock_ssh_client = Mock()
        mock_ssh_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        mock_ssh_class.return_value = mock_ssh_client
        
        mock_dist_handler, mock_os_handler = mock_handlers
        
        result = setup_node(
            sample_node, 
            sample_config, 
            mock_dist_handler, 
            mock_os_handler, 
            is_server=True
        )
        
        assert result is False
        mock_log_error.assert_called()
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_error')
    def test_setup_node_os_preparation_failure(self, mock_log_error, mock_ssh_class, 
                                             sample_node, sample_config, 
                                             mock_handlers, mock_ssh_client):
        """Test node setup failure during OS preparation"""
        from deploy.node import setup_node
        
        mock_ssh_class.return_value = mock_ssh_client
        mock_dist_handler, mock_os_handler = mock_handlers
        
        # Make OS handler fail
        mock_os_handler.install_base_packages.return_value = False
        
        result = setup_node(
            sample_node, 
            sample_config, 
            mock_dist_handler, 
            mock_os_handler, 
            is_server=True
        )
        
        assert result is False
        mock_log_error.assert_called()
        mock_ssh_client.close.assert_called()
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_error')
    def test_setup_node_distribution_failure(self, mock_log_error, mock_ssh_class, 
                                           sample_node, sample_config, 
                                           mock_handlers, mock_ssh_client):
        """Test node setup failure during distribution installation"""
        from deploy.node import setup_node
        
        mock_ssh_class.return_value = mock_ssh_client
        mock_dist_handler, mock_os_handler = mock_handlers
        
        # Make distribution handler fail
        mock_dist_handler.install_distribution.return_value = False
        
        result = setup_node(
            sample_node, 
            sample_config, 
            mock_dist_handler, 
            mock_os_handler, 
            is_server=True
        )
        
        assert result is False
        mock_log_error.assert_called()
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.install_extra_tools')
    @patch('deploy.node.log_success')
    def test_setup_node_with_extra_tools(self, mock_log_success, mock_install_tools, 
                                       mock_ssh_class, sample_node, sample_config, 
                                       mock_handlers, mock_ssh_client):
        """Test server node setup with extra tools installation"""
        from deploy.node import setup_node
        
        mock_ssh_class.return_value = mock_ssh_client
        mock_dist_handler, mock_os_handler = mock_handlers
        
        # Add extra tools to config
        sample_config['extra_tools'] = ['k9s', 'helm']
        
        result = setup_node(
            sample_node, 
            sample_config, 
            mock_dist_handler, 
            mock_os_handler, 
            is_server=True
        )
        
        assert result is True
        mock_install_tools.assert_called_once_with(
            mock_ssh_client, ['k9s', 'helm'], mock_os_handler, sample_config
        )
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_message')
    def test_setup_node_vanilla_k8s_container_runtime(self, mock_log_message, mock_ssh_class, 
                                                    sample_node, sample_config, 
                                                    mock_handlers, mock_ssh_client):
        """Test node setup with vanilla Kubernetes container runtime installation"""
        from deploy.node import setup_node
        
        mock_ssh_class.return_value = mock_ssh_client
        mock_dist_handler, mock_os_handler = mock_handlers
        mock_os_handler.install_container_runtime.return_value = True
        
        # Configure for vanilla Kubernetes
        sample_config['deployment']['type'] = 'vanilla_k8s'
        sample_config['deployment']['vanilla_k8s'] = {
            'container_runtime': 'containerd'
        }
        
        result = setup_node(
            sample_node, 
            sample_config, 
            mock_dist_handler, 
            mock_os_handler, 
            is_server=True
        )
        
        assert result is True
        mock_os_handler.install_container_runtime.assert_called_once_with(
            mock_ssh_client, 'containerd'
        )

class TestGPUInstallation:
    """Test GPU stack installation"""
    
    @pytest.fixture
    def gpu_node(self):
        """GPU-enabled node configuration"""
        return {
            'hostname': 'gpu-worker-1',
            'ip': '10.0.4.20',
            'user': 'k8s-admin',
            'ssh_key': '.ssh/test_key',
            'gpu_enabled': True
        }
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_success')
    def test_install_gpu_stack_success(self, mock_log_success, mock_ssh_class, 
                                     gpu_node, sample_config):
        """Test successful GPU stack installation"""
        from deploy.node import install_gpu_stack
        
        mock_ssh_client = Mock()
        mock_ssh_class.return_value = mock_ssh_client
        
        mock_os_handler = Mock()
        mock_os_handler.install_gpu_packages.return_value = True
        mock_os_handler.get_os_name.return_value = 'rhel'
        
        result = install_gpu_stack(gpu_node, sample_config, mock_os_handler)
        
        assert result is True
        mock_ssh_client.connect.assert_called_once()
        mock_os_handler.install_gpu_packages.assert_called_once()
        mock_ssh_client.close.assert_called_once()
        mock_log_success.assert_called()
    
    @patch('deploy.node.paramiko.SSHClient')
    @patch('deploy.node.log_error')
    def test_install_gpu_stack_failure(self, mock_log_error, mock_ssh_class, 
                                     gpu_node, sample_config):
        """Test GPU stack installation failure"""
        from deploy.node import install_gpu_stack
        
        mock_ssh_client = Mock()
        mock_ssh_class.return_value = mock_ssh_client
        
        mock_os_handler = Mock()
        mock_os_handler.install_gpu_packages.return_value = False
        
        result = install_gpu_stack(gpu_node, sample_config, mock_os_handler)
        
        assert result is False
        mock_log_error.assert_called()

class TestExtraToolsInstallation:
    """Test extra tools installation"""
    
    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client for tools installation"""
        mock_ssh = Mock()
        return mock_ssh
    
    @pytest.fixture
    def mock_os_handler(self):
        """Mock OS handler"""
        return Mock()
    
    @patch('deploy.node.run_ssh_command')
    def test_install_k9s_online(self, mock_run_ssh, mock_ssh_client, mock_os_handler):
        """Test k9s installation in online mode"""
        from deploy.node import install_k9s
        
        mock_run_ssh.return_value = True
        
        install_k9s(mock_ssh_client, mock_os_handler, is_airgapped=False)
        
        # Should execute online installation commands
        assert mock_run_ssh.call_count == 3  # curl, install, cleanup
        
        # Check that online installation commands were called
        calls = mock_run_ssh.call_args_list
        assert any('curl' in str(call) for call in calls)
        assert any('install' in str(call) for call in calls)
    
    @patch('deploy.node.run_ssh_command')
    @patch('deploy.node._get_bundle_path')
    def test_install_k9s_airgapped(self, mock_get_bundle, mock_run_ssh, 
                                 mock_ssh_client, mock_os_handler, sample_config):
        """Test k9s installation in airgapped mode"""
        from deploy.node import install_k9s
        
        mock_run_ssh.return_value = True
        mock_get_bundle.return_value = '/opt/k8s-bundles'
        
        install_k9s(mock_ssh_client, mock_os_handler, sample_config, is_airgapped=True)
        
        # Should execute airgapped installation commands
        assert mock_run_ssh.call_count == 2  # copy and chmod
        
        # Check that airgapped installation commands were called
        calls = mock_run_ssh.call_args_list
        assert any('/opt/k8s-bundles/bin/k9s' in str(call) for call in calls)
    
    @patch('deploy.node.run_ssh_command')
    def test_install_helm_online(self, mock_run_ssh, mock_ssh_client, mock_os_handler):
        """Test Helm installation in online mode"""
        from deploy.node import install_helm
        
        mock_run_ssh.return_value = True
        
        install_helm(mock_ssh_client, mock_os_handler, is_airgapped=False)
        
        # Should execute online installation command
        mock_run_ssh.assert_called_once()
        call_args = mock_run_ssh.call_args[0][1]
        assert 'get-helm-3' in call_args
    
    @patch('deploy.node.run_ssh_command')
    def test_install_flux_online(self, mock_run_ssh, mock_ssh_client, mock_os_handler):
        """Test Flux installation in online mode"""
        from deploy.node import install_flux
        
        mock_run_ssh.return_value = True
        
        install_flux(mock_ssh_client, mock_os_handler, is_airgapped=False)
        
        # Should execute online installation commands
        assert mock_run_ssh.call_count == 2  # install script and move binary
    
    @patch('deploy.node.install_k9s')
    @patch('deploy.node.install_helm')
    @patch('deploy.node.install_flux')
    @patch('deploy.node.log_warning')
    def test_install_extra_tools_all(self, mock_log_warning, mock_install_flux, 
                                   mock_install_helm, mock_install_k9s, 
                                   mock_ssh_client, mock_os_handler, sample_config):
        """Test installation of all supported extra tools"""
        from deploy.node import install_extra_tools
        
        tools = ['k9s', 'helm', 'flux', 'unknown_tool']
        
        install_extra_tools(mock_ssh_client, tools, mock_os_handler, sample_config)
        
        mock_install_k9s.assert_called_once()
        mock_install_helm.assert_called_once()
        mock_install_flux.assert_called_once()
        mock_log_warning.assert_called_once_with("Unknown tool: unknown_tool")
    
    @patch('deploy.node.install_k9s')
    @patch('deploy.node.log_error')
    def test_install_extra_tools_failure(self, mock_log_error, mock_install_k9s, 
                                       mock_ssh_client, mock_os_handler, sample_config):
        """Test extra tools installation with failure"""
        from deploy.node import install_extra_tools
        
        mock_install_k9s.side_effect = Exception("Installation failed")
        
        install_extra_tools(mock_ssh_client, ['k9s'], mock_os_handler, sample_config)
        
        mock_log_error.assert_called_once()
    
    def test_get_bundle_path_server_node(self, mock_ssh_client, sample_config):
        """Test bundle path retrieval for server node"""
        from deploy.node import _get_bundle_path
        
        # Mock transport to return server IP
        mock_transport = Mock()
        mock_transport.getpeername.return_value = ('10.0.4.10', 22)
        mock_ssh_client.get_transport.return_value = mock_transport
        
        # Add staging paths to server node
        sample_config['nodes']['servers'][0]['staging_paths'] = {
            'bundles': '/custom/bundle/path'
        }
        
        result = _get_bundle_path(mock_ssh_client, sample_config)
        assert result == '/custom/bundle/path'
    
    def test_get_bundle_path_agent_node(self, mock_ssh_client, sample_config):
        """Test bundle path retrieval for agent node"""
        from deploy.node import _get_bundle_path
        
        # Mock transport to return agent IP
        mock_transport = Mock()
        mock_transport.getpeername.return_value = ('10.0.4.177', 22)
        mock_ssh_client.get_transport.return_value = mock_transport
        
        # Add staging paths to agent node
        sample_config['nodes']['agents'][0]['staging_paths'] = {
            'bundles': '/agent/bundle/path'
        }
        
        result = _get_bundle_path(mock_ssh_client, sample_config)
        assert result == '/agent/bundle/path'
    
    def test_get_bundle_path_default(self, mock_ssh_client, sample_config):
        """Test bundle path retrieval with default fallback"""
        from deploy.node import _get_bundle_path
        
        # Mock transport to return unknown IP
        mock_transport = Mock()
        mock_transport.getpeername.return_value = ('10.0.4.999', 22)
        mock_ssh_client.get_transport.return_value = mock_transport
        
        result = _get_bundle_path(mock_ssh_client, sample_config)
        assert result == '/tmp/k8s-bundles'
    
    @patch('deploy.node.log_error')
    def test_get_bundle_path_error(self, mock_log_error, mock_ssh_client, sample_config):
        """Test bundle path retrieval with transport error"""
        from deploy.node import _get_bundle_path
        
        # Mock transport error
        mock_ssh_client.get_transport.side_effect = Exception("Transport error")
        
        result = _get_bundle_path(mock_ssh_client, sample_config)
        assert result == '/tmp/k8s-bundles'
        mock_log_error.assert_called_once()
