from .base_handler import BaseDistributionHandler
from ..utils import log_message, log_error, log_success, log_debug, log_warning, run_ssh_command
from ..airgap.bundle_manager import BundleManager
import tempfile
import os

class AirgappedRKE2Handler(BaseDistributionHandler):
    """Handler for RKE2 in airgapped environments"""
    
    def __init__(self):
        self.bundle_manager = None

    def generate_config_files(self, config, node_type, is_first_server=False):
        """Generate RKE2 configuration files"""
        if node_type == 'server':
            return self.generate_server_config(config, is_first_server)
        else:
            return self.generate_agent_config(config)
    
    def validate_requirements(self, config):
        """Validate RKE2 airgapped requirements"""
        rke2_config = config['deployment'].get('rke2', {})
        
        required_bundles = [
            'airgap_bundle_path'
            # 'images_bundle_path',
            # 'install_script_path'
        ]
        
        for bundle in required_bundles:
            if bundle not in rke2_config:
                log_error(f"Missing required RKE2 bundle: {bundle}")
                return False
            
            path = rke2_config[bundle]
            if not os.path.exists(path):
                log_error(f"Bundle not found: {path}")
                return False
        
        # Initialize bundle manager
        self.bundle_manager = BundleManager(config)
        return True
    
    def prepare_server_node(self, ssh_client, config, is_first_server=False):
        """Prepare RKE2 server node in airgapped environment"""
        log_message("Preparing RKE2 server node (airgapped)...")
        
        # Stage bundles first
        node = self._get_current_node(ssh_client, config)
        if not self.bundle_manager.stage_bundles_to_node(ssh_client, node, 'server'):
            return False
        
        # Create directories with sudo
        directories = [
            "/etc/rancher/rke2",
            "/var/lib/rancher/rke2/server/manifests",
            "/var/lib/rancher/rke2/agent/images"
        ]
        
        for directory in directories:
            cmd = f"sudo mkdir -p {directory}"
            if not run_ssh_command(ssh_client, cmd):
                return False
        
        # Generate and upload config
        config_content = self.generate_server_config(config, is_first_server)
        return self._upload_config_file(ssh_client, config_content, '/etc/rancher/rke2/config.yaml')
    
    def prepare_agent_node(self, ssh_client, config):
        """Prepare RKE2 agent node in airgapped environment"""
        log_message("Preparing RKE2 agent node (airgapped)...")
        
        # Stage bundles first
        node = self._get_current_node(ssh_client, config)
        if not self.bundle_manager.stage_bundles_to_node(ssh_client, node, 'agent'):
            return False
        
        # Create directories with sudo
        directories = [
            "/etc/rancher/rke2",
            "/var/lib/rancher/rke2/agent/images"
        ]
        
        for directory in directories:
            cmd = f"sudo mkdir -p {directory}"
            if not run_ssh_command(ssh_client, cmd):
                return False
        
        # Generate and upload config
        config_content = self.generate_agent_config(config)
        return self._upload_config_file(ssh_client, config_content, '/etc/rancher/rke2/config.yaml')
    
    def install_distribution(self, ssh_client, config, node_type):
        """Install RKE2 in airgapped environment"""
        log_message(f"Installing RKE2 {node_type} (airgapped)...")
        
        node = self._get_current_node(ssh_client, config)
        staging_paths = node.get('staging_paths', {})
        bundles_path = staging_paths.get('bundles', '/tmp/k8s-bundles')
        
        # Load container images first
        if config['deployment']['k8s_distribution'] != 'rke2':
            if not self._load_container_images(ssh_client, config, bundles_path):
                return False
        
        # Extract and install RKE2 from airgap bundle
        if not self._install_rke2_airgapped(ssh_client, config, bundles_path, node_type):
            return False
        
        return True
    
    def _load_container_images(self, ssh_client, config, bundles_path):
        """Load container images into local container runtime"""
        log_message("Loading container images...")
        
        rke2_config = config['deployment']['rke2']
        images_bundle = f"{bundles_path}/rke2-images.tar.gz"
        
        # Check if we have containerd or docker available
        runtime_check_cmd = "which containerd || which docker"
        stdout, stderr, exit_code = run_ssh_command(ssh_client, runtime_check_cmd, return_output=True)
        
        if exit_code != 0:
            log_error("No container runtime found for loading images")
            return False
        
        # Load images based on available runtime
        if "containerd" in stdout:
            load_cmd = f"sudo ctr -n k8s.io image import {images_bundle}"
        else:
            load_cmd = f"sudo docker load < {images_bundle}"
        
        if not run_ssh_command(ssh_client, load_cmd):
            log_error("Failed to load container images")
            return False
        
        return True
    
    def _install_rke2_airgapped(self, ssh_client, config, bundles_path, node_type):
        """Install RKE2 from airgap bundle"""
        log_message("Installing RKE2 from airgap bundle...")
        
        # Extract airgap bundle
        airgap_bundle = f"{bundles_path}/rke2-airgap-bundle.tar.gz"
        print(airgap_bundle)
        extract_cmd = f"cd /tmp && sudo tar -xzf {airgap_bundle}"
        
        if not run_ssh_command(ssh_client, extract_cmd):
            log_error("Failed to extract RKE2 airgap bundle")
            return False
        
        install_cmds = [
            f"ls -la /tmp/rke2-airgap-bundle",
            f"echo {config[]}"

        ]

        for cmd in install_cmds:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to install RKE2: {cmd}")
                return False
            else: 
                log_debug(f"Test")
        
        # # Make install script executable and run it
        # install_script = f"{bundles_path}/install.sh"
        # install_commands = [
        #     f"chmod +x {install_script}",
        #     f"sudo INSTALL_RKE2_TYPE='{node_type}' INSTALL_RKE2_METHOD='tar' sh {install_script}"
        # ]
        
        # for cmd in install_commands:
        #     if not run_ssh_command(ssh_client, cmd):
        #         log_error(f"Failed to install RKE2: {cmd}")
        #         return False
        
        return True
    
    def start_services(self, ssh_client, node_type):
        """Start RKE2 services"""
        log_message("Starting RKE2 services...")
        
        service_name = f"rke2-{node_type}"
        commands = [
            f"sudo systemctl enable {service_name}",
            f"sudo systemctl start {service_name}",
            f"sudo systemctl status {service_name}"  # Check status
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to start service: {cmd}")
                return False
        
        # For server nodes, wait for kubeconfig and set up kubectl access
        if node_type == 'server':
            return self._setup_kubectl_access(ssh_client)
        
        return True
    
    def _setup_kubectl_access(self, ssh_client):
        """Set up kubectl access for non-root user"""
        log_message("Setting up kubectl access...")
        
        # Wait for kubeconfig to be generated
        wait_cmd = "sudo timeout 300 bash -c 'until [ -f /etc/rancher/rke2/rke2.yaml ]; do sleep 5; done'"
        if not run_ssh_command(ssh_client, wait_cmd):
            log_error("Timeout waiting for kubeconfig")
            return False
        
        # Copy kubeconfig to user directory and fix permissions
        setup_commands = [
            "mkdir -p ~/.kube",
            "sudo cp /etc/rancher/rke2/rke2.yaml ~/.kube/config",
            "sudo chown $(id -u):$(id -g) ~/.kube/config",
            "chmod 600 ~/.kube/config",
            # Add RKE2 binary to PATH
            "echo 'export PATH=$PATH:/var/lib/rancher/rke2/bin' >> ~/.bashrc",
            "export PATH=$PATH:/var/lib/rancher/rke2/bin"
        ]
        
        for cmd in setup_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_warning(f"Non-critical setup command failed: {cmd}")
        
        return True
    
    def generate_server_config(self, config, is_first_server):
        """Generate RKE2 server configuration for airgapped environment"""
        cluster_config = config['cluster']
        airgap_config = config['deployment']['airgap']
        
        config_lines = [
            f"cluster-cidr: {cluster_config['cluster_cidr']}",
            f"service-cidr: {cluster_config['service_cidr']}",
            f"write-kubeconfig-mode: \"{cluster_config['write_kubeconfig_mode']}\"",
        ]
        
        # Add registry configuration for airgapped environment
        if airgap_config.get('enabled'):
            config_lines.extend([
                "system-default-registry: " + airgap_config['local_registry'],
            ])
        
        if not is_first_server:
            first_server_ip = config['nodes']['servers'][0]['ip']
            config_lines.extend([
                f"server: https://{first_server_ip}:9345",
                f"token: {cluster_config['token']}",
            ])
        else:
            config_lines.append(f"token: {cluster_config['token']}")
        
        # Add CNI configuration
        if 'cni' in cluster_config:
            cni_list = ', '.join(f'"{cni}"' for cni in cluster_config['cni'])
            config_lines.append(f"cni: [{cni_list}]")
        
        # Add disable configuration
        if 'disable' in cluster_config:
            for item in cluster_config['disable']:
                config_lines.append(f"disable: {item}")
        
        return '\n'.join(config_lines)
    
    def generate_agent_config(self, config):
        """Generate RKE2 agent configuration for airgapped environment"""
        cluster_config = config['cluster']
        airgap_config = config['deployment']['airgap']
        first_server_ip = config['nodes']['servers'][0]['ip']
        
        config_lines = [
            f"server: https://{first_server_ip}:9345",
            f"token: {cluster_config['token']}",
        ]
        
        # Add registry configuration for airgapped environment
        if airgap_config.get('enabled'):
            config_lines.append("system-default-registry: " + airgap_config['local_registry'])
        
        return '\n'.join(config_lines)
    
    def _get_current_node(self, ssh_client, config):
        """Get current node info from config based on SSH connection"""
        # This is a helper method - in practice you'd track which node you're deploying to
        # For now, return the first server as an example
        return config['nodes']['servers'][0]
    
    def _upload_config_file(self, ssh_client, content, remote_path):
        """Upload configuration file using sudo for permissions"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            # Upload to tmp location first
            temp_remote_path = f"/tmp/{os.path.basename(remote_path)}"
            sftp = ssh_client.open_sftp()
            sftp.put(tmp_file_path, temp_remote_path)
            sftp.close()
            
            # Move to final location with sudo
            move_cmd = f"sudo mv {temp_remote_path} {remote_path}"
            if not run_ssh_command(ssh_client, move_cmd):
                return False
            
            # Set proper permissions
            chmod_cmd = f"sudo chmod 644 {remote_path}"
            run_ssh_command(ssh_client, chmod_cmd)
            
            os.unlink(tmp_file_path)
            return True
            
        except Exception as e:
            log_error(f"Failed to upload config file: {e}")
            return False
    
    def health_check(self, ssh_client, node):
        """Perform RKE2 health check in airgapped environment"""
        log_message(f"Performing health check on {node['hostname']}...")
        
        check_commands = [
            "sudo systemctl is-active rke2-server || sudo systemctl is-active rke2-agent",
            "export PATH=$PATH:/var/lib/rancher/rke2/bin && kubectl get nodes --kubeconfig ~/.kube/config || true",
            "export PATH=$PATH:/var/lib/rancher/rke2/bin && kubectl get pods -A --kubeconfig ~/.kube/config || true"
        ]
        
        for cmd in check_commands:
            stdout, stderr, exit_code = run_ssh_command(ssh_client, cmd, return_output=True)
            if exit_code != 0 and "|| true" not in cmd:
                log_error(f"Health check failed: {stderr}")
                return False
            elif stdout:
                log_message(f"Health check output: {stdout}")
        
        return True
    
    def uninstall(self, ssh_client, node_type):
        """Uninstall RKE2 in airgapped environment"""
        log_message(f"Uninstalling RKE2 {node_type}...")
        
        service_name = f"rke2-{node_type}"
        commands = [
            f"sudo systemctl stop {service_name}",
            f"sudo systemctl disable {service_name}",
            "sudo sh /usr/local/bin/rke2-uninstall.sh || true",
            "sudo rm -rf /etc/rancher/rke2",
            "sudo rm -rf /var/lib/rancher/rke2",
            "rm -rf ~/.kube"  # Clean up user kubectl config
        ]
        
        for cmd in commands:
            run_ssh_command(ssh_client, cmd)  # Don't fail on errors during cleanup
        
        return True 