#!/usr/bin/env python3
import click
import yaml
import colorama
import paramiko
from deploy.node import setup_node, install_gpu_stack
from deploy.health import post_install_health_check
from deploy.utils import log_message, log_error, log_success, log_warning
from logo.space_jam_logo import display_animated_logo, display_space_jam_logo4
from uninstall.uninstall_rke2 import uninstall_rke2

colorama.init(autoreset=True)

def load_config(config_file):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

@click.group()
def cli():
    """Space Jam Deployment CLI"""
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

        # GPU Enabled Agent ? 
        if node.get("gpu_enabled", False):
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=node["ip"],
                username=node["user"],
                key_filename=node["ssh_key"]
            )
            install_gpu_stack(ssh, node, cfg['cluster']['nvidia_rpm_path'])
            ssh.close()
    
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


if __name__ == "__main__":
    cli()