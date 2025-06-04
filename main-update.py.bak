#!/usr/bin/env python3
import click
import yaml
import colorama
import paramiko
from deploy.node import setup_node, install_gpu_stack
from deploy.health import post_install_health_check
from deploy.utils import log_message, log_error, log_success, log_warning
#from deploy.distributions import get_distribution_handler
#from deploy.os_handlers import get_os_handler
from logo.space_jam_logo import display_animated_logo, display_space_jam_logo4
#from uninstall.uninstall_cluster import uninstall_cluster

colorama.init(autoreset=True)

# Supported configurations
SUPPORTED_DISTRIBUTIONS = ['rke2', 'eks-anywhere', 'vanilla', 'k3s', 'kubeadm']
SUPPORTED_OS = ['rhel', 'ubuntu', 'centos', 'rocky', 'debian']

def load_config(config_file):
    """Load and validate configuration file"""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate configuration
    validate_config(config)
    return config

def validate_config(config):
    """Validate configuration for supported options"""
    deployment = config.get('deployment', {})
    
    # Check K8s distribution
    k8s_dist = deployment.get('k8s_distribution', 'rke2')
    if k8s_dist not in SUPPORTED_DISTRIBUTIONS:
        raise click.ClickException(
            f"Unsupported Kubernetes distribution: {k8s_dist}. "
            f"Supported: {', '.join(SUPPORTED_DISTRIBUTIONS)}"
        )
    
    # Check OS type
    os_type = deployment.get('os', {}).get('type', 'rhel')
    if os_type not in SUPPORTED_OS:
        raise click.ClickException(
            f"Unsupported OS: {os_type}. "
            f"Supported: {', '.join(SUPPORTED_OS)}"
        )
    
    # Distribution-specific validation
    if k8s_dist == 'rke2' and 'rke2' not in deployment:
        raise click.ClickException("RKE2 configuration section missing")
    elif k8s_dist == 'eks-anywhere' and 'eks_anywhere' not in deployment:
        raise click.ClickException("EKS Anywhere configuration section missing")

@click.group()
def cli():
    """Multi-Distribution Kubernetes Deployment CLI"""
    pass

@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
@click.option('--extra-tools', '-e', multiple=True, type=click.Choice(['k9s', 'helm', 'flux']),
              help='Install additional tools (specify multiple times for multiple tools)')
@click.option('--dry-run', is_flag=True, help='Show what would be deployed without actually deploying')
def deploy(config, extra_tools, dry_run):
    """Deploy Kubernetes Cluster"""
    display_animated_logo()
    
    try:
        cfg = load_config(config)
    except Exception as e:
        log_error(f"Configuration error: {e}")
        return
    
    # Add extra_tools to config
    if extra_tools:
        cfg['extra_tools'] = list(extra_tools)
        click.echo(colorama.Fore.CYAN + "Extra tools to be installed: " + 
                   colorama.Fore.YELLOW + f"{', '.join(extra_tools)}")

    deployment = cfg['deployment']
    k8s_dist = deployment.get('k8s_distribution', 'rke2')
    os_info = deployment.get('os', {'type': 'rhel', 'version': '8'})
    
    click.echo(colorama.Fore.CYAN + f"Deploying {k8s_dist.upper()} cluster: " + 
               colorama.Fore.YELLOW + f"{cfg['cluster']['name']}")
    click.echo(colorama.Fore.CYAN + f"Target OS: " + 
               colorama.Fore.YELLOW + f"{os_info['type']} {os_info['version']}")
    
    if dry_run:
        click.echo(colorama.Fore.YELLOW + "\n=== DRY RUN MODE ===")
        show_deployment_plan(cfg)
        return
    
    # Get appropriate handlers
    try:
        dist_handler = get_distribution_handler(k8s_dist)
        os_handler = get_os_handler(os_info['type'])
    except Exception as e:
        log_error(f"Handler error: {e}")
        return
    
    # Pre-deployment validation
    click.echo(colorama.Fore.CYAN + "\nValidating cluster requirements...")
    if not dist_handler.validate_requirements(cfg):
        log_error("Pre-deployment validation failed")
        return
    
    # Server nodes
    click.echo(colorama.Fore.CYAN + f"\n=== Deploying Server Nodes ===")
    for i, node in enumerate(cfg['nodes']['servers']):
        is_first_server = (i == 0)
        node_os = node.get('os_override', os_info)
        
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + 
                   colorama.Fore.CYAN + f"] Setting up {'first' if is_first_server else 'joining'} server " + 
                   colorama.Fore.MAGENTA + f"({node['ip']}) - {node_os['type']} {node_os['version']}")
        
        # Get OS handler for this specific node
        node_os_handler = get_os_handler(node_os['type'])
        
        setup_node(node, cfg, dist_handler, node_os_handler, 
                  is_server=True, is_first_server=is_first_server)

    # Agent nodes
    click.echo(colorama.Fore.CYAN + f"\n=== Deploying Agent Nodes ===")
    for node in cfg['nodes']['agents']:
        node_os = node.get('os_override', os_info)
        
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + 
                   colorama.Fore.CYAN + f"] Setting up agent " + 
                   colorama.Fore.MAGENTA + f"({node['ip']}) - {node_os['type']} {node_os['version']}")
        
        node_os_handler = get_os_handler(node_os['type'])
        setup_node(node, cfg, dist_handler, node_os_handler, is_server=False)

        # GPU support
        if node.get("gpu_enabled", False):
            click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + 
                       colorama.Fore.CYAN + f"] Installing GPU stack...")
            install_gpu_stack(node, cfg, node_os_handler)
    
    # Post-install health check
    click.echo(colorama.Fore.CYAN + f"\n=== Running Health Checks ===")
    for node in cfg['nodes']['servers']:
        post_install_health_check(node, dist_handler)

    log_success(f"✅ {k8s_dist.upper()} cluster '{cfg['cluster']['name']}' deployed successfully!")
    display_space_jam_logo4()

def show_deployment_plan(cfg):
    """Display deployment plan for dry run"""
    deployment = cfg['deployment']
    k8s_dist = deployment.get('k8s_distribution', 'rke2')
    
    click.echo(f"\nDeployment Plan:")
    click.echo(f"  Kubernetes Distribution: {k8s_dist}")
    click.echo(f"  Default OS: {deployment['os']['type']} {deployment['os']['version']}")
    click.echo(f"  Cluster Name: {cfg['cluster']['name']}")
    
    click.echo(f"\n  Server Nodes ({len(cfg['nodes']['servers'])}):")
    for i, node in enumerate(cfg['nodes']['servers']):
        role = "First Server" if i == 0 else "Server"
        node_os = node.get('os_override', deployment['os'])
        click.echo(f"    - {node['hostname']} ({node['ip']}) - {role} - {node_os['type']} {node_os['version']}")
    
    click.echo(f"\n  Agent Nodes ({len(cfg['nodes']['agents'])}):")
    for node in cfg['nodes']['agents']:
        node_os = node.get('os_override', deployment['os'])
        gpu_status = "GPU-enabled" if node.get('gpu_enabled') else "Standard"
        click.echo(f"    - {node['hostname']} ({node['ip']}) - {gpu_status} - {node_os['type']} {node_os['version']}")

@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
@click.option('--force', '-f', is_flag=True, help='Force uninstall without confirmation')
def uninstall(config, force):
    """Uninstall Kubernetes Cluster"""
    display_animated_logo()

    try:
        cfg = load_config(config)
    except Exception as e:
        log_error(f"Configuration error: {e}")
        return
    
    deployment = cfg['deployment']
    k8s_dist = deployment.get('k8s_distribution', 'rke2')
    
    # Count total nodes
    total_nodes = len(cfg['nodes']['servers']) + len(cfg['nodes']['agents'])
    
    click.echo(colorama.Fore.RED + f"Preparing to uninstall {k8s_dist.upper()} from " + 
              colorama.Fore.YELLOW + f"{cfg['cluster']['name']}" + 
              colorama.Fore.RED + f" ({total_nodes} nodes)")
    
    if not force:
        confirm = click.confirm(colorama.Fore.RED + f'Are you sure you want to uninstall {k8s_dist.upper()} from all nodes?')
        if not confirm:
            click.echo(colorama.Fore.CYAN + "Uninstall cancelled.")
            return
    
    # Get distribution handler for proper uninstall
    try:
        dist_handler = get_distribution_handler(k8s_dist)
    except Exception as e:
        log_error(f"Handler error: {e}")
        return
    
    uninstall_cluster(cfg, dist_handler)
    
    log_success(f"✅ {k8s_dist.upper()} uninstallation complete for cluster '{cfg['cluster']['name']}'")
    display_space_jam_logo4()

@cli.command()
def list_supported():
    """List supported Kubernetes distributions and operating systems"""
    click.echo(colorama.Fore.CYAN + "Supported Kubernetes Distributions:")
    for dist in SUPPORTED_DISTRIBUTIONS:
        click.echo(f"  • {dist}")
    
    click.echo(colorama.Fore.CYAN + "\nSupported Operating Systems:")
    for os_type in SUPPORTED_OS:
        click.echo(f"  • {os_type}")

@cli.command()
@click.option('--distribution', '-d', type=click.Choice(SUPPORTED_DISTRIBUTIONS), 
              help='Generate config for specific distribution')
@click.option('--os', '-o', type=click.Choice(SUPPORTED_OS), 
              help='Generate config for specific OS')
@click.option('--output', default='generated-config.yml', 
              help='Output file name (default: generated-config.yml)')
def generate_config(distribution, os, output):
    """Generate a sample configuration file"""
    from deploy.config_generator import generate_sample_config
    
    click.echo(colorama.Fore.CYAN + f"Generating sample configuration...")
    
    try:
        generate_sample_config(
            distribution=distribution or 'rke2',
            os_type=os or 'rhel',
            output_file=output
        )
        log_success(f"✅ Sample configuration generated: {output}")
    except Exception as e:
        log_error(f"Failed to generate config: {e}")

if __name__ == "__main__":
    cli()