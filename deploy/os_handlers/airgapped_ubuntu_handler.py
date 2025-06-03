from .base_handler import BaseOSHandler
from ..utils import log_message, log_error, log_success, run_ssh_command

class AirgappedUbuntuHandler(BaseOSHandler):
    """Handler for Ubuntu in airgapped environments with non-root user"""
    
    def install_base_packages(self, ssh_client, packages=None):
        """Install base packages from local bundle"""
        log_message("Installing base packages for Ubuntu (airgapped)...")
        
        # Check if we have a package bundle
        bundle_path = "/tmp/k8s-bundles/ubuntu20-packages.tar.gz"
        if not self._check_remote_file_exists(ssh_client, bundle_path):
            log_warning("No package bundle found, assuming packages are pre-installed")
            return True
        
        # Extract and install packages from bundle
        extract_commands = [
            f"cd /tmp && tar -xzf {bundle_path}",
            "cd /tmp/ubuntu20-packages && sudo apt-get update || true",
            "cd /tmp/ubuntu20-packages && sudo dpkg -i *.deb || true",
            "sudo apt-get install -f -y"  # Fix any dependency issues
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
            commands = [
                "cd /tmp/ubuntu20-packages && sudo dpkg -i containerd*.deb || sudo apt-get install -y containerd",
                "sudo mkdir -p /etc/containerd",
                "sudo containerd config default | sudo tee /etc/containerd/config.toml",
                "sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml",
                "sudo systemctl enable containerd",
                "sudo systemctl restart containerd"
            ]
        elif runtime == 'crio':
            commands = [
                "cd /tmp/ubuntu20-packages && sudo dpkg -i cri-o*.deb || sudo apt-get install -y cri-o cri-o-runc",
                "sudo systemctl enable crio",
                "sudo systemctl start crio"
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
        """Configure UFW firewall with sudo"""
        log_message("Configuring UFW firewall (airgapped)...")
        
        # Check if UFW is active
        stdout, stderr, exit_code = run_ssh_command(ssh_client, 
            "sudo ufw status", return_output=True)
        
        if "inactive" in stdout:
            log_message("UFW is inactive, skipping firewall configuration")
            return True
        
        firewall_commands = []
        
        if node_type == 'server':
            server_ports = [
                "6443",      # Kubernetes API server
                "2379:2380", # etcd server client API
                "10250",     # Kubelet API
                "10251",     # kube-scheduler
                "10252",     # kube-controller-manager
                "9345",      # RKE2 supervisor API
            ]
            
            for port in server_ports:
                firewall_commands.append(f"sudo ufw allow {port}")
        
        # Common ports for all nodes
        common_ports = [
            "10250",       # Kubelet API
            "30000:32767", # NodePort Services
        ]
        
        for port in common_ports:
            firewall_commands.append(f"sudo ufw allow {port}")
        
        for cmd in firewall_commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to configure firewall: {cmd}")
                return False
        
        return True
    
    def configure_selinux(self, ssh_client):
        """Configure AppArmor for Ubuntu"""
        log_message("Configuring AppArmor (airgapped)...")
        
        # AppArmor is usually fine for Kubernetes
        # Just check if it's installed and running
        commands = [
            "which apparmor_status || echo 'AppArmor not installed'",
        ]
        
        for cmd in commands:
            run_ssh_command(ssh_client, cmd)  # Don't fail if AppArmor commands fail
        
        return True
    
    def install_gpu_packages(self, ssh_client, packages=None):
        """Install GPU packages from local bundle"""
        log_message("Installing GPU packages (airgapped)...")
        
        gpu_bundle_path = "/tmp/k8s-bundles/nvidia-packages-ubuntu20.tar.gz"
        if not self._check_remote_file_exists(ssh_client, gpu_bundle_path):
            log_error("GPU package bundle not found")
            return False
        
        # Extract and install GPU packages
        gpu_commands = [
            f"cd /tmp && tar -xzf {gpu_bundle_path}",
            "cd /tmp/nvidia-packages && sudo dpkg -i *.deb",
            "sudo apt-get install -f -y",  # Fix dependencies
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
    
    def disable_swap(self, ssh_client):
        """Disable swap with sudo privileges"""
        log_message("Disabling swap...")
        
        commands = [
            "sudo swapoff -a",
            "sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd):
                log_error(f"Failed to disable swap: {cmd}")
                return False
        
        return True
    
    def configure_kernel_modules(self, ssh_client):
        """Load required kernel modules with sudo"""
        log_message("Configuring kernel modules...")
        
        modules = ['br_netfilter', 'overlay']
        
        # Load modules immediately
        for module in modules:
            if not run_ssh_command(ssh_client, f"sudo modprobe {module}"):
                log_error(f"Failed to load module: {module}")
                return False
        
        # Make modules persistent
        modules_content = '\n'.join(modules)
        create_modules_cmd = f"echo '{modules_content}' | sudo tee /etc/modules-load.d/k8s.conf"
        
        if not run_ssh_command(ssh_client, create_modules_cmd):
            log_error("Failed to create kernel modules configuration")
            return False
        
        # Configure sysctl
        sysctl_content = """net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1"""
        
        create_sysctl_cmd = f"echo '{sysctl_content}' | sudo tee /etc/sysctl.d/k8s.conf"
        
        if not run_ssh_command(ssh_client, create_sysctl_cmd):
            log_error("Failed to create sysctl configuration")
            return False
        
        # Apply sysctl settings
        if not run_ssh_command(ssh_client, "sudo sysctl --system"):
            log_error("Failed to apply sysctl settings")
            return False
        
        return True
    
    def get_package_manager(self):
        """Return the package manager for Ubuntu"""
        return "apt"
    
    def _check_remote_file_exists(self, ssh_client, file_path):
        """Check if a file exists on the remote system"""
        stdout, stderr, exit_code = run_ssh_command(ssh_client, 
            f"test -f {file_path} && echo 'exists'", return_output=True)
        return exit_code == 0 and 'exists' in stdout

