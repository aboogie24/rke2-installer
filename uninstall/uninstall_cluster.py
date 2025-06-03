from deploy.utils import log_message, log_error, log_success
from deploy.os_handlers import get_os_handler
import paramiko

def uninstall_cluster(config, dist_handler):
    """Uninstall cluster using the appropriate distribution handler"""
    
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
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=node["ip"],
            username=node["user"],
            key_filename=node["ssh_key"]
        )
        
        node_type = 'server' if is_server else 'agent'
        
        # Use distribution handler to uninstall
        if not dist_handler.uninstall(ssh, node_type):
            log_error(f"Failed to uninstall from {node['hostname']}")
        
        ssh.close()
        log_success(f"✅ Uninstalled from {node['hostname']}")
        
    except Exception as e:
        log_error(f"❌ Failed to uninstall from {node['hostname']}: {str(e)}")
        if 'ssh' in locals():
            ssh.close()
