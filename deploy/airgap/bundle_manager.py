# deploy/airgap/bundle_manager.py
import os
import tarfile
import tempfile
from ..utils import log_message, log_error, log_success, run_ssh_command

class BundleManager:
    """Manages airgapped bundles and staging"""
    
    def __init__(self, config):
        self.config = config
        self.airgap_config = config['deployment']['airgap']
        
    def stage_bundles_to_node(self, ssh_client, node, node_type):
        """Stage all required bundles to a node"""
        log_message(node, f"Staging bundles to {node['hostname']}...")
        
        # Create staging directories on remote node
        staging_paths = node.get('staging_paths', {})
        bundles_path = staging_paths.get('bundles', '/tmp/k8s-bundles')
        images_path = staging_paths.get('images', '/tmp/k8s-images')
        
        # Use sudo to create directories since we're not root
        create_dirs_cmd = f"sudo mkdir -p {bundles_path} {images_path} && sudo chown {node['user']}:{node['user']} {bundles_path} {images_path}"
        if not run_ssh_command(ssh_client, create_dirs_cmd):
            return False
        
        # Upload bundles based on distribution
        dist = self.config['deployment']['k8s_distribution']
        if dist == 'rke2':
            return self._stage_rke2_bundles(ssh_client, node, bundles_path)
        elif dist == 'eks-anywhere':
            return self._stage_eks_bundles(ssh_client, node, bundles_path)
        elif dist in ['vanilla', 'kubeadm']:
            return self._stage_vanilla_bundles(ssh_client, node, bundles_path)
        elif dist == 'k3s':
            return self._stage_k3s_bundles(ssh_client, node, bundles_path)
        
        return True
    
    def _stage_rke2_bundles(self, ssh_client, node, staging_path):
        """Stage RKE2 bundles"""
        rke2_config = self.config['deployment']['rke2']
        
        bundles_to_upload = [
            ('airgap_bundle_path', 'rke2-airgap-bundle.tar.gz'),
            ('images_bundle_path', 'rke2-images.tar.gz'),
            ('rpm_bundle_path', 'rke2-rpms.tar.gz'),
            ('install_script_path', 'install.sh')
        ]
        
        for config_key, filename in bundles_to_upload:
            if config_key in rke2_config:
                local_path = rke2_config[config_key]
                remote_path = f"{staging_path}/{filename}"
                
                if not self._upload_file(ssh_client, local_path, remote_path):
                    log_error(node, f"Failed to upload {filename}")
                    return False
        
        return True
    
    def _stage_k3s_bundles(self, ssh_client, node, staging_path):
        """Stage K3s bundles"""
        k3s_config = self.config['deployment']['k3s']
        
        bundles_to_upload = [
            ('binary_path', 'k3s'),
            ('images_bundle_path', 'k3s-airgap-images.tar.gz')
        ]
        
        for config_key, filename in bundles_to_upload:
            if config_key in k3s_config:
                local_path = k3s_config[config_key]
                remote_path = f"{staging_path}/{filename}"
                
                if not self._upload_file(ssh_client, local_path, remote_path):
                    log_error(node, f"Failed to upload {filename}")
                    return False
        
        return True
    
    def _upload_file(self, ssh_client, local_path, remote_path):
        """Upload a file to the remote node"""
        try:
            if not os.path.exists(local_path):
                log_error(f"Local file not found: {local_path}")
                return False
            
            log_message(f"Uploading {os.path.basename(local_path)}...")
            sftp = ssh_client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            
            # Make executable if it's a script or binary
            if local_path.endswith(('.sh', 'k3s', 'flux', 'helm', 'k9s')):
                run_ssh_command(ssh_client, f"chmod +x {remote_path}")
            
            return True
            
        except Exception as e:
            log_error(f"Failed to upload {local_path}: {e}")
            return False

