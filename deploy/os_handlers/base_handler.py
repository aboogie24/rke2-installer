from abc import ABC, abstractmethod

class BaseOSHandler(ABC):
    """Base class for all operating system handlers"""

    @abstractmethod
    def stage_bundle(self, ssh_client, node, os_type, dist, local_bundle_path):
        """Stage Bundle on host node"""
        pass

    @abstractmethod
    def extract_bundle(self, ssh_client, node, local_bundle_path):
        """Extract Bundle on host node"""
        pass
    
    @abstractmethod
    def install_base_packages(self, ssh_client, packages=None, local_bundle_path=None):
        """Install base packages required for Kubernetes"""
        pass
    
    @abstractmethod
    def install_container_runtime(self, ssh_client, runtime='containerd'):
        """Install and configure container runtime"""
        pass
    
    @abstractmethod
    def configure_firewall(self, ssh_client, node_type):
        """Configure firewall for Kubernetes"""
        pass
    
    @abstractmethod
    def configure_selinux(self, ssh_client):
        """Configure SELinux/AppArmor for Kubernetes"""
        pass
    
    @abstractmethod
    def install_gpu_packages(self, ssh_client, packages=None):
        """Install GPU-related packages"""
        pass
    
    @abstractmethod
    def setup_kubernetes_repo(self, ssh_client):
        """Setup Kubernetes package repository"""
        pass
    
    @abstractmethod
    def disable_swap(self, ssh_client):
        """Disable swap for Kubernetes"""
        pass
    
    @abstractmethod
    def configure_kernel_modules(self, ssh_client):
        """Load required kernel modules"""
        pass
    
    @abstractmethod
    def get_package_manager(self):
        """Return the package manager command for this OS"""
        pass
    
    @abstractmethod
    def config_tmp_directory(self, ssh_client):
        """Configure /tmp directory if needed"""
        pass
    
    def get_os_name(self):
        """Return the OS name"""
        return self.__class__.__name__.replace('Handler', '').lower()