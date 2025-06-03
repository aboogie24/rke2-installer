from abc import ABC, abstractmethod

class BaseDistributionHandler(ABC):
    """Base class for all Kubernetes distribution handlers"""
    
    @abstractmethod
    def validate_requirements(self, config):
        """Validate distribution-specific requirements"""
        pass
    
    @abstractmethod
    def prepare_server_node(self, ssh_client, config, is_first_server=False):
        """Prepare and configure server node"""
        pass
    
    @abstractmethod
    def prepare_agent_node(self, ssh_client, config):
        """Prepare and configure agent node"""
        pass
    
    @abstractmethod
    def generate_config_files(self, config, node_type, is_first_server=False):
        """Generate distribution-specific configuration files"""
        pass
    
    @abstractmethod
    def install_distribution(self, ssh_client, config, node_type):
        """Install the Kubernetes distribution"""
        pass
    
    @abstractmethod
    def start_services(self, ssh_client, node_type):
        """Start distribution-specific services"""
        pass
    
    @abstractmethod
    def health_check(self, ssh_client, node):
        """Perform distribution-specific health checks"""
        pass
    
    @abstractmethod
    def uninstall(self, ssh_client, node_type):
        """Uninstall the distribution"""
        pass
    
    def get_distribution_name(self):
        """Return the distribution name"""
        return self.__class__.__name__.replace('Handler', '').lower()