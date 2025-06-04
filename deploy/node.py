import paramiko
from .utils import log_message, log_error, log_success, log_warning

def setup_node(node, config, dist_handler, os_handler, is_server=False, is_first_server=False):
    """Setup a node with the specified distribution and OS handlers"""
    
    try:
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        log_message(f"Connecting to {node['hostname']} ({node['ip']})...")
        ssh.connect(
            hostname=node["ip"],
            username=node["user"],
            key_filename=node["ssh_key"],
            timeout=30
        )
        
        # Step 1: OS-level preparation
        log_message(node, "Step 1: Preparing operating system...")
        
        # Get packages from config if specified
        packages = config.get('packages', {}).get(os_handler.get_os_name(), {}).get('base_packages')
        
        if not os_handler.install_base_packages(ssh, node, packages):
            raise Exception("Failed to install base packages")
        
        if not os_handler.disable_swap(ssh, node):
            raise Exception("Failed to disable swap")
        
        if not os_handler.configure_kernel_modules(ssh):
            raise Exception("Failed to configure kernel modules")
        
        if not os_handler.configure_selinux(ssh):
            raise Exception("Failed to configure SELinux/AppArmor")
        
        if not os_handler.configure_firewall(ssh, 'server' if is_server else 'agent'):
            raise Exception("Failed to configure firewall")
        
        # Step 2: Container runtime installation
        log_message("Step 2: Installing container runtime...")
        
        runtime = config['deployment'].get('vanilla_k8s', {}).get('container_runtime', 'containerd')
        if not os_handler.install_container_runtime(ssh, runtime):
            raise Exception("Failed to install container runtime")
        
        # Step 3: Distribution-specific preparation
        log_message("Step 3: Preparing for Kubernetes distribution...")
        
        if is_server:
            if not dist_handler.prepare_server_node(ssh, config, is_first_server):
                raise Exception("Failed to prepare server node")
        else:
            if not dist_handler.prepare_agent_node(ssh, config):
                raise Exception("Failed to prepare agent node")
        
        # Step 4: Install Kubernetes distribution
        log_message("Step 4: Installing Kubernetes distribution...")
        
        node_type = 'server' if is_server else 'agent'
        if not dist_handler.install_distribution(ssh, config, node_type):
            raise Exception("Failed to install Kubernetes distribution")
        
        # Step 5: Start services
        log_message("Step 5: Starting services...")
        
        if not dist_handler.start_services(ssh, node_type):
            raise Exception("Failed to start services")
        
        # Step 6: Install extra tools (if specified and this is a server)
        if is_server and 'extra_tools' in config:
            log_message("Step 6: Installing extra tools...")
            install_extra_tools(ssh, config['extra_tools'], os_handler)
        
        ssh.close()
        log_success(f"✅ Node {node['hostname']} setup completed successfully")
        return True
        
    except Exception as e:
        log_error(f"❌ Failed to setup node {node['hostname']}: {str(e)}")
        if 'ssh' in locals():
            ssh.close()
        return False

def install_gpu_stack(node, config, os_handler):
    """Install GPU stack on a node"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=node["ip"],
            username=node["user"],
            key_filename=node["ssh_key"]
        )
        
        log_message(f"Installing GPU stack on {node['hostname']}...")
        
        # Get GPU packages from config if specified
        gpu_packages = config.get('packages', {}).get(os_handler.get_os_name(), {}).get('gpu_packages')
        
        if not os_handler.install_gpu_packages(ssh, gpu_packages):
            raise Exception("Failed to install GPU packages")
        
        ssh.close()
        log_success(f"✅ GPU stack installed on {node['hostname']}")
        return True
        
    except Exception as e:
        log_error(f"❌ Failed to install GPU stack on {node['hostname']}: {str(e)}")
        if 'ssh' in locals():
            ssh.close()
        return False

def install_extra_tools(ssh_client, tools, os_handler):
    """Install extra tools like k9s, helm, flux"""
    log_message("Installing extra tools...")
    
    for tool in tools:
        try:
            if tool == 'k9s':
                install_k9s(ssh_client, os_handler)
            elif tool == 'helm':
                install_helm(ssh_client, os_handler)
            elif tool == 'flux':
                install_flux(ssh_client, os_handler)
            else:
                log_warning(f"Unknown tool: {tool}")
                
        except Exception as e:
            log_error(f"Failed to install {tool}: {str(e)}")

def install_k9s(ssh_client, os_handler):
    """Install k9s"""
    from .utils import run_ssh_command
    
    commands = [
        "curl -sL https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz | tar xzf - -C /tmp",
        "install -m 755 /tmp/k9s /usr/local/bin/k9s",
        "rm -f /tmp/k9s"
    ]
    
    for cmd in commands:
        if not run_ssh_command(ssh_client, cmd):
            raise Exception(f"Failed to execute: {cmd}")

def install_helm(ssh_client, os_handler):
    """Install Helm"""
    from .utils import run_ssh_command
    
    commands = [
        "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
    ]
    
    for cmd in commands:
        if not run_ssh_command(ssh_client, cmd):
            raise Exception(f"Failed to execute: {cmd}")

def install_flux(ssh_client, os_handler):
    """Install Flux CLI"""
    from .utils import run_ssh_command
    
    commands = [
        "curl -s https://fluxcd.io/install.sh | bash",
        "install -m 755 ~/.local/bin/flux /usr/local/bin/flux || install -m 755 ./flux /usr/local/bin/flux"
    ]
    
    for cmd in commands:
        if not run_ssh_command(ssh_client, cmd):
            raise Exception(f"Failed to execute: {cmd}")
