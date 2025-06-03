from .base_handler import BaseOSHandler
from ..utils import log_message, log_error, log_success, run_ssh_command

class UbuntuHandler(BaseOSHandler):
    """Handler for Ubuntu/Debian operating systems"""
    
    def install_base_packages(self, ssh_client, packages=None):
        """Install base packages for Ubuntu"""
        log_message("Installing base packages for Ubuntu...")
        
        default_packages = [
            'apt-transport-https',
            'ca-certificates',
            'curl',
            'gnupg',
            'lsb-release',
            'iptables',
            'software-properties-common',
            'wget',
            'vim'
        ]
        
        packages_to_install = packages or default_packages
        
        # Update package index
        if not run_ssh_command(ssh_client, "apt-get update"):
            log_error("Failed to update package index")
            return False
        
        # Install packages
        package_list = ' '.join(packages_to_install)
        install_cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install -y {package_list}"
        
        if not run_ssh_command(ssh_client, install_cmd):
            log_error("Failed to install base packages")
            return False
        
        return True
    
    def install_container_runtime(self, ssh_client, runtime='containerd'):
        """Install containerd on Ubuntu"""
        log_message(f"Installing {runtime} container runtime...")
        
        if runtime == 'containerd':
            commands = [
                # Install containerd
                "apt-get update",
                "DEBIAN_FRONTEND=noninteractive apt-get install -y containerd",
                
                # Generate default config
                "mkdir -p /etc/containerd",
                "containerd config default > /etc/containerd/config.toml",
                
                # Enable SystemdCgroup
                "sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml",
                
                # Enable and start containerd
                "systemctl enable containerd",
                "systemctl restart containerd"
            ]
        elif runtime == 'crio':
            commands = [
                # Add CRI-O repository
                "curl -fsSL https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable/xUbuntu_20.04/Release.key | gpg --dearmor -o /usr/share/keyrings/libcontainers-archive-keyring.gpg",
                "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/libcontainers-archive-keyring.gpg] https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable/xUbuntu_20.04/ /' > /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list",
                
                # Install CRI-O
                "apt-get update",
                "DEBIAN_FRONTEND=noninteractive apt-get install -y cri-o cri-o-runc",
                
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
        """Configure UFW firewall for Ubuntu"""
        log_message("Configuring UFW firewall...")
        
        # Check if UFW is active
        stdout, stderr, exit_code = run_ssh_command(ssh_client, 
            "ufw status", return_output=True)
        
        if "inactive" in stdout:
            log_message("UFW is inactive, skipping firewall configuration")
            return True
        
        firewall_commands = []
        
        if node_type == 'server':
            # Control plane ports
            server_ports = [
                "6443",      # Kubernetes API server
                "2379:2380", # etcd server client API
                "10250",     # Kubelet API
                "10251",     # kube-scheduler
                "10252",     # kube-controller-manager
                "9345",      # RKE2 supervisor API
            ]
            
            for port in server_ports:
                firewall_commands.append(f"ufw allow {port}")
        
        # Common ports for all nodes
        common_ports = [
            "10250",       # Kubelet API
            "30000:32767", # NodePort Services
        ]
        
        for port in common_ports:
            firewall_commands.append(f"ufw allow {port}")
        
        for cmd in firewall_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to configure firewall: {cmd}")
                return False
        
        return True
    
    def configure_selinux(self, ssh_client):
        """Configure AppArmor for Ubuntu (SELinux equivalent)"""
        log_message("Configuring AppArmor...")
        
        # AppArmor is usually fine for Kubernetes, but we can set it to complain mode if needed
        commands = [
            # Check if AppArmor is installed
            "which apparmor_status || echo 'AppArmor not installed'",
            
            # Set AppArmor profiles to complain mode if needed
            # "aa-complain /etc/apparmor.d/*"  # Uncomment if issues arise
        ]
        
        for cmd in commands:
            run_ssh_command(ssh_client, cmd)  # Don't fail if AppArmor commands fail
        
        return True
    
    def install_gpu_packages(self, ssh_client, packages=None):
        """Install GPU packages for Ubuntu"""
        log_message("Installing GPU packages...")
        
        default_packages = [
            'nvidia-container-toolkit',
            'nvidia-container-runtime'
        ]
        
        packages_to_install = packages or default_packages
        
        # Add NVIDIA repository
        repo_commands = [
            "curl -fsSL https://nvidia.github.io/nvidia-container-runtime/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
            "curl -s -L https://nvidia.github.io/nvidia-container-runtime/ubuntu20.04/nvidia-container-runtime.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' > /etc/apt/sources.list.d/nvidia-container-runtime.list",
            "apt-get update"
        ]
        
        for cmd in repo_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to add NVIDIA repository: {cmd}")
                return False
        
        # Install GPU packages
        package_list = ' '.join(packages_to_install)
        install_cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install -y {package_list}"
        
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
        """Setup Kubernetes repository for Ubuntu"""
        log_message("Setting up Kubernetes repository...")
        
        commands = [
            # Add Kubernetes GPG key
            "curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/kubernetes-archive-keyring.gpg",
            
            # Add Kubernetes repository
            "echo 'deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main' > /etc/apt/sources.list.d/kubernetes.list",
            
            # Update package index
            "apt-get update"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to setup Kubernetes repository: {cmd}")
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
        """Return the package manager for Ubuntu"""
        return "apt"