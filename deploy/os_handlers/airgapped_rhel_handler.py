from .base_handler import BaseOSHandler
from ..utils import log_message, log_error, log_warning, run_ssh_command
import os


""" 
This handler is designed to setup nodes running 
RHEL/CENTOS 

Notes:  Commands may need some adjusting to run on STIG'd 
        Machines. Using /opt directory should work as it 

Possible solution: 'echo <Non root Pass> | sudo -S <command>' 

"""

class AirgappedRHELHandler(BaseOSHandler):
    """Handler for RHEL in airgapped environments with non-root user"""
    
    def install_base_packages(self, ssh_client, node, packages=None):
        """Install base packages from local bundle"""
        log_message(node, "Installing base packages for RHEL (airgapped)...")
        
        # Check if we have a package bundle to work with
        bundle_path = "/tmp/k8s-bundles/rhel8-packages.tar.gz"
        if not self._check_remote_file_exists(ssh_client, bundle_path):
            log_warning("No package bundle found, assuming packages are pre-installed")
            return True
        
        # Extract and install packages from bundle
        # Will need to update this in the future
        extract_commands = [
            f"cd /tmp && tar -xzf {bundle_path}",
            "cd /tmp/rhel8-packages && sudo dnf install -y *.rpm --nogpgcheck"
        ]
        
        for cmd in extract_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to install packages: {cmd}")
                return False
        
        return True
    
    def install_container_runtime(self, ssh_client, runtime='containerd'):
        """Install containerd from local packages"""
        log_message(f"Installing {runtime} container runtime (airgapped)...")
        
        if runtime == 'containerd':
            # Try to install from bundle first, fall back to pre-installed
            bundle_commands = [
                "cd /tmp/rhel8-packages && sudo dnf install -y containerd*.rpm --nogpgcheck || sudo dnf install -y containerd",
                "sudo mkdir -p /etc/containerd",
                "sudo containerd config default | sudo tee /etc/containerd/config.toml",
                "sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml",
                "sudo systemctl enable containerd",
                "sudo systemctl start containerd"
            ]
        elif runtime == 'crio':
            bundle_commands = [
                "cd /tmp/rhel8-packages && sudo dnf install -y cri-o*.rpm --nogpgcheck || sudo dnf install -y cri-o",
                "sudo systemctl enable crio",
                "sudo systemctl start crio"
            ]
        else:
            log_error(f"Unsupported container runtime: {runtime}")
            return False
        
        for cmd in bundle_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to execute: {cmd}")
                return False
        
        return True
    
    def configure_firewall(self, ssh_client, node_type, node):
        """Configure firewall with sudo privileges"""
        log_message("Configuring firewall (airgapped)...")
        
        # Check if firewalld is running
        stdout, stderr, exit_code = run_ssh_command(ssh_client, 
            "sudo systemctl is-active firewalld", return_output=True)
        
        if exit_code != 0:
            log_message(node,"Firewalld is not running, skipping firewall configuration")
            return True
        
        firewall_commands = []
        
        if node_type == 'server':
            server_ports = [
                "6443/tcp",    # Kubernetes API server
                "2379-2380/tcp", # etcd server client API
                "10250/tcp",   # Kubelet API
                "10251/tcp",   # kube-scheduler
                "10252/tcp",   # kube-controller-manager
                "9345/tcp",    # RKE2 supervisor API
            ]
            
            for port in server_ports:
                firewall_commands.append(f"sudo firewall-cmd --permanent --add-port={port}")
        
        # Common ports for all nodes
        common_ports = [
            "10250/tcp",     # Kubelet API
            "30000-32767/tcp", # NodePort Services
        ]
        
        for port in common_ports:
            firewall_commands.append(f"sudo firewall-cmd --permanent --add-port={port}")
        
        # Reload firewall
        firewall_commands.append("sudo firewall-cmd --reload")
        
        for cmd in firewall_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(node, f"Failed to configure firewall: {cmd}")
                return False
        
        return True
    
    def configure_selinux(self, ssh_client, node):
        """Configure SELinux with sudo privileges"""
        log_message(node, "Configuring SELinux (airgapped)...")
        
        commands = [
            "sudo setenforce 0",
            "sudo sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(node, f"Failed to configure SELinux: {cmd}")
                return False
        
        return True
    
    def install_gpu_packages(self, ssh_client, packages=None):
        """Install GPU packages from local bundle"""
        log_message("Installing GPU packages (airgapped)...")
        
        gpu_bundle_path = "/tmp/k8s-bundles/nvidia-packages-rhel8.tar.gz"
        if not self._check_remote_file_exists(ssh_client, gpu_bundle_path):
            log_error("GPU package bundle not found")
            return False
        
        # Extract and install GPU packages
        gpu_commands = [
            f"cd /tmp && tar -xzf {gpu_bundle_path}",
            "cd /tmp/nvidia-packages && sudo dnf install -y *.rpm --nogpgcheck",
            "sudo nvidia-ctk runtime configure --runtime=containerd",
            "sudo systemctl restart containerd"
        ]
        
        for cmd in gpu_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to install GPU packages: {cmd}")
                return False
        
        return True
    
    def setup_kubernetes_repo(self, ssh_client):
        """In airgapped environment, we don't need external repos"""
        log_message("Skipping Kubernetes repository setup (airgapped environment)")
        return True
    
    def disable_swap(self, ssh_client, node):
        """Disable swap with sudo privileges"""
        log_message(node, "Disabling swap...")
        
        commands = [
            "sudo swapoff -a",
            "sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to disable swap: {cmd}")
                return False
        
        return True
    
    def configure_kernel_modules(self, ssh_client, node):
        """Load required kernel modules with sudo"""
        log_message("Configuring kernel modules...")
        
        modules = ['br_netfilter', 'overlay']
        
        # Load modules immediately
        for module in modules:
            if not run_ssh_command(ssh_client, f"sudo modprobe {module}"):
                log_error(node, f"Failed to load module: {module}")
                return False
        
        # Make modules persistent
        # This command may not working in STIG'd airgapped environments
        modules_content = '\n'.join(modules)
        create_modules_cmd = f"echo '{modules_content}' | sudo tee /etc/modules-load.d/k8s.conf"
        
        if not run_ssh_command(ssh_client, create_modules_cmd):
            log_error(node, "Failed to create kernel modules configuration")
            return False
        
        # This should be updated
        # Configure sysctl
        sysctl_content = """net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1"""
        
        create_sysctl_cmd = f"echo '{sysctl_content}' | sudo tee /etc/sysctl.d/k8s.conf"
        
        if not run_ssh_command(ssh_client, create_sysctl_cmd):
            log_error(node, "Failed to create sysctl configuration")
            return False
        
        # Apply sysctl settings
        if not run_ssh_command(ssh_client, "sudo sysctl --system"):
            log_error(node, "Failed to apply sysctl settings")
            return False
        
        return True
    
    def get_package_manager(self):
        """Return the package manager for RHEL"""
        return "dnf"
    
    def _check_remote_file_exists(self, ssh_client, file_path):
        """Check if a file exists on the remote system"""
        stdout, stderr, exit_code = run_ssh_command(ssh_client, 
            f"test -f {file_path} && echo 'exists'", return_output=True)
        return exit_code == 0 and 'exists' in stdout