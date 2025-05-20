#!/usr/bin/env python3
import click
import yaml
import colorama
import paramiko
from deploy.node import setup_node
from deploy.health import post_install_health_check
from deploy.utils import log_message, log_error, log_success, log_warning
from logo.space_jam_logo import display_animated_logo, display_space_jam_logo4

colorama.init(autoreset=True)

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

@click.group()
def cli():
    """RKE2 Airgapped Deployment CLI"""
    pass

@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
@click.option('--extra-tools', '-e', multiple=True, type=click.Choice(['k9s', 'helm', 'flux']),
              help='Install additional tools (specify multiple times for multiple tools, e.g., -e k9s -e helm)')
def deploy(config, extra_tools):
    """Deploy RKE2 Cluster"""
    display_animated_logo()
    cfg = load_config(config)

    # Add extra_tools to config
    if extra_tools:
        cfg['extra_tools'] = list(extra_tools)
        click.echo(colorama.Fore.CYAN + "Extra tools to be installed: " + 
                   colorama.Fore.YELLOW + f"{', '.join(extra_tools)}")

    click.echo(colorama.Fore.CYAN + f"Deploying RKE2 cluster: " + colorama.Fore.YELLOW + f"{cfg['cluster']['name']}\n")

    # Server nodes
    for i, node in enumerate(cfg['nodes']['servers']):
        is_first_server = (i == 0)
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + colorama.Fore.CYAN + 
                   f"] Setting up {'first' if is_first_server else 'joining'} server " + 
                   colorama.Fore.MAGENTA + f"({node['ip']})")
        setup_node(node, cfg, is_server=True, is_first_server=is_first_server)

    # Agent nodes
    for node in cfg['nodes']['agents']:
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + colorama.Fore.CYAN + 
                  f"] Setting up agent " + colorama.Fore.MAGENTA + f"({node['ip']})")
        setup_node(node, cfg, is_server=False)
    
    # Post-install health check
    for node in cfg['nodes']['servers']:
        post_install_health_check(node)

    display_space_jam_logo4()


@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
@click.option('--force', '-f', is_flag=True, help='Force uninstall without confirmation')
def uninstall(config, force):
    """Uninstall RKE2 Cluster"""
    display_animated_logo()

    cfg = load_config(config)
    
    # Count total nodes
    total_nodes = len(cfg['nodes']['servers']) + len(cfg['nodes']['agents'])
    
    click.echo(colorama.Fore.RED + f"Preparing to uninstall RKE2 from " + 
              colorama.Fore.YELLOW + f"{cfg['cluster']['name']}" + 
              colorama.Fore.RED + f" ({total_nodes} nodes)")
    
    if not force:
        confirm = click.confirm(colorama.Fore.RED + 'Are you sure you want to uninstall RKE2 from all nodes?')
        if not confirm:
            click.echo(colorama.Fore.CYAN + "Uninstall cancelled.")
            return
    
    # First uninstall from agent nodes
    for node in cfg['nodes']['agents']:
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + colorama.Fore.CYAN + 
                  f"] Uninstalling RKE2 agent " + colorama.Fore.MAGENTA + f"({node['ip']})")
        uninstall_rke2(node, is_server=False)
    
    # Then uninstall from server nodes in reverse order (last-in, first-out)
    for node in reversed(cfg['nodes']['servers']):
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + colorama.Fore.CYAN + 
                  f"] Uninstalling RKE2 server " + colorama.Fore.MAGENTA + f"({node['ip']})")
        uninstall_rke2(node, is_server=True)
    
    click.echo(colorama.Fore.GREEN + f"RKE2 uninstallation complete for cluster " + 
               colorama.Fore.YELLOW + f"{cfg['cluster']['name']}")
    
    display_space_jam_logo4()

def uninstall_rke2(node, is_server=True):
    """Uninstall RKE2 from a node"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to the node
        log_message(node, "Connecting to", details=f"{node['ip']}...")
        ssh.connect(
            hostname=node['ip'],
            username=node['user'],
            key_filename=node['ssh_key']
        )
        
        service_type = "server" if is_server else "agent"
        
        # Step 1: Stop and disable the RKE2 service
        log_message(node, f"Stopping RKE2 {service_type} service...")
        commands = [
            f"sudo systemctl stop rke2-{service_type}",
            f"sudo systemctl disable rke2-{service_type}"
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                err = stderr.read().decode()
                log_warning(node, f"Warning during command '{cmd}':", details=err)
        
        # Step 2: Run the uninstall script
        log_message(node, "Running RKE2 uninstall script...")
        uninstall_paths = [
            "/usr/local/bin/rke2-uninstall.sh",  # Tarball installation
            "/usr/bin/rke2-uninstall.sh"         # RPM installation
        ]
        
        uninstall_success = False
        for script_path in uninstall_paths:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {script_path} && echo 'exists'")
            if stdout.read().decode().strip() == 'exists':
                stdin, stdout, stderr = ssh.exec_command(f"sudo {script_path}")
                exit_code = stdout.channel.recv_exit_status()
                if exit_code == 0:
                    log_success(node, f"Uninstall script at {script_path} executed successfully")
                    uninstall_success = True
                    break
                else:
                    log_error(node, f"Uninstall script failed:", details=stderr.read().decode())
        
        if not uninstall_success:
            log_warning(node, "Uninstall script not found, attempting manual cleanup...")
        
        # Step 3: Additional cleanup for any left behind files
        log_message(node, "Cleaning up remaining RKE2 files and directories...")
        cleanup_commands = [
            "sudo rm -rf /var/lib/rancher/rke2",
            "sudo rm -rf /etc/rancher/rke2",
            "sudo rm -rf /var/lib/kubelet",
            "sudo rm -rf /opt/rke2",
            "sudo rm -f /usr/local/bin/rke2",
            "sudo rm -f /usr/local/bin/kubectl",
            "sudo rm -f /usr/bin/rke2",
            "sudo rm -f /etc/systemd/system/rke2-*.service",
            "sudo rm -f /usr/share/rke2"
        ]
        
        for cmd in cleanup_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            # Not checking exit code for cleanup - some files might not exist
        
        # Step 4: Remove network interfaces
        log_message(node, "Cleaning up network interfaces...")
        network_commands = [
            "sudo ip link delete flannel.1 2>/dev/null || true",
            "sudo ip link delete cni0 2>/dev/null || true",
            "sudo ip link delete vxlan.calico 2>/dev/null || true"
        ]
        
        for cmd in network_commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Step 5: Reset firewall rules if it's a server
        if is_server:
            log_message(node, "Resetting firewall rules...")
            firewall_commands = [
                "sudo firewall-cmd --permanent --remove-port=9345/tcp || true",
                "sudo firewall-cmd --permanent --remove-port=6443/tcp || true", 
                "sudo firewall-cmd --permanent --remove-port=8472/udp || true",
                "sudo firewall-cmd --permanent --remove-port=10250/tcp || true",
                "sudo firewall-cmd --reload || true"
            ]
            
            for cmd in firewall_commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
        
        log_success(node, f"RKE2 {service_type} uninstalled successfully")
        ssh.close()
        
    except Exception as e:
        log_error(node, f"Error uninstalling RKE2:", details=str(e))

if __name__ == "__main__":
    cli()