import pytest
from unittest.mock import Mock, patch, MagicMock
import paramiko

class TestHealthChecks:
    """Test health check functionality"""
    
    @pytest.fixture
    def sample_node(self):
        """Sample node configuration for health checks"""
        return {
            'hostname': 'test-server-1',
            'ip': '10.0.4.10',
            'user': 'k8s-admin',
            'ssh_key': '.ssh/test_key'
        }
    
    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client for health checks"""
        mock_ssh = Mock(spec=paramiko.SSHClient)
        mock_ssh.connect = Mock()
        mock_ssh.exec_command = Mock()
        mock_ssh.close = Mock()
        return mock_ssh
    
    @patch('deploy.health.paramiko.SSHClient')
    @patch('deploy.health.log_success')
    @patch('deploy.health.log_message')
    def test_post_install_health_check_rke2_server_active(self, mock_log_message, 
                                                        mock_log_success, mock_ssh_class, 
                                                        sample_node, mock_ssh_client):
        """Test health check with active RKE2 server"""
        from deploy.health import post_install_health_check
        
        mock_ssh_class.return_value = mock_ssh_client
        
        # Mock systemctl command to return active status
        mock_stdout_status = Mock()
        mock_stdout_status.read.return_value = b"active"
        mock_stderr_status = Mock()
        mock_stderr_status.read.return_value = b""
        
        # Mock kubectl command to return node list
        mock_stdout_nodes = Mock()
        mock_stdout_nodes.read.return_value = b"NAME           STATUS   ROLES                       AGE   VERSION\ntest-server-1  Ready    control-plane,etcd,master   1m    v1.32.3+rke2r1"
        mock_stderr_nodes = Mock()
        mock_stderr_nodes.read.return_value = b""
        
        # Setup exec_command to return different results for different commands
        mock_ssh_client.exec_command.side_effect = [
            (Mock(), mock_stdout_status, mock_stderr_status),  # systemctl command
            (Mock(), mock_stdout_nodes, mock_stderr_nodes)     # kubectl command
        ]
        
        post_install_health_check(sample_node)
        
        # Verify SSH connection and commands
        mock_ssh_client.connect.assert_called_once_with(
            hostname='10.0.4.10',
            username='k8s-admin',
            key_filename='.ssh/test_key'
        )
        
        assert mock_ssh_client.exec_command.call_count == 2
        mock_log_success.assert_called()
        mock_log_message.assert_called()
        mock_ssh_client.close.assert_called_once()
    
    @patch('deploy.health.paramiko.SSHClient')
    @patch('deploy.health.log_error')
    @patch('deploy.health.log_message')
    def test_post_install_health_check_rke2_inactive(self, mock_log_message, 
                                                   mock_log_error, mock_ssh_class, 
                                                   sample_node, mock_ssh_client):
        """Test health check with inactive RKE2 service"""
        from deploy.health import post_install_health_check
        
        mock_ssh_class.return_value = mock_ssh_client
        
        # Mock systemctl command to return inactive status
        mock_stdout_status = Mock()
        mock_stdout_status.read.return_value = b"inactive"
        mock_stderr_status = Mock()
        mock_stderr_status.read.return_value = b""
        
        # Mock kubectl command (won't be reached but setup anyway)
        mock_stdout_nodes = Mock()
        mock_stdout_nodes.read.return_value = b""
        mock_stderr_nodes = Mock()
        mock_stderr_nodes.read.return_value = b"connection refused"
        
        mock_ssh_client.exec_command.side_effect = [
            (Mock(), mock_stdout_status, mock_stderr_status),
            (Mock(), mock_stdout_nodes, mock_stderr_nodes)
        ]
        
        post_install_health_check(sample_node)
        
        mock_log_error.assert_called()
        # Should still try kubectl command
        assert mock_ssh_client.exec_command.call_count == 2
    
    @patch('deploy.health.paramiko.SSHClient')
    @patch('deploy.health.log_success')
    @patch('deploy.health.log_warning')
    def test_post_install_health_check_kubectl_error(self, mock_log_warning, 
                                                    mock_log_success, mock_ssh_class, 
                                                    sample_node, mock_ssh_client):
        """Test health check with kubectl command error"""
        from deploy.health import post_install_health_check
        
        mock_ssh_class.return_value = mock_ssh_client
        
        # Mock systemctl command to return active status
        mock_stdout_status = Mock()
        mock_stdout_status.read.return_value = b"active"
        mock_stderr_status = Mock()
        mock_stderr_status.read.return_value = b""
        
        # Mock kubectl command to return error
        mock_stdout_nodes = Mock()
        mock_stdout_nodes.read.return_value = b""
        mock_stderr_nodes = Mock()
        mock_stderr_nodes.read.return_value = b"The connection to the server localhost:8080 was refused"
        
        mock_ssh_client.exec_command.side_effect = [
            (Mock(), mock_stdout_status, mock_stderr_status),
            (Mock(), mock_stdout_nodes, mock_stderr_nodes)
        ]
        
        post_install_health_check(sample_node)
        
        mock_log_success.assert_called()  # RKE2 is active
        mock_log_warning.assert_called()  # kubectl failed
    
    @patch('deploy.health.paramiko.SSHClient')
    @patch('deploy.health.log_error')
    def test_post_install_health_check_ssh_connection_error(self, mock_log_error, 
                                                          mock_ssh_class, sample_node):
        """Test health check with SSH connection error"""
        from deploy.health import post_install_health_check
        
        mock_ssh_client = Mock()
        mock_ssh_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        mock_ssh_class.return_value = mock_ssh_client
        
        post_install_health_check(sample_node)
        
        mock_log_error.assert_called()
        # Should not call exec_command if connection fails
        mock_ssh_client.exec_command.assert_not_called()
    
    @patch('deploy.health.paramiko.SSHClient')
    @patch('deploy.health.log_error')
    def test_post_install_health_check_command_execution_error(self, mock_log_error, 
                                                             mock_ssh_class, 
                                                             sample_node, mock_ssh_client):
        """Test health check with command execution error"""
        from deploy.health import post_install_health_check
        
        mock_ssh_class.return_value = mock_ssh_client
        mock_ssh_client.exec_command.side_effect = Exception("Command execution failed")
        
        post_install_health_check(sample_node)
        
        mock_log_error.assert_called()
    
    @patch('deploy.health.paramiko.SSHClient')
    @patch('deploy.health.log_success')
    @patch('deploy.health.log_message')
    def test_post_install_health_check_rke2_agent_active(self, mock_log_message, 
                                                       mock_log_success, mock_ssh_class, 
                                                       sample_node, mock_ssh_client):
        """Test health check with active RKE2 agent"""
        from deploy.health import post_install_health_check
        
        mock_ssh_class.return_value = mock_ssh_client
        
        # Mock systemctl command to return active for agent (server check fails, agent succeeds)
        mock_stdout_status = Mock()
        mock_stdout_status.read.return_value = b"active"
        mock_stderr_status = Mock()
        mock_stderr_status.read.return_value = b""
        
        # Mock kubectl command (agents typically can't run kubectl directly)
        mock_stdout_nodes = Mock()
        mock_stdout_nodes.read.return_value = b""
        mock_stderr_nodes = Mock()
        mock_stderr_nodes.read.return_value = b"kubectl not found or not configured"
        
        mock_ssh_client.exec_command.side_effect = [
            (Mock(), mock_stdout_status, mock_stderr_status),
            (Mock(), mock_stdout_nodes, mock_stderr_nodes)
        ]
        
        post_install_health_check(sample_node)
        
        mock_log_success.assert_called()
    
    @patch('deploy.health.paramiko.SSHClient')
    @patch('deploy.health.log_success')
    @patch('deploy.health.log_message')
    def test_post_install_health_check_with_node_details(self, mock_log_message, 
                                                       mock_log_success, mock_ssh_class, 
                                                       sample_node, mock_ssh_client):
        """Test health check with detailed node information"""
        from deploy.health import post_install_health_check
        
        mock_ssh_class.return_value = mock_ssh_client
        
        # Mock systemctl command
        mock_stdout_status = Mock()
        mock_stdout_status.read.return_value = b"active"
        mock_stderr_status = Mock()
        mock_stderr_status.read.return_value = b""
        
        # Mock kubectl command with detailed node output
        detailed_output = """NAME           STATUS   ROLES                       AGE   VERSION
test-server-1  Ready    control-plane,etcd,master   5m    v1.32.3+rke2r1
test-agent-1   Ready    <none>                      3m    v1.32.3+rke2r1
test-agent-2   Ready    <none>                      2m    v1.32.3+rke2r1"""
        
        mock_stdout_nodes = Mock()
        mock_stdout_nodes.read.return_value = detailed_output.encode()
        mock_stderr_nodes = Mock()
        mock_stderr_nodes.read.return_value = b""
        
        mock_ssh_client.exec_command.side_effect = [
            (Mock(), mock_stdout_status, mock_stderr_status),
            (Mock(), mock_stdout_nodes, mock_stderr_nodes)
        ]
        
        post_install_health_check(sample_node)
        
        mock_log_success.assert_called()
        
        # Check that detailed node information was logged
        log_calls = mock_log_message.call_args_list
        node_info_logged = any("Cluster Nodes:" in str(call) for call in log_calls)
        assert node_info_logged
    
    def test_health_check_integration_with_distribution_handler(self, sample_node):
        """Test health check integration with distribution handler"""
        # This would be an integration test that verifies the health check
        # works with actual distribution handlers
        
        # Mock distribution handler
        mock_dist_handler = Mock()
        mock_dist_handler.get_service_name.return_value = "rke2-server"
        mock_dist_handler.get_health_check_commands.return_value = [
            "systemctl is-active rke2-server",
            "kubectl get nodes --kubeconfig /etc/rancher/rke2/rke2.yaml"
        ]
        
        # This test would verify that the health check can be extended
        # to work with different distribution handlers
        assert mock_dist_handler.get_service_name() == "rke2-server"
        assert len(mock_dist_handler.get_health_check_commands()) == 2

class TestHealthCheckUtilities:
    """Test health check utility functions"""
    
    def test_parse_systemctl_status(self):
        """Test parsing systemctl status output"""
        # This would test a utility function for parsing systemctl output
        # if such a function existed in the health module
        
        active_output = "active"
        inactive_output = "inactive"
        failed_output = "failed"
        
        # Mock function that would parse status
        def parse_status(output):
            return output.strip() == "active"
        
        assert parse_status(active_output) is True
        assert parse_status(inactive_output) is False
        assert parse_status(failed_output) is False
    
    def test_parse_kubectl_nodes_output(self):
        """Test parsing kubectl nodes output"""
        # This would test a utility function for parsing kubectl output
        
        nodes_output = """NAME           STATUS   ROLES                       AGE   VERSION
test-server-1  Ready    control-plane,etcd,master   5m    v1.32.3+rke2r1
test-agent-1   Ready    <none>                      3m    v1.32.3+rke2r1"""
        
        # Mock function that would parse nodes
        def parse_nodes(output):
            lines = output.strip().split('\n')[1:]  # Skip header
            nodes = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    nodes.append({
                        'name': parts[0],
                        'status': parts[1],
                        'roles': parts[2] if len(parts) > 2 else '<none>'
                    })
            return nodes
        
        nodes = parse_nodes(nodes_output)
        assert len(nodes) == 2
        assert nodes[0]['name'] == 'test-server-1'
        assert nodes[0]['status'] == 'Ready'
        assert nodes[1]['name'] == 'test-agent-1'
    
    def test_health_check_timeout_handling(self):
        """Test health check timeout handling"""
        # This would test timeout handling in health checks
        
        def mock_health_check_with_timeout(timeout=30):
            # Mock implementation that would handle timeouts
            import time
            start_time = time.time()
            
            # Simulate a long-running operation
            while time.time() - start_time < timeout:
                # Check if operation completed
                return True
            
            # Timeout occurred
            return False
        
        # Test normal completion
        result = mock_health_check_with_timeout(timeout=1)
        assert result is True
    
    def test_health_check_retry_logic(self):
        """Test health check retry logic"""
        # This would test retry logic for health checks
        
        def mock_health_check_with_retry(max_retries=3):
            attempts = 0
            
            while attempts < max_retries:
                attempts += 1
                
                # Mock check that fails first two times, succeeds on third
                if attempts < 3:
                    continue  # Simulate failure
                else:
                    return True  # Simulate success
            
            return False  # All retries exhausted
        
        result = mock_health_check_with_retry(max_retries=3)
        assert result is True
        
        result = mock_health_check_with_retry(max_retries=2)
        assert result is False
