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
        
        if not os_handler.configure_kernel_modules(ssh, node):
            raise Exception("Failed to configure kernel modules")
        
        if not os_handler.configure_selinux(ssh, node):
            raise Exception("Failed to configure SELinux/AppArmor")
        
        if not os_handler.configure_firewall(ssh, 'server' if is_server else 'agent', node):
            raise Exception("Failed to configure firewall")
        
        # Step 2: Container runtime installation
        log_message("Step 2: Installing container runtime...")
        
        # Only install the container runtime using 'vanilla
        deployment_type = config.get('deployment', {}).get('type')
        if deployment_type == 'vanilla_k8s':
            runtime = config['deployment']['vanilla_k8s'].get('container_runtime', 'containerd')
            if not os_handler.install_container_runtime(ssh, runtime):
                raise Exception("Failed to install container runtime")
        else: 
            log_warning(node, 'Skipping container runtime install...')
        
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
            install_extra_tools(ssh, config['extra_tools'], os_handler, config)
        
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

def install_extra_tools(ssh_client, tools, os_handler, config=None):
    """Install extra tools like k9s, helm, flux"""
    log_message("Installing extra tools...")
    
    # Check if we're in an airgapped environment
    is_airgapped = config and config.get('deployment', {}).get('airgap', {}).get('enabled', False)
    
    for tool in tools:
        try:
            if tool == 'k9s':
                install_k9s(ssh_client, os_handler, config, is_airgapped)
            elif tool == 'helm':
                install_helm(ssh_client, os_handler, config, is_airgapped)
            elif tool == 'flux':
                install_flux(ssh_client, os_handler, config, is_airgapped)
            else:
                log_warning(f"Unknown tool: {tool}")
                
        except Exception as e:
            log_error(f"Failed to install {tool}: {str(e)}")

def install_k9s(ssh_client, os_handler, config=None, is_airgapped=False):
    """Install k9s"""
    from .utils import run_ssh_command
    
    if is_airgapped and config:
        # Get bundle path from config
        bundle_path = _get_bundle_path(ssh_client, config)
        if bundle_path:
            log_message("Installing k9s from airgap bundle...")
            commands = [
                f"sudo cp {bundle_path}/bin/k9s /usr/bin/k9s",
                "sudo chmod +x /usr/bin/k9s"
            ]
        else:
            raise Exception("Bundle path not found for airgapped k9s installation")
    else:
        # Online installation
        log_message("Installing k9s from internet...")
        commands = [
            "curl -sL https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz | tar xzf - -C /tmp",
            "sudo install -m 755 /tmp/k9s /usr/local/bin/k9s",
            "rm -f /tmp/k9s"
        ]
    
    for cmd in commands:
        if not run_ssh_command(ssh_client, cmd):
            raise Exception(f"Failed to execute: {cmd}")

def install_helm(ssh_client, os_handler, config=None, is_airgapped=False):
    """Install Helm"""
    from .utils import run_ssh_command
    
    if is_airgapped and config:
        # Get bundle path from config
        bundle_path = _get_bundle_path(ssh_client, config)
        if bundle_path:
            log_message("Installing helm from airgap bundle...")
            commands = [
                f"sudo cp {bundle_path}/bin/helm /usr/bin/helm",
                "sudo chmod +x /usr/bin/helm"
            ]
        else:
            raise Exception("Bundle path not found for airgapped helm installation")
    else:
        # Online installation
        log_message("Installing helm from internet...")
        commands = [
            "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
        ]
    
    for cmd in commands:
        if not run_ssh_command(ssh_client, cmd):
            raise Exception(f"Failed to execute: {cmd}")

def install_flux(ssh_client, os_handler, config=None, is_airgapped=False):
    """Install Flux CLI"""
    from .utils import run_ssh_command
    
    if is_airgapped and config:
        # Get bundle path from config
        bundle_path = _get_bundle_path(ssh_client, config)
        if bundle_path:
            log_message("Installing flux from airgap bundle...")
            commands = [
                f"sudo cp {bundle_path}/bin/flux /usr/bin/flux",
                "sudo chmod +x /usr/bin/flux"
            ]
        else:
            raise Exception("Bundle path not found for airgapped flux installation")
    else:
        # Online installation
        log_message("Installing flux from internet...")
        commands = [
            "curl -s https://fluxcd.io/install.sh | bash",
            "sudo install -m 755 ~/.local/bin/flux /usr/local/bin/flux || sudo install -m 755 ./flux /usr/local/bin/flux"
        ]
    
    for cmd in commands:
        if not run_ssh_command(ssh_client, cmd):
            raise Exception(f"Failed to execute: {cmd}")

def _get_bundle_path(ssh_client, config):
    """Get the bundle path for airgapped installations"""
    from .utils import run_ssh_command
    
    # Try to get the current node to find its staging paths
    try:
        transport = ssh_client.get_transport()
        if not transport:
            return None

        remote_host = transport.getpeername()[0]

        # Search in servers
        for node in config.get('nodes', {}).get('servers', []):
            if node.get('ip') == remote_host or node.get('hostname') == remote_host:
                staging_paths = node.get('staging_paths', {})
                return staging_paths.get('bundles', '/tmp/k8s-bundles')

        # Search in agents
        for node in config.get('nodes', {}).get('agents', []):
            if node.get('ip') == remote_host or node.get('hostname') == remote_host:
                staging_paths = node.get('staging_paths', {})
                return staging_paths.get('bundles', '/tmp/k8s-bundles')

        # Default fallback
        return '/tmp/k8s-bundles'

    except Exception as e:
        log_error(f"Failed to get bundle path: {e}")
        return '/tmp/k8s-bundles'
