from .rke2_handler import RKE2Handler
from .eks_anywhere_handler import EKSAnywhereHandler
from .airgapped_rke2_handler import AirgappedRKE2Handler
from ..utils import log_message    
#from .vanilla_k8s_handler import VanillaK8sHandler
#from .k3s_handler import K3sHandler

def get_distribution_handler(distribution):
    """Factory function to get appropriate distribution handler"""
    handlers = {
        'rke2': RKE2Handler,
        'eks-anywhere': EKSAnywhereHandler,
        #'vanilla': VanillaK8sHandler,
        #'k3s': K3sHandler,
        #'kubeadm': VanillaK8sHandler,  # Use vanilla handler for kubeadm
    }
    
    if distribution not in handlers:
        raise ValueError(f"Unsupported distribution: {distribution}")
    
    return handlers[distribution]()

def get_airgapped_distribution_handler(distribution):
    """Airgapped function to get the appropriate for airgapped environments handler"""
    handlers = {
        'rke2': AirgappedRKE2Handler,
    }

    if distribution not in handlers:
        raise ValueError(f"Unsupported distribution: {distribution}")
    
    log_message("Returning handler")
    return handlers[distribution]()