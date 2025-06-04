import pytest
import tempfile
import os
import yaml
from .mock_helpers import MockBundleEnvironment, create_test_config

@pytest.fixture
def temp_dir():
    """Temporary directory fixture"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    import shutil
    shutil.rmtree(temp_path)

@pytest.fixture
def bundle_environment():
    """Bundle environment fixture"""
    bundle_env = MockBundleEnvironment()
    bundle_env.create_rke2_bundles()
    yield bundle_env
    bundle_env.cleanup()

@pytest.fixture
def test_config_file(bundle_environment):
    """Test configuration file fixture"""
    config = create_test_config(bundle_environment)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config, f)
        config_file = f.name
    
    yield config_file
    os.unlink(config_file)

@pytest.fixture
def ssh_key_file(temp_dir):
    """SSH key file fixture"""
    key_path = os.path.join(temp_dir, 'test_key')
    with open(key_path, 'w') as f:
        f.write("-----BEGIN OPENSSH PRIVATE KEY-----\nMOCK_KEY_CONTENT\n-----END OPENSSH PRIVATE KEY-----")
    os.chmod(key_path, 0o600)
    yield key_path