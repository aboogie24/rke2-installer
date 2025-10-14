from .base_handler import BaseOSHandler
from ..utils import log_message, log_error, log_warning, log_success, run_ssh_command
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

    def stage_bundle(self, ssh_client, node, os_type, dist, local_bundle_path):
        """
            Stage bundle on host node
        """
        try:
            log_message(node, "Openning SFTP connection....")
            sftp = ssh_client.open_sftp()

            file_size = os.path.getsize(local_bundle_path)
            log_message(node, "Uploading",  details=f"{file_size/1024/1024:.2f} MB")

            def progress_callback(transferred, total):
                try:
                    if total == 0: 
                        return
                    percentage = (transferred / total) * 100
                    if abs(percentage % 10) < 0.5:
                        mb = transferred / 1024 / 1024 
                        log_message(node, "Transfer progress:", details=f"{percentage:.1f}% ({mb:.2f} MB)")
                except Exception as e: 
                    log_message(node, f"Progress callback error {e}")

            remote_path = os.path.join(
                node['staging_paths']['bundles'],
                os.path.basename(local_bundle_path)
            )

            # Perform Transfer
            sftp.put(
                local_bundle_path,
                remote_path,
                callback=progress_callback if file_size > 10*1024*1024 else None
            )             

            return True
        except Exception as e:
            log_error(node, f"Failed stage bundle: {e}")
                    # Upload with progress callback for large files

    def extract_bundle(self, ssh_client, node, local_bundle_path): 
        """Extract Bundle path"""
        try:
            log_message(node, "Extracting bundle...")
            remote_path = os.path.join(
                node['staging_paths']['bundles'],
                os.path.basename(local_bundle_path)
            )

            # This Extracts the tar in the local user home dir
            # /home/user/{bundle_name}
            extract_commands = [
                "mkdir -p /tmp/k8s-bundle",
                f"tar -xvzf {remote_path} -C /tmp/k8s-bundle --strip-components=1"
            ]

            for cmd in extract_commands:
                if not run_ssh_command(ssh_client, cmd, return_output=True, timeout=300, sudo=True, sudo_password=node['sudo_password']):
                    log_error(f"Failed to install packages: {cmd}")
                    return False

            log_success(node, f"Successfully extracted bundle to /tmp directory")
            return True
        except Exception as e: 
            log_error(node, f"Extraction Error: {e}")
            return False
    
    def install_base_packages(self, ssh_client, node, packages=None, local_bundle_path=None):
        """Install base packages from local bundle"""
        log_message(node, "Installing base packages for RHEL (airgapped)...")
        log_message(node, f"{packages}")

        
        #Change this to reflex the name of the directory 
        bundle_path = os.path.join(
            node['staging_paths']['bundles'],
            "k8s-bundle"
        )
        
        # Get path to packages

        packages_path = f"{bundle_path}/rke2/os/rhel_8.10/base_packages"
        file_path = f"/{packages_path}/base_packages_rhel_8.10.tar.gz"

        if not self._check_remote_file_exists(ssh_client, file_path):
            log_warning("No package bundle found, assuming packages are pre-installed")
            return True
        
        # Extract and install packages from bundle
        # Will need to update this in the future
        extract_commands = [
            f"tar -xvzf {file_path} -C {packages_path}",
            f"cd {packages_path}",
            f"dnf install -y {packages_path}/rpms/*.rpm --nogpgcheck"
        ]
        
        for cmd in extract_commands:
            if not run_ssh_command(ssh_client, cmd, return_output=True, timeout=300, sudo=True, sudo_password=node['sudo_password']):
                log_error(f"Failed to install packages: {cmd}")
                return False
        
        log_success(node, "Successfully installed packages")
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
            "systemctl is-active firewalld", return_output=True, timeout=300, sudo=True, sudo_password=node['sudo_password'])
        
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
            if not run_ssh_command(ssh_client, cmd, return_output=False, timeout=300, sudo=True, sudo_password=node['sudo_password']):
                log_error(node, f"Failed to configure firewall: {cmd}")
                return False
        log_success(node, "Successfully configured firewalld")
        return True
    
    def configure_selinux(self, ssh_client, node):
        """Configure SELinux with sudo privileges"""
        log_message(node, "Configuring SELinux (airgapped)...")
        
        commands = [
            "setenforce 0",
            "sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd, return_output=False, timeout=300, sudo=True, sudo_password=node['sudo_password']):
                log_error(node, f"Failed to configure SELinux: {cmd}")
                return False
        log_success(node, "Successfully set selinux to passive mode")
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
            "swapoff -a",
            "sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab"
        ]
        
        for cmd in commands:
            if not run_ssh_command(ssh_client, cmd, return_output=False, timeout=300, sudo=True, sudo_password=node['sudo_password']):
                log_error(f"Failed to disable swap: {cmd}")
                return False
        
        log_success(node, "Swap disabled")
        return True
    
    def configure_kernel_modules(self, ssh_client, node):
        """Load required kernel modules with sudo"""
        log_message(node, "Configuring kernel modules...")
        
        modules = ['br_netfilter', 'overlay']
        
        # Load modules immediately
        for module in modules:
            if not run_ssh_command(ssh_client, f"modprobe {module}", return_output=False, timeout=300, sudo=True, sudo_password=node['sudo_password']):
                log_error(node, f"Failed to load module: {module}")
                return False
        
        # Make modules persistent
        # This command may not working in STIG'd airgapped environments
        modules_content = '\n'.join(modules)
        #create_modules_cmd = f"echo '{modules_content}' | tee /etc/modules-load.d/k8s.conf"
        create_modules_cmd = (
            " bash -c "
            "\"echo -e 'br_netfilter\\noverlay' > /etc/modules-load.d/k8s.conf\""
        )

        
        if not run_ssh_command(ssh_client, create_modules_cmd, return_output=False, timeout=300, sudo=True, sudo_password=node['sudo_password']):
            log_error(node, "Failed to create kernel modules configuration")
            return False
        
        # This should be updated
        # Configure sysctl
        sysctl_content = """net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1"""

        # Escape newlines for bash -c
        escaped_content = sysctl_content.replace("\n", "\\n")

# Build command: run as root using sudo bash -c
        create_sysctl_cmd = (
            "bash -c "
            f"\"echo -e '{escaped_content}' > /etc/sysctl.d/k8s.conf\""
        )
        
        if not run_ssh_command(ssh_client, create_sysctl_cmd, return_output=False, timeout=300, sudo=True, sudo_password=node['sudo_password']):
            log_error(node, "Failed to create sysctl configuration")
            return False
        
        # Apply sysctl settings
        if not run_ssh_command(ssh_client, "sysctl --system", return_output=False, timeout=300, sudo=True, sudo_password=node['sudo_password']):
            log_error(node, "Failed to apply sysctl settings")
            return False
        log_success(node, "Successfully installed kernel modules")
        return True
    
    def get_package_manager(self):
        """Return the package manager for RHEL"""
        return "dnf"
    
    def _check_remote_file_exists(self, ssh_client, file_path):
        """Check if a file exists on the remote system"""
        stdout, stderr, exit_code = run_ssh_command(ssh_client, 
            f"test -f {file_path} && echo 'exists'", return_output=True)
        return exit_code == 0 and 'exists' in stdout
    
    def config_tmp_directory(self, ssh_client): 
        """
        Configure tmp directory
        """
        return