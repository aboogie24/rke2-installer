# deploy/distributions/rke2_handler.py
from .base_handler import BaseDistributionHandler
from ..utils import log_message, log_error, log_success, run_ssh_command
import tempfile
import os

class RKE2Handler(BaseDistributionHandler):
    """Handler for RKE2 Kubernetes distribution"""
    
    def validate_requirements(self, config):
        """Validate RKE2-specific requirements"""
        rke2_config = config['deployment'].get('rke2', {})
        
        required_fields = ['version', 'airgap_bundle_path']
        for field in required_fields:
            if field not in rke2_config:
                log_error(f"Missing required RKE2 configuration: {field}")
                return False
        
        # Check if airgap bundle exists
        bundle_path = rke2_config['airgap_bundle_path']
        if not os.path.exists(bundle_path):
            log_error(f"RKE2 airgap bundle not found: {bundle_path}")
            return False
        
        return True
    
    def prepare_server_node(self, ssh_client, config, is_first_server=False):
        """Prepare RKE2 server node"""
        log_message("Preparing RKE2 server node...")
        
        # Create directories
        commands = [
            "mkdir -p /etc/rancher/rke2",
            "mkdir -p /var/lib/rancher/rke2/server/manifests",
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                return False
        
        # Generate and upload config
        config_content = self.generate_server_config(config, is_first_server)
        return self._upload_config_file(ssh_client, config_content, '/etc/rancher/rke2/config.yaml')
    
    def prepare_agent_node(self, ssh_client, config):
        """Prepare RKE2 agent node"""
        log_message("Preparing RKE2 agent node...")
        
        # Create directories
        commands = [
            "mkdir -p /etc/rancher/rke2",
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                return False
        
        # Generate and upload config
        config_content = self.generate_agent_config(config)
        return self._upload_config_file(ssh_client, config_content, '/etc/rancher/rke2/config.yaml')
    
    def generate_config_files(self, config, node_type, is_first_server=False):
        """Generate RKE2 configuration files"""
        if node_type == 'server':
            return self.generate_server_config(config, is_first_server)
        else:
            return self.generate_agent_config(config)
    
    def generate_server_config(self, config, is_first_server):
        """Generate RKE2 server configuration"""
        cluster_config = config['cluster']
        rke2_config = config['deployment']['rke2']
        
        config_lines = [
            f"cluster-cidr: {cluster_config['cluster_cidr']}",
            f"service-cidr: {cluster_config['service_cidr']}",
            f"write-kubeconfig-mode: \"{cluster_config['write_kubeconfig_mode']}\"",
        ]
        
        if not is_first_server:
            # For joining servers, add the server URL and token
            first_server_ip = config['nodes']['servers'][0]['ip']
            config_lines.extend([
                f"server: https://{first_server_ip}:9345",
                f"token: {cluster_config['token']}",
            ])
        else:
            # For first server, set the token
            config_lines.append(f"token: {cluster_config['token']}")
        
        # Add CNI configuration
        if 'cni' in cluster_config:
            config_lines.append(f"cni: {cluster_config['cni']}")
        
        # Add disable configuration
        if 'disable' in cluster_config:
            for item in cluster_config['disable']:
                config_lines.append(f"disable: {item}")
        
        return '\n'.join(config_lines)
    
    def generate_agent_config(self, config):
        """Generate RKE2 agent configuration"""
        cluster_config = config['cluster']
        first_server_ip = config['nodes']['servers'][0]['ip']
        
        config_lines = [
            f"server: https://{first_server_ip}:9345",
            f"token: {cluster_config['token']}",
        ]
        
        return '\n'.join(config_lines)
    
    def install_distribution(self, ssh_client, config, node_type):
        """Install RKE2"""
        log_message(f"Installing RKE2 {node_type}...")
        
        rke2_config = config['deployment']['rke2']
        
        # Upload and extract airgap bundle
        if not self._upload_airgap_bundle(ssh_client, rke2_config):
            return False
        
        # Install RKE2
        install_script = f"INSTALL_RKE2_TYPE='{node_type}' sh /opt/rke2/install.sh"
        if not run_ssh_command(ssh_client, install_script):
            return False
        
        return True
    
    def start_services(self, ssh_client, node_type):
        """Start RKE2 services"""
        service_name = f"rke2-{node_type}"
        commands = [
            f"systemctl enable {service_name}",
            f"systemctl start {service_name}",
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                return False
        
        return True
    
    def health_check(self, ssh_client, node):
        """Perform RKE2 health check"""
        log_message(f"Performing health check on {node['hostname']}...")
        
        # Check if RKE2 service is running
        check_commands = [
            "systemctl is-active rke2-server || systemctl is-active rke2-agent",
            "kubectl get nodes --kubeconfig /etc/rancher/rke2/rke2.yaml || true",
        ]
        
        for cmd in check_commands:
            stdout, stderr, exit_code = run_ssh_command(ssh_client, cmd, return_output=True)
            if exit_code != 0 and "|| true" not in cmd:
                log_error(f"Health check failed: {stderr}")
                return False
        
        return True
    
    def uninstall(self, ssh_client, node_type):
        """Uninstall RKE2"""
        log_message(f"Uninstalling RKE2 {node_type}...")
        
        service_name = f"rke2-{node_type}"
        commands = [
            f"systemctl stop {service_name}",
            f"systemctl disable {service_name}",
            "sh /usr/local/bin/rke2-uninstall.sh || true",
            "rm -rf /etc/rancher/rke2",
            "rm -rf /var/lib/rancher/rke2",
        ]
        
        for cmd in commands:
            run_ssh_command(ssh_client, cmd)  # Don't fail on errors during cleanup
        
        return True
    
    def _upload_config_file(self, ssh_client, content, remote_path):
        """Upload configuration file to remote node"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            sftp = ssh_client.open_sftp()
            sftp.put(tmp_file_path, remote_path)
            sftp.close()
            
            os.unlink(tmp_file_path)
            return True
            
        except Exception as e:
            log_error(f"Failed to upload config file: {e}")
            return False
    
    def _upload_airgap_bundle(self, ssh_client, rke2_config):
        """Upload and extract RKE2 airgap bundle"""
        try:
            bundle_path = rke2_config['airgap_bundle_path']
            remote_bundle_path = "/tmp/rke2-airgap-bundle.tar.gz"
            
            log_message("Uploading RKE2 airgap bundle...")
            sftp = ssh_client.open_sftp()
            sftp.put(bundle_path, remote_bundle_path)
            sftp.close()
            
            # Extract bundle
            extract_cmd = f"cd /opt && tar -xzf {remote_bundle_path}"
            if not run_ssh_command(ssh_client, extract_cmd):
                return False
            
            # Cleanup
            run_ssh_command(ssh_client, f"rm -f {remote_bundle_path}")
            return True
            
        except Exception as e:
            log_error(f"Failed to upload airgap bundle: {e}")
            return False