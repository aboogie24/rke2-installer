from .base_handler import BaseOSHandler
from ..utils import log_message, log_error, log_success, run_ssh_command

class RHELHandler(BaseOSHandler):
    """Handler for RHEL/Rocky Linux/CentOS Stream operating systems"""
    
    def install_base_packages(self, ssh_client, packages=None):
        """Install base packages for RHEL-based systems"""
        log_message("Installing base packages for RHEL...")
        
        default_packages = [
            'container-selinux',
            'iptables',
            'libnetfilter_conntrack',
            'libnfnetlink', 
            'libnftnl',
            'libseccomp',
            'tar',
            'wget',
            'curl',
            'vim',
            'yum-utils'
        ]
        
        packages_to_install = packages or default_packages
        
        # Update system first
        if not run_ssh_command(ssh_client, "dnf update -y"):
            log_error("Failed to update system packages")
            return False
        
        # Install packages
        package_list = ' '.join(packages_to_install)
        install_cmd = f"dnf install -y {package_list}"
        
        if not run_ssh_command(ssh_client, install_cmd):
            log_error("Failed to install base packages")
            return False
        
        return True
    
    def install_container_runtime(self, ssh_client, runtime='containerd'):
        """Install containerd on RHEL"""
        log_message(f"Installing {runtime} container runtime...")
        
        if runtime == 'containerd':
            commands = [
                # Install containerd
                "dnf install -y containerd",
                
                # Generate default config
                "mkdir -p /etc/containerd",
                "containerd config default > /etc/containerd/config.toml",
                
                # Enable SystemdCgroup
                "sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml",
                
                # Enable and start containerd
                "systemctl enable containerd",
                "systemctl start containerd"
            ]
        elif runtime == 'crio':
            commands = [
                # Add CRI-O repository
                "curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable.repo https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/CentOS_8/devel:kubic:libcontainers:stable.repo",
                "curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable:cri-o:1.24.repo https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable:cri-o:1.24/CentOS_8/devel:kubic:libcontainers:stable:cri-o:1.24.repo",
                
                # Install CRI-O
                "dnf install -y cri-o",
                
                # Enable and start CRI-O
                "systemctl enable crio",
                "systemctl start crio"
            ]
        else:
            log_error(f"Unsupported container runtime: {runtime}")
            return False
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to execute: {cmd}")
                return False
        
        return True
    
    def configure_firewall(self, ssh_client, node_type):
        """Configure firewall for Kubernetes on RHEL"""
        log_message("Configuring firewall...")
        
        # Check if firewalld is running
        stdout, stderr, exit_code = run_ssh_command(ssh_client, 
            "systemctl is-active firewalld", return_output=True)
        
        if exit_code != 0:
            log_message("Firewalld is not running, skipping firewall configuration")
            return True
        
        firewall_commands = []
        
        if node_type == 'server':
            # Control plane ports
            server_ports = [
                "6443/tcp",    # Kubernetes API server
                "2379-2380/tcp", # etcd server client API
                "10250/tcp",   # Kubelet API
                "10251/tcp",   # kube-scheduler
                "10252/tcp",   # kube-controller-manager
                "9345/tcp",    # RKE2 supervisor API
            ]
            
            for port in server_ports:
                firewall_commands.append(f"firewall-cmd --permanent --add-port={port}")
        
        # Common ports for all nodes
        common_ports = [
            "10250/tcp",     # Kubelet API
            "30000-32767/tcp", # NodePort Services
        ]
        
        for port in common_ports:
            firewall_commands.append(f"firewall-cmd --permanent --add-port={port}")
        
        # Reload firewall
        firewall_commands.append("firewall-cmd --reload")
        
        for cmd in firewall_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to configure firewall: {cmd}")
                return False
        
        return True
    
    def configure_selinux(self, ssh_client):
        """Configure SELinux for Kubernetes"""
        log_message("Configuring SELinux...")
        
        # Set SELinux to permissive mode
        commands = [
            "setenforce 0",
            "sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to configure SELinux: {cmd}")
                return False
        
        return True
    
    def install_gpu_packages(self, ssh_client, packages=None):
        """Install GPU packages for RHEL"""
        log_message("Installing GPU packages...")
        
        default_packages = [
            'nvidia-container-toolkit',
            'nvidia-container-runtime'
        ]
        
        packages_to_install = packages or default_packages
        
        # Add NVIDIA repository
        repo_commands = [
            "dnf config-manager --add-repo https://nvidia.github.io/nvidia-container-runtime/centos8/nvidia-container-runtime.repo",
            "dnf config-manager --add-repo https://nvidia.github.io/nvidia-docker/centos8/nvidia-docker.repo"
        ]
        
        for cmd in repo_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to add NVIDIA repository: {cmd}")
                return False
        
        # Install GPU packages
        package_list = ' '.join(packages_to_install)
        install_cmd = f"dnf install -y {package_list}"
        
        if not run_ssh_command(ssh_client, install_cmd):
            log_error("Failed to install GPU packages")
            return False
        
        # Configure containerd for GPU
        gpu_config_commands = [
            "nvidia-ctk runtime configure --runtime=containerd",
            "systemctl restart containerd"
        ]
        
        for cmd in gpu_config_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to configure GPU runtime: {cmd}")
                return False
        
        return True
    
    def setup_kubernetes_repo(self, ssh_client):
        """Setup Kubernetes repository for RHEL"""
        log_message("Setting up Kubernetes repository...")
        
        repo_content = """[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
"""
        
        # Create repo file
        create_repo_cmd = f"cat > /etc/yum.repos.d/kubernetes.repo << 'EOF'\n{repo_content}EOF"
        
        if not run_ssh_command(ssh_client, create_repo_cmd):
            log_error("Failed to create Kubernetes repository")
            return False
        
        return True
    
    def disable_swap(self, ssh_client):
        """Disable swap for Kubernetes"""
        log_message("Disabling swap...")
        
        commands = [
            "swapoff -a",
            "sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to disable swap: {cmd}")
                return False
        
        return True
    
    def configure_kernel_modules(self, ssh_client):
        """Load required kernel modules"""
        log_message("Configuring kernel modules...")
        
        modules = ['br_netfilter', 'overlay']
        
        # Load modules immediately
        for module in modules:
            if not run_ssh_command(ssh_client, f"modprobe {module}"):
                log_error(f"Failed to load module: {module}")
                return False
        
        # Make modules persistent
        modules_content = '\n'.join(modules)
        create_modules_cmd = f"cat > /etc/modules-load.d/k8s.conf << 'EOF'\n{modules_content}\nEOF"
        
        if not run_ssh_command(ssh_client, create_modules_cmd):
            log_error("Failed to create kernel modules configuration")
            return False
        
        # Configure sysctl
        sysctl_content = """net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
"""
        
        create_sysctl_cmd = f"cat > /etc/sysctl.d/k8s.conf << 'EOF'\n{sysctl_content}EOF"
        
        if not run_ssh_command(ssh_client, create_sysctl_cmd):
            log_error("Failed to create sysctl configuration")
            return False
        
        # Apply sysctl settings
        if not run_ssh_command(ssh_client, "sysctl --system"):
            log_error("Failed to apply sysctl settings")
            return False
        
        return True
    
    def get_package_manager(self):
        """Return the package manager for RHEL"""
        return "dnf"