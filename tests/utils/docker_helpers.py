import subprocess
import time
import requests
from contextlib import contextmanager

class DockerRegistry:
    """Helper for managing Docker registry in tests"""
    
    def __init__(self, port=5000):
        self.port = port
        self.container_name = f"test-registry-{port}"
        self.running = False
    
    def start(self):
        """Start Docker registry"""
        try:
            # Stop existing container if running
            subprocess.run(['docker', 'rm', '-f', self.container_name], 
                         capture_output=True)
            
            # Start new registry
            subprocess.run([
                'docker', 'run', '-d',
                '--name', self.container_name,
                '-p', f'{self.port}:5000',
                'registry:2'
            ], check=True, capture_output=True)
            
            # Wait for registry to be ready
            self._wait_for_ready()
            self.running = True
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to start registry: {e}")
    
    def stop(self):
        """Stop Docker registry"""
        if self.running:
            subprocess.run(['docker', 'rm', '-f', self.container_name], 
                         capture_output=True)
            self.running = False
    
    def _wait_for_ready(self, timeout=30):
        """Wait for registry to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{self.port}/v2/")
                if response.status_code == 200:
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise RuntimeError("Registry failed to start within timeout")
    
    @property
    def url(self):
        """Get registry URL"""
        return f"localhost:{self.port}"

@contextmanager
def docker_registry(port=5000):
    """Context manager for Docker registry"""
    registry = DockerRegistry(port)
    try:
        registry.start()
        yield registry
    finally:
        registry.stop()

def push_test_image(registry_url, image_name="test-image", tag="latest"):
    """Push a test image to registry"""
    # Create a simple test image
    dockerfile_content = """
FROM alpine:latest
RUN echo "test image" > /test.txt
CMD ["cat", "/test.txt"]
"""
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as temp_dir:
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        # Build image
        subprocess.run([
            'docker', 'build', '-t', f"{registry_url}/{image_name}:{tag}",
            temp_dir
        ], check=True, capture_output=True)
        
        # Push image
        subprocess.run([
            'docker', 'push', f"{registry_url}/{image_name}:{tag}"
        ], check=True, capture_output=True)
    
    return f"{registry_url}/{image_name}:{tag}"