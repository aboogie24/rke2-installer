import pytest
from unittest.mock import Mock, patch
import socket
import subprocess

class TestSSHUtils:
    """Test SSH utility functions"""
    
    @patch('deploy.utils.log_debug')
    def test_run_ssh_command_success(self, mock_log_debug, mock_ssh_client):
        """Test successful SSH command execution"""
        # Import after patching
        from deploy.utils import run_ssh_command
        
        result = run_ssh_command(mock_ssh_client, "echo 'test'")
        assert result is True
        mock_ssh_client.exec_command.assert_called_once_with("echo 'test'", timeout=300)
    
    def test_run_ssh_command_failure(self, mock_ssh_client):
        """Test failed SSH command execution"""
        from deploy.utils import run_ssh_command
        
        # Mock command failure
        mock_stdout = Mock()
        mock_stdout.channel.recv_exit_status.return_value = 1
        mock_stderr = Mock()
        mock_stderr.read.return_value = b"command failed"
        
        mock_ssh_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
        
        result = run_ssh_command(mock_ssh_client, "false")
        assert result is False
    
    def test_run_ssh_command_with_output(self, mock_ssh_client):
        """Test SSH command with output capture"""
        from deploy.utils import run_ssh_command
        
        stdout, stderr, exit_code = run_ssh_command(mock_ssh_client, "echo 'test'", return_output=True)
        assert stdout == "success"
        assert stderr == ""
        assert exit_code == 0

class TestLogging:
    """Test logging utility functions"""
    
    @patch('click.echo')
    def test_log_message_general(self, mock_echo):
        """Test general log message function"""
        from deploy.utils import log_message
        
        log_message("test message")
        mock_echo.assert_called_once()
        args = mock_echo.call_args[0][0]
        assert "test message" in args
        assert "[INFO]" in args
    
    @patch('click.echo')
    def test_log_message_node_specific(self, mock_echo):
        """Test node-specific log message function"""
        from deploy.utils import log_message
        
        node = {'hostname': 'test-server'}
        log_message(node, "test message")
        mock_echo.assert_called_once()
        args = mock_echo.call_args[0][0]
        assert "test-server" in args
        assert "test message" in args
    
    @patch('click.echo')
    def test_log_error_node_specific(self, mock_echo):
        """Test node-specific error logging"""
        from deploy.utils import log_error
        
        node = {'hostname': 'test-server'}
        log_error(node, "test error")
        mock_echo.assert_called_once()
        args = mock_echo.call_args[0][0]
        assert "test-server" in args
        assert "test error" in args

class TestNetworkUtils:
    """Test network utility functions"""
    
    @patch('socket.create_connection')
    def test_check_port_open_success(self, mock_connection):
        """Test successful port check"""
        from deploy.utils import check_port_open
        
        mock_connection.return_value.__enter__ = Mock()
        mock_connection.return_value.__exit__ = Mock(return_value=None)
        
        result = check_port_open("localhost", 22)
        assert result is True
    
    @patch('socket.create_connection')
    def test_check_port_open_failure(self, mock_connection):
        """Test failed port check"""
        from deploy.utils import check_port_open
        
        mock_connection.side_effect = socket.timeout()
        
        result = check_port_open("localhost", 22)
        assert result is False
    
    @patch('socket.gethostbyname')
    def test_resolve_hostname_success(self, mock_resolve):
        """Test successful hostname resolution"""
        from deploy.utils import resolve_hostname
        
        mock_resolve.return_value = "192.168.1.1"
        
        result = resolve_hostname("example.com")
        assert result == "192.168.1.1"
    
    @patch('socket.gethostbyname')
    def test_resolve_hostname_failure(self, mock_resolve):
        """Test failed hostname resolution"""
        from deploy.utils import resolve_hostname
        
        mock_resolve.side_effect = socket.gaierror()
        
        result = resolve_hostname("nonexistent.com")
        assert result is None

class TestFileUtils:
    """Test file utility functions"""
    
    def test_calculate_file_checksum(self, tmp_path):
        """Test file checksum calculation"""
        from deploy.utils import calculate_file_checksum
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        checksum = calculate_file_checksum(str(test_file))
        assert checksum is not None
        assert len(checksum) == 64  # SHA256 length
    
    def test_verify_file_checksum_success(self, tmp_path):
        """Test successful checksum verification"""
        from deploy.utils import calculate_file_checksum, verify_file_checksum
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Calculate checksum
        expected_checksum = calculate_file_checksum(str(test_file))
        
        # Verify checksum
        result = verify_file_checksum(str(test_file), expected_checksum)
        assert result is True
    
    def test_verify_file_checksum_failure(self, tmp_path):
        """Test failed checksum verification"""
        from deploy.utils import verify_file_checksum
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Use wrong checksum
        wrong_checksum = "wrong_checksum"
        
        # Verify checksum
        result = verify_file_checksum(str(test_file), wrong_checksum)
        assert result is False

class TestSystemUtils:
    """Test system utility functions"""
    
    @patch('subprocess.run')
    def test_run_local_command_success(self, mock_run):
        """Test successful local command execution"""
        from deploy.utils import run_local_command
        
        # Mock successful command
        mock_result = Mock()
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        stdout, stderr, exit_code = run_local_command("echo test")
        
        assert stdout == "success output"
        assert stderr == ""
        assert exit_code == 0
    
    @patch('subprocess.run')
    def test_run_local_command_failure(self, mock_run):
        """Test failed local command execution"""
        from deploy.utils import run_local_command
        
        # Mock failed command
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "error output"
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        stdout, stderr, exit_code = run_local_command("false")
        
        assert stdout == ""
        assert stderr == "error output"
        assert exit_code == 1
    
    @patch('subprocess.run')
    def test_run_local_command_timeout(self, mock_run):
        """Test local command timeout"""
        from deploy.utils import run_local_command
        
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
        
        stdout, stderr, exit_code = run_local_command("sleep 100", timeout=1)
        
        assert stdout == ""
        assert "timed out" in stderr.lower()
        assert exit_code == -1

class TestValidationUtils:
    """Test validation utility functions"""
    
    def test_validate_ip_address_ipv4(self):
        """Test IPv4 address validation"""
        from deploy.utils import validate_ip_address
        
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.1") is True
        assert validate_ip_address("invalid") is False
        assert validate_ip_address("256.256.256.256") is False
    
    def test_validate_hostname(self):
        """Test hostname validation"""
        from deploy.utils import validate_hostname
        
        assert validate_hostname("example.com") is True
        assert validate_hostname("server-1") is True
        assert validate_hostname("test.example.com") is True
        assert validate_hostname("invalid..hostname") is False
        assert validate_hostname("") is False
    
    def test_validate_port(self):
        """Test port validation"""
        from deploy.utils import validate_port
        
        assert validate_port(22) is True
        assert validate_port("8080") is True
        assert validate_port(65535) is True
        assert validate_port(0) is False
        assert validate_port(65536) is False
        assert validate_port("invalid") is False# tests/conftest.py - Pytest configuration and fixtures
import pytest
import tempfile
import os
import yaml
from unittest.mock import Mock, MagicMock
import paramiko

@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
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
            'name': 'test-cluster',
            'domain': 'test.local',
            'token': 'test-token',
            'cluster_cidr': '10.42.0.0/16',
            'service_cidr': '10.43.0.0/16',
            'write_kubeconfig_mode': '0644'
        },
        'nodes': {
            'servers': [
                {
                    'hostname': 'test-server-1',
                    'ip': '10.0.4.10',
                    'user': 'k8s-admin',
                    'ssh_key': '.ssh/test_key',
                    'sudo_password': ''
                }
            ],
            'agents': [
                {
                    'hostname': 'test-agent-1',
                    'ip': '10.0.4.177',
                    'user': 'k8s-admin',
                    'ssh_key': '.ssh/test_key',
                    'gpu_enabled': False
                }
            ]
        },
        'extra_tools': ['k9s', 'helm']
    }

@pytest.fixture
def temp_config_file(sample_config):
    """Create a temporary config file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(sample_config, f)
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def mock_ssh_client():
    """Mock SSH client for testing"""
    mock_ssh = Mock(spec=paramiko.SSHClient)
    mock_ssh.connect = Mock()
    mock_ssh.exec_command = Mock()
    mock_ssh.open_sftp = Mock()
    mock_ssh.close = Mock()
    
    # Setup default return values
    mock_stdout = Mock()
    mock_stdout.read.return_value = b"success"
    mock_stdout.channel.recv_exit_status.return_value = 0
    
    mock_stderr = Mock()
    mock_stderr.read.return_value = b""
    
    mock_ssh.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
    
    return mock_ssh

@pytest.fixture
def mock_bundle_files(tmp_path):
    """Create mock bundle files"""
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    
    # Create mock bundle files
    (bundle_dir / "rke2-airgap-bundle.tar.gz").write_bytes(b"mock airgap bundle")
    (bundle_dir / "rke2-images.tar.gz").write_bytes(b"mock images bundle")
    (bundle_dir / "install.sh").write_text("#!/bin/bash\necho 'mock install script'")
    
    return bundle_dir

@pytest.fixture(scope="session")
def test_environment():
    """Setup test environment variables"""
    os.environ['TESTING'] = 'true'
    yield
    if 'TESTING' in os.environ:
        del os.environ['TESTING']

# tests/unit/test_config_validation.py - Unit tests for configuration validation
import pytest
from click.testing import CliRunner
from main import validate_config, load_config, migrate_legacy_config
import yaml
import tempfile
import os

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

# # tests/unit/test_handlers.py - Unit tests for distribution and OS handlers
# import pytest
# from unittest.mock import Mock, patch, MagicMock
# from deploy.distributions.airgapped_rke2_handler import AirgappedRKE2Handler
# from deploy.os_handlers.airgapped_rhel_handler import AirgappedRHELHandler
# from deploy.airgap.bundle_manager import BundleManager

# class TestAirgappedRKE2Handler:
#     """Test RKE2 handler for airgapped environments"""
    
#     @pytest.fixture
#     def handler(self):
#         return AirgappedRKE2Handler()
    
#     def test_validate_requirements_success(self, handler, sample_config, mock_bundle_files):
#         """Test successful requirements validation"""
#         # Update config with real bundle paths
#         rke2_config = sample_config['deployment']['rke2']
#         rke2_config['airgap_bundle_path'] = str(mock_bundle_files / "rke2-airgap-bundle.tar.gz")
#         rke2_config['images_bundle_path'] = str(mock_bundle_files / "rke2-images.tar.gz")
#         rke2_config['install_script_path'] = str(mock_bundle_files / "install.sh")
        
#         result = handler.validate_requirements(sample_config)
#         assert result is True
    
#     def test_validate_requirements_missing_bundle(self, handler, sample_config):
#         """Test validation failure with missing bundles"""
#         # Point to non-existent files
#         rke2_config = sample_config['deployment']['rke2']
#         rke2_config['airgap_bundle_path'] = '/nonexistent/bundle.tar.gz'
        
#         result = handler.validate_requirements(sample_config)
#         assert result is False
    
#     def test_generate_server_config(self, handler, sample_config):
#         """Test server configuration generation"""
#         config_content = handler.generate_server_config(sample_config, is_first_server=True)
        
#         assert "cluster-cidr: 10.42.0.0/16" in config_content
#         assert "service-cidr: 10.43.0.0/16" in config_content
#         assert "token: test-token" in config_content
#         assert "system-default-registry: registry.internal.local:5000" in config_content
    
#     def test_generate_agent_config(self, handler, sample_config):
#         """Test agent configuration generation"""
#         config_content = handler.generate_agent_config(sample_config)
        
#         assert "server: https://10.0.4.10:9345" in config_content
#         assert "token: test-token" in config_content
#         assert "system-default-registry: registry.internal.local:5000" in config_content
    
#     @patch('deploy.utils.run_ssh_command')
#     def test_prepare_server_node(self, mock_run_cmd, handler, sample_config, mock_ssh_client):
#         """Test server node preparation"""
#         mock_run_cmd.return_value = True
#         handler.bundle_manager = Mock()
#         handler.bundle_manager.stage_bundles_to_node.return_value = True
        
#         with patch.object(handler, '_upload_config_file', return_value=True):
#             with patch.object(handler, '_get_current_node', return_value=sample_config['nodes']['servers'][0]):
#                 result = handler.prepare_server_node(mock_ssh_client, sample_config, is_first_server=True)
#                 assert result is True
                
#                 # Verify directories were created
#                 assert mock_run_cmd.call_count >= 2

# class TestAirgappedRHELHandler:
#     """Test RHEL handler for airgapped environments"""
    
#     @pytest.fixture
#     def handler(self):
#         return AirgappedRHELHandler()
    
#     @patch('deploy.utils.run_ssh_command')
#     def test_install_base_packages(self, mock_run_cmd, handler, mock_ssh_client):
#         """Test base package installation"""
#         mock_run_cmd.return_value = True
        
#         with patch.object(handler, '_check_remote_file_exists', return_value=True):
#             result = handler.install_base_packages(mock_ssh_client)
#             assert result is True
#             assert mock_run_cmd.call_count >= 2
    
#     @patch('deploy.utils.run_ssh_command')
#     def test_configure_firewall(self, mock_run_cmd, handler, mock_ssh_client):
#         """Test firewall configuration"""
#         # Mock firewalld as active
#         mock_run_cmd.side_effect = [
#             (True, "active", 0),  # systemctl is-active firewalld
#             True, True, True, True, True  # firewall-cmd commands
#         ]
        
#         result = handler.configure_firewall(mock_ssh_client, 'server')
#         assert result is True
    
#     @patch('deploy.utils.run_ssh_command')
#     def test_disable_swap(self, mock_run_cmd, handler, mock_ssh_client):
#         """Test swap disabling"""
#         mock_run_cmd.return_value = True
        
#         result = handler.disable_swap(mock_ssh_client)
#         assert result is True
#         assert mock_run_cmd.call_count == 2

# class TestBundleManager:
#     """Test bundle management functionality"""
    
#     @pytest.fixture
#     def bundle_manager(self, sample_config):
#         return BundleManager(sample_config)
    
#     @patch('deploy.utils.run_ssh_command')
#     def test_stage_bundles_to_node(self, mock_run_cmd, bundle_manager, mock_ssh_client, sample_config):
#         """Test bundle staging to node"""
#         mock_run_cmd.return_value = True
#         node = sample_config['nodes']['servers'][0]
        
#         with patch.object(bundle_manager, '_stage_rke2_bundles', return_value=True):
#             result = bundle_manager.stage_bundles_to_node(mock_ssh_client, node, 'server')
#             assert result is True
    
#     @patch('deploy.utils.run_ssh_command')
#     def test_upload_file(self, mock_run_cmd, bundle_manager, mock_ssh_client, tmp_path):
#         """Test file upload functionality"""
#         mock_run_cmd.return_value = True
        
#         # Create a test file
#         test_file = tmp_path / "test_file.txt"
#         test_file.write_text("test content")
        
#         mock_sftp = Mock()
#         mock_ssh_client.open_sftp.return_value = mock_sftp
        
#         result = bundle_manager._upload_file(mock_ssh_client, str(test_file), "/remote/path")
#         assert result is True
#         mock_sftp.put.assert_called_once()

# # tests/unit/test_utils.py - Unit tests for utility functions
# import pytest
# from unittest.mock import Mock, patch
# from deploy.utils import run_ssh_command, log_message, log_error, log_success, log_warning

# class TestSSHUtils:
#     """Test SSH utility functions"""
    
#     def test_run_ssh_command_success(self, mock_ssh_client):
#         """Test successful SSH command execution"""
#         result = run_ssh_command(mock_ssh_client, "echo 'test'")
#         assert result is True
#         mock_ssh_client.exec_command.assert_called_once_with("echo 'test'", timeout=300)
    
#     def test_run_ssh_command_failure(self, mock_ssh_client):
#         """Test failed SSH command execution"""
#         # Mock command failure
#         mock_stdout = Mock()
#         mock_stdout.channel.recv_exit_status.return_value = 1
#         mock_stderr = Mock()
#         mock_stderr.read.return_value = b"command failed"
        
#         mock_ssh_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)
        
#         result = run_ssh_command(mock_ssh_client, "false")
#         assert result is False
    
#     def test_run_ssh_command_with_output(self, mock_ssh_client):
#         """Test SSH command with output capture"""
#         stdout, stderr, exit_code = run_ssh_command(mock_ssh_client, "echo 'test'", return_output=True)
#         assert stdout == "success"
#         assert stderr == ""
#         assert exit_code == 0

# class TestLogging:
#     """Test logging utility functions"""
    
#     @patch('builtins.print')
#     def test_log_message(self, mock_print):
#         """Test log message function"""
#         log_message("test message")
#         mock_print.assert_called_once()
#         args = mock_print.call_args[0][0]
#         assert "test message" in args
#         assert "[INFO]" in args
    
#     @patch('builtins.print')
#     def test_log_error(self, mock_print):
#         """Test log error function"""
#         log_error("test error")
#         mock_print.assert_called_once()
#         args = mock_print.call_args[0][0]
#         assert "test error" in args
#         assert "[ERROR]" in args