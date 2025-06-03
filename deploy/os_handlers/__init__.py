from .rhel_handler import RHELHandler
from .ubuntu_handler import UbuntuHandler
#from .centos_handler import CentOSHandler

def get_os_handler(os_type):
    """Factory function to get appropriate OS handler"""
    handlers = {
        'rhel': RHELHandler,
        'ubuntu': UbuntuHandler,
        'debian': UbuntuHandler,  # Use Ubuntu handler for Debian (similar commands)
        #'centos': CentOSHandler,
        'rocky': RHELHandler,     # Use RHEL handler for Rocky Linux
    }
    
    if os_type not in handlers:
        raise ValueError(f"Unsupported OS: {os_type}")
    
    return handlers[os_type]()