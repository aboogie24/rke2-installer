# deploy/distributions/eks_anywhere_handler.py
from .base_handler import BaseDistributionHandler
from ..utils import log_message, log_error, log_success, run_ssh_command
import tempfile
import os
import yaml

class EKSAnywhereHandler(BaseDistributionHandler):
    """Handler for EKS Anywhere Kubernetes distribution"""
    
    def validate_requirements(self, config):
        """Validate EKS Anywhere specific requirements"""
        eks_config = config['deployment'].get('eks_anywhere', {})
        
        required_fields = ['version', 'bundle_manifest_url']
        for field in required_fields:
            if field not in eks_config:
                log_error(f"Missing required EKS Anywhere configuration: {field}")
                return False
        
        return True
    
    def prepare_server_node(self, ssh_client, config, is_first_server=False):
        """Prepare EKS Anywhere admin node (only first server acts as admin)"""
        if not is_first_server:
            log_message("EKS Anywhere: Additional servers will be managed by the admin node")
            return True
            
        log_message("Preparing EKS Anywhere admin node...")
        
        # Create directories
        commands = [
            "mkdir -p /opt/eks-anywhere",
            "mkdir -p ~/.eks-anywhere",
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                return False
        
        # Generate cluster specification
        cluster_spec = self.generate_cluster_spec(config)
        return self._upload_config_file(ssh_client, cluster_spec, '/opt/eks-anywhere/cluster.yaml')
    
    def prepare_agent_node(self, ssh_client, config):
        """EKS Anywhere manages agent nodes automatically"""
        log_message("EKS Anywhere will automatically configure this node during cluster creation")
        return True
    
    def generate_config_files(self, config, node_type, is_first_server=False):
        """Generate EKS Anywhere cluster specification"""
        if node_type == 'server' and is_first_server:
            return self.generate_cluster_spec(config)
        return ""
    
    def generate_cluster_spec(self, config):
        """Generate EKS Anywhere cluster specification"""
        cluster_config = config['cluster']
        eks_config = config['deployment']['eks_anywhere']
        
        # Build node list
        control_plane_nodes = []
        worker_nodes = []
        
        for i, node in enumerate(config['nodes']['servers']):
            control_plane_nodes.append({
                'name': node['hostname'],
                'ip': node['ip']
            })
        
        for node in config['nodes']['agents']:
            worker_nodes.append({
                'name': node['hostname'], 
                'ip': node['ip']
            })
        
        cluster_spec = {
            'apiVersion': 'anywhere.eks.amazonaws.com/v1alpha1',
            'kind': 'Cluster',
            'metadata': {
                'name': cluster_config['name'],
                'namespace': 'default'
            },
            'spec': {
                'kubernetesVersion': eks_config['version'],
                'clusterNetwork': {
                    'cniConfig': {
                        'cilium': {}
                    },
                    'pods': {
                        'cidrBlocks': [cluster_config['cluster_cidr']]
                    },
                    'services': {
                        'cidrBlocks': [cluster_config['service_cidr']]
                    }
                },
                'controlPlaneConfiguration': {
                    'count': len(control_plane_nodes),
                    'endpoint': {
                        'host': config['nodes']['servers'][0]['ip']
                    },
                    'machineGroupRef': {
                        'kind': 'VSphereMachineConfig',
                        'name': 'control-plane-machine-config'
                    }
                },
                'workerNodeGroupConfigurations': [{
                    'count': len(worker_nodes),
                    'machineGroupRef': {
                        'kind': 'VSphereMachineConfig', 
                        'name': 'worker-machine-config'
                    },
                    'name': 'worker-nodes'
                }],
                'datacenterRef': {
                    'kind': 'VSphereDatacenterConfig',
                    'name': 'datacenter-config'
                }
            }
        }
        
        # Add machine configs (simplified - would need more details for real deployment)
        machine_configs = [
            {
                'apiVersion': 'anywhere.eks.amazonaws.com/v1alpha1',
                'kind': 'VSphereMachineConfig',
                'metadata': {
                    'name': 'control-plane-machine-config'
                },
                'spec': {
                    'diskGiB': 25,
                    'memoryMiB': 8192,
                    'numCPUs': 2,
                    'osFamily': 'ubuntu',
                    'users': [{
                        'name': 'capv',
                        'sshAuthorizedKeys': ['ssh-key-content-here']
                    }]
                }
            },
            {
                'apiVersion': 'anywhere.eks.amazonaws.com/v1alpha1',
                'kind': 'VSphereMachineConfig', 
                'metadata': {
                    'name': 'worker-machine-config'
                },
                'spec': {
                    'diskGiB': 25,
                    'memoryMiB': 4096,
                    'numCPUs': 2,
                    'osFamily': 'ubuntu',
                    'users': [{
                        'name': 'capv',
                        'sshAuthorizedKeys': ['ssh-key-content-here']
                    }]
                }
            }
        ]
        
        # Combine all configs
        all_configs = [cluster_spec] + machine_configs
        
        return '---\n'.join([yaml.dump(config, default_flow_style=False) for config in all_configs])
    
    def install_distribution(self, ssh_client, config, node_type):
        """Install EKS Anywhere CLI and create cluster"""
        if node_type != 'server':
            log_message("EKS Anywhere installation only needed on admin node")
            return True
            
        log_message("Installing EKS Anywhere CLI...")
        
        eks_config = config['deployment']['eks_anywhere']
        
        # Download and install eksctl-anywhere
        install_commands = [
            f"curl 'https://github.com/aws/eks-anywhere/releases/download/{eks_config['version']}/eksctl-anywhere-linux-amd64.tar.gz' -o /tmp/eksctl-anywhere.tar.gz",
            "tar xzf /tmp/eksctl-anywhere.tar.gz -C /tmp",
            "install -m 0755 /tmp/eksctl-anywhere /usr/local/bin/eksctl-anywhere",
            "rm -f /tmp/eksctl-anywhere.tar.gz /tmp/eksctl-anywhere"
        ]
        
        for cmd in install_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to install EKS Anywhere: {cmd}")
                return False
        
        return True
    
    def start_services(self, ssh_client, node_type):
        """Create EKS Anywhere cluster"""
        if node_type != 'server':
            return True
            
        log_message("Creating EKS Anywhere cluster...")
        
        # Create cluster using eksctl-anywhere
        create_commands = [
            "cd /opt/eks-anywhere",
            "eksctl-anywhere create cluster -f cluster.yaml"
        ]
        
        for cmd in create_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to create cluster: {cmd}")
                return False
        
        return True
    
    def health_check(self, ssh_client, node):
        """Perform EKS Anywhere health check"""
        log_message(f"Performing EKS Anywhere health check on {node['hostname']}...")
        
        check_commands = [
            "eksctl-anywhere version",
            "kubectl get nodes --kubeconfig /opt/eks-anywhere/kubeconfig || true",
            "kubectl get pods -A --kubeconfig /opt/eks-anywhere/kubeconfig || true"
        ]
        
        for cmd in check_commands:
            stdout, stderr, exit_code = run_ssh_command(ssh_client, cmd, return_output=True)
            if exit_code != 0 and "|| true" not in cmd:
                log_error(f"Health check failed: {stderr}")
                return False
            else:
                log_message(f"Health check output: {stdout}")
        
        return True
    
    def uninstall(self, ssh_client, node_type):
        """Uninstall EKS Anywhere cluster"""
        log_message("Uninstalling EKS Anywhere cluster...")
        
        if node_type == 'server':
            # Delete cluster first
            delete_commands = [
                "cd /opt/eks-anywhere",
                "eksctl-anywhere delete cluster -f cluster.yaml || true"
            ]
            
            for cmd in delete_commands:
                run_ssh_command(ssh_client, cmd)  # Don't fail on errors during cleanup
        
        # Cleanup files
        cleanup_commands = [
            "rm -rf /opt/eks-anywhere",
            "rm -rf ~/.eks-anywhere", 
            "rm -f /usr/local/bin/eksctl-anywhere"
        ]
        
        for cmd in cleanup_commands:
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