import pytest
import tempfile
import os
import yaml
from unittest.mock import Mock, MagicMock
import paramiko


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests requiring external services"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "smoke: marks tests as smoke tests for quick validation"
    )
    config.addinivalue_line(
        "markers", "gpu: marks tests that require GPU hardware"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests that measure performance"
    )
    config.addinivalue_line(
        "markers", "security: marks tests related to security validation"
    )

@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
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