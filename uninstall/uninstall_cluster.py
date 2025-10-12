from deploy.utils import log_message, log_error, log_success
from deploy.os_handlers import get_os_handler
from common.connect.node import connect_node
import paramiko

def uninstall_cluster(config, dist_handler):
    """Uninstall cluster using the appropriate distribution handler"""
    log_message(f"Distribution: {dist_handler.get_distribution_name()}")
    
    # Uninstall from agent nodes first
    for node in config['nodes']['agents']:
        log_message(f"Uninstalling from agent: {node['hostname']}")
        uninstall_from_node(node, config, dist_handler, is_server=False)
    
    # Then uninstall from server nodes (reverse order)
    for node in reversed(config['nodes']['servers']):
        log_message(f"Uninstalling from server: {node['hostname']}")
        uninstall_from_node(node, config, dist_handler, is_server=True)




def uninstall_from_node(node, config, dist_handler, is_server=False):
    """Uninstall from a specific node"""
    try:
        ssh = connect_node(node)
        if ssh is None:
            log_error(f"Skipping uninstallation for {node['hostname']} due to connection failure.")
            return
        
        node_type = 'server' if is_server else 'agent'
        
        # Use distribution handler to uninstall
        if not dist_handler.uninstall(ssh, node_type, sudo_password=node.get('sudo_password', '')):
            log_error(f"Failed to uninstall from {node['hostname']}")
        
        ssh.close()
        log_success(f"✅ Uninstalled from {node['hostname']}")
        
    except Exception as e:
        log_error(f"❌ Failed to uninstall from {node['hostname']}: {str(e)}")
        if 'ssh' in locals():
            ssh.close()
