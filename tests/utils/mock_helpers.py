import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager
import paramiko

class MockSSHClient:
    """Enhanced mock SSH client for testing"""
    
    def __init__(self, success=True, command_outputs=None):
        self.success = success
        self.command_outputs = command_outputs or {}
        self.commands_executed = []
        self.connected = False
        self.connection_params = {}
    
    def connect(self, **kwargs):
        """Mock SSH connection"""
        self.connected = True
        self.connection_params = kwargs
        if not self.success:
            raise paramiko.AuthenticationException("Mock auth failure")
    
    def exec_command(self, command, timeout=300):
        """Mock command execution"""
        self.commands_executed.append(command)
        
        # Return mock stdin, stdout, stderr
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        # Configure stdout
        if command in self.command_outputs:
            output, exit_code = self.command_outputs[command]
            mock_stdout.read.return_value = output.encode() if isinstance(output, str) else output
            mock_stdout.channel.recv_exit_status.return_value = exit_code
        else:
            mock_stdout.read.return_value = b"success"
            mock_stdout.channel.recv_exit_status.return_value = 0 if self.success else 1
        
        # Configure stderr
        mock_stderr.read.return_value = b"" if self.success else b"error"
        
        return mock_stdin, mock_stdout, mock_stderr
    
    def open_sftp(self):
        """Mock SFTP client"""
        mock_sftp = Mock()
        mock_sftp.put = Mock()
        mock_sftp.get = Mock()
        mock_sftp.close = Mock()
        return mock_sftp
    
    def close(self):
        """Mock close connection"""
        self.connected = False
    
    def set_missing_host_key_policy(self, policy):
        """Mock host key policy"""
        pass

class MockBundleEnvironment:
    """Mock bundle environment for testing"""
    
    def __init__(self, base_path=None):
        self.base_path = base_path or tempfile.mkdtemp()
        self.bundle_paths = {}
    
    def create_bundle(self, name, content=b"mock bundle content"):
        """Create a mock bundle file"""
        bundle_path = os.path.join(self.base_path, name)
        os.makedirs(os.path.dirname(bundle_path), exist_ok=True)
        
        with open(bundle_path, 'wb') as f:
            f.write(content)
        
        self.bundle_paths[name] = bundle_path
        return bundle_path
    
    def create_rke2_bundles(self):
        """Create standard RKE2 bundles"""
        bundles = {
            'rke2-airgap-bundle.tar.gz': b"mock rke2 airgap bundle",
            'rke2-images.tar.gz': b"mock rke2 images",
            'install.sh': b"#!/bin/bash\necho 'mock install script'",
            'rhel8-packages.tar.gz': b"mock rhel packages"
        }
        
        for name, content in bundles.items():
            self.create_bundle(name, content)
        
        return self.bundle_paths
    
    def cleanup(self):
        """Clean up mock environment"""
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)

@contextmanager
def mock_ssh_environment(success=True, command_outputs=None):
    """Context manager for mock SSH environment"""
    with patch('paramiko.SSHClient') as mock_ssh_class:
        mock_ssh = MockSSHClient(success, command_outputs)
        mock_ssh_class.return_value = mock_ssh
        yield mock_ssh

@contextmanager
def mock_bundle_environment():
    """Context manager for mock bundle environment"""
    bundle_env = MockBundleEnvironment()
    try:
        bundle_env.create_rke2_bundles()
        yield bundle_env
    finally:
        bundle_env.cleanup()

def create_test_config(bundle_env=None, **overrides):
    """Create a test configuration with optional overrides"""
    base_config = {
        'deployment': {
            'k8s_distribution': 'rke2',
            'os': {'type': 'rhel', 'version': '8'},
            'airgap': {
                'enabled': True,
                'local_registry': 'localhost:5000',
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
        'extra_tools': ['k9s']
    }
    
    # Update with bundle paths if bundle environment provided
    if bundle_env:
        base_config['deployment']['rke2']['airgap_bundle_path'] = bundle_env.bundle_paths.get('rke2-airgap-bundle.tar.gz')
        base_config['deployment']['rke2']['images_bundle_path'] = bundle_env.bundle_paths.get('rke2-images.tar.gz')
        base_config['deployment']['rke2']['install_script_path'] = bundle_env.bundle_paths.get('install.sh')
    
    # Apply overrides
    def deep_update(base_dict, update_dict):
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    deep_update(base_config, overrides)
    return base_config