#!/usr/bin/env python3
import click
import yaml
import colorama
import paramiko
import os
from deploy import config_generator 
from deploy.node import setup_node, install_gpu_stack
from deploy.health import post_install_health_check
from deploy.utils import log_message, log_error, log_success, log_warning
from deploy.distributions import get_distribution_handler
from deploy.os_handlers import get_os_handler
from deploy.validation.airgap_validator import AirgapValidator
from logo.space_jam_logo import display_animated_logo, display_space_jam_logo4
from uninstall.uninstall_cluster import uninstall_cluster

colorama.init(autoreset=True)

# Supported configurations for airgapped environments
SUPPORTED_DISTRIBUTIONS = ['rke2', 'eks-a', 'vanilla', 'k3s', 'kubeadm']
SUPPORTED_OS = ['rhel', 'ubuntu', 'centos', 'rocky', 'debian']

def load_config(config_file):
    """Load and validate configuration file"""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Auto-detect if this is an old-style config and migrate it
    if 'deployment' not in config and 'cluster' in config:
        log_warning("Detected old configuration format, auto-migrating...")
        config = migrate_legacy_config(config)
    
    # Validate configuration
    validate_config(config)
    return config

def migrate_legacy_config(old_config):
    """Migrate legacy RKE2-specific config to new multi-distribution format"""
    new_config = {
        'deployment': {
            'k8s_distribution': 'rke2',
            'os': {'type': 'rhel', 'version': '8'},
            'airgap': {
                'enabled': True,
                'local_registry': old_config.get('cluster', {}).get('registry', {}).get('mirrors', {}).get('registry.example.com', {}).get('endpoints', [''])[0].replace('https://', ''),
                'bundle_staging_path': '/opt/k8s-bundles',
                'image_staging_path': '/opt/container-images'
            },
            'rke2': {
                'version': old_config.get('cluster', {}).get('version', 'v1.32.3'),
                'airgap_bundle_path': old_config.get('cluster', {}).get('airgap_bundle_path', '/opt/rke2-airgap-bundle.tar.gz'),
                'images_bundle_path': '/opt/k8s-bundles/rke2-images.tar.gz',
                'install_script_path': '/opt/k8s-bundles/install.sh'
            }
        },
        'cluster': old_config.get('cluster', {}),
        'nodes': old_config.get('nodes', {}),
        'extra_tools': old_config.get('extra_tools', [])
    }
    
    # Convert root user to non-root user with warning
    for node_list in [new_config['nodes'].get('servers', []), new_config['nodes'].get('agents', [])]:
        for node in node_list:
            if node.get('user') == 'root':
                log_warning(node, f"Converting root user to k8s-admin for {node['hostname']} - please ensure this user has sudo access")
                node['user'] = 'k8s-admin'
                node['sudo_password'] = ''
    
    return new_config

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
    
    # Airgapped environment validation
    airgap_config = deployment.get('airgap', {})
    if airgap_config.get('enabled', True):
        if not airgap_config.get('local_registry'):
            log_warning("No local registry specified for airgapped deployment")
    
    # Distribution-specific validation
    if k8s_dist == 'rke2' and 'rke2' not in deployment:
        raise click.ClickException("RKE2 configuration section missing")
    elif k8s_dist == 'eks-anywhere' and 'eks_anywhere' not in deployment:
        raise click.ClickException("EKS Anywhere configuration section missing")

def get_cluster_config(cfg):
    """
    Return the appropriate cluster config based on the Kubernetes distribution.
    Example:
    cfg['deployment']['k8s_distribution'] == 'rke2' --> cfg['cluster']['rke2']
    """
    k8s_dist = cfg.get('deployment', {}).get('k8s_distribution')
    cluster_config = cfg.get('cluster', {}).get(k8s_dist)
    if not cluster_config:
        raise ValueError(f"Missing cluster configuration for distribution: {k8s_dist}")
    return cluster_config

@click.group()
def cli():
    """Multi-Distribution Kubernetes Airgapped Deployment CLI"""
    pass



@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
@click.option('--extra-tools', '-e', multiple=True, type=click.Choice(['k9s', 'helm', 'flux']),
              help='Install additional tools (specify multiple times for multiple tools)')
@click.option('--dry-run', is_flag=True, help='Show what would be deployed without actually deploying')
@click.option('--skip-validation', is_flag=True, help='Skip pre-deployment validation')
@click.option('--stage-only', is_flag=True, help='Only stage bundles, do not deploy')
def deploy(config, extra_tools, dry_run, skip_validation, stage_only):
    """Deploy Kubernetes Cluster in Airgapped Environment"""
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
    airgap_enabled = deployment.get('airgap', {}).get('enabled', True)

    try: 
        cluster_config = get_cluster_config(cfg)
    except Exception as e:
        log_error(str(e))
        return
    
    click.echo(colorama.Fore.CYAN + f"Deploying {k8s_dist.upper()} cluster: " + 
               colorama.Fore.YELLOW + f"{cluster_config.get('name', 'Unnamed')}")
    click.echo(colorama.Fore.CYAN + f"Target OS: " + 
               colorama.Fore.YELLOW + f"{os_info['type']} {os_info['version']}")
    
    if airgap_enabled:
        click.echo(colorama.Fore.CYAN + f"Mode: " + 
                   colorama.Fore.YELLOW + "Airgapped Environment")
        local_registry = deployment.get('airgap', {}).get('local_registry', 'Not configured')
        click.echo(colorama.Fore.CYAN + f"Local Registry: " + 
                   colorama.Fore.YELLOW + f"{local_registry}")
    
    if dry_run:
        click.echo(colorama.Fore.YELLOW + "\n=== DRY RUN MODE ===")
        show_deployment_plan(cfg)
        return
    
    # Pre-deployment validation
    if not skip_validation:
        click.echo(colorama.Fore.CYAN + "\n=== Pre-deployment Validation ===")
        validator = AirgapValidator(cfg)
        if not validator.run_full_validation():
            log_error("Pre-deployment validation failed. Use --skip-validation to bypass.")
            return
    
    # Get appropriate handlers (use airgapped versions)
    try:
        if airgap_enabled:
            # Use airgapped-specific handlers
            dist_handler = get_airgapped_distribution_handler(k8s_dist)
            os_handler = get_airgapped_os_handler(os_info['type'])
        else:
            dist_handler = get_distribution_handler(k8s_dist)
            os_handler = get_os_handler(os_info['type'])
    except Exception as e:
        log_error(f"Handler error: {e}")
        return
    
    # Distribution-specific validation
    click.echo(colorama.Fore.CYAN + "\nValidating distribution requirements...")
    if not dist_handler.validate_requirements(cfg):
        log_error("Distribution validation failed")
        return
    
    if stage_only:
        click.echo(colorama.Fore.CYAN + f"\n=== Staging Bundles Only ===")
        stage_bundles_to_all_nodes(cfg, dist_handler)
        log_success("✅ Bundle staging completed")
        return
    
    # Server nodes deployment
    click.echo(colorama.Fore.CYAN + f"\n=== Deploying Server Nodes ===")
    for i, node in enumerate(cfg['nodes']['servers']):
        is_first_server = (i == 0)
        node_os = node.get('os_override', os_info)
        
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + 
                   colorama.Fore.CYAN + f"] Setting up {'first' if is_first_server else 'joining'} server " + 
                   colorama.Fore.MAGENTA + f"({node['ip']}) - {node_os['type']} {node_os['version']}")
        
        # Get OS handler for this specific node
        if airgap_enabled:
            node_os_handler = get_airgapped_os_handler(node_os['type'])
        else:
            node_os_handler = get_os_handler(node_os['type'])
        
        if not setup_node(node, cfg, dist_handler, node_os_handler, 
                         is_server=True, is_first_server=is_first_server):
            log_error(f"Failed to setup server {node['hostname']}")
            return

    # Agent nodes deployment
    click.echo(colorama.Fore.CYAN + f"\n=== Deploying Agent Nodes ===")
    for node in cfg['nodes']['agents']:
        node_os = node.get('os_override', os_info)
        
        click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + 
                   colorama.Fore.CYAN + f"] Setting up agent " + 
                   colorama.Fore.MAGENTA + f"({node['ip']}) - {node_os['type']} {node_os['version']}")
        
        if airgap_enabled:
            node_os_handler = get_airgapped_os_handler(node_os['type'])
        else:
            node_os_handler = get_os_handler(node_os['type'])
            
        if not setup_node(node, cfg, dist_handler, node_os_handler, is_server=False):
            log_error(f"Failed to setup agent {node['hostname']}")
            return

        # GPU support
        if node.get("gpu_enabled", False):
            click.echo(colorama.Fore.CYAN + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + 
                       colorama.Fore.CYAN + f"] Installing GPU stack...")
            if not install_gpu_stack(node, cfg, node_os_handler):
                log_warning(f"GPU stack installation failed on {node['hostname']}")
    
    # Post-install health check
    click.echo(colorama.Fore.CYAN + f"\n=== Running Health Checks ===")
    for node in cfg['nodes']['servers']:
        if not post_install_health_check(node, dist_handler):
            log_warning(f"Health check failed on {node['hostname']}")

    log_success(f"✅ {k8s_dist.upper()} cluster '{cfg['cluster'][k8s_dist]['name']}' deployed successfully!")
    
    # Display kubeconfig info for airgapped environments
    if airgap_enabled and k8s_dist == 'rke2':
        first_server = cfg['nodes']['servers'][0]
        click.echo(colorama.Fore.CYAN + f"\nTo access your cluster:")
        click.echo(colorama.Fore.YELLOW + f"  ssh {first_server['user']}@{first_server['ip']}")
        click.echo(colorama.Fore.YELLOW + f"  export KUBECONFIG=~/.kube/config")
        click.echo(colorama.Fore.YELLOW + f"  kubectl get nodes")
    
    display_space_jam_logo4()

def get_airgapped_distribution_handler(distribution):
    """Get airgapped-specific distribution handler"""
    if distribution == 'rke2':
        from deploy.distributions.airgapped_rke2_handler import AirgappedRKE2Handler
        return AirgappedRKE2Handler()
    elif distribution == 'eks-a':
        from deploy.distributions.eks_anywhere_handler import EKSAnywhereHandler
        return EKSAnywhereHandler()
    else:
        # For other distributions, use regular handlers for now
        return get_distribution_handler(distribution)

def get_airgapped_os_handler(os_type):
    """Get airgapped-specific OS handler"""
    if os_type in ['rhel', 'centos', 'rocky']:
        from deploy.os_handlers.airgapped_rhel_handler import AirgappedRHELHandler
        return AirgappedRHELHandler()
    elif os_type in ['ubuntu', 'debian']:
        from deploy.os_handlers.airgapped_ubuntu_handler import AirgappedUbuntuHandler
        return AirgappedUbuntuHandler()
    else:
        # Fallback to regular handlers
        return get_os_handler(os_type)

def stage_bundles_to_all_nodes(config, dist_handler):
    """Stage bundles to all nodes"""
    from deploy.airgap.bundle_manager import BundleManager
    
    bundle_manager = BundleManager(config)
    
    # Stage to all nodes
    all_nodes = config['nodes']['servers'] + config['nodes']['agents']
    
    for node in all_nodes:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Handle sudo password if provided
            connect_kwargs = {
                'hostname': node["ip"],
                'username': node["user"],
                'key_filename': node["ssh_key"],
                'timeout': 60
            }
            
            ssh.connect(**connect_kwargs)
            
            log_message(f"Staging bundles to {node['hostname']}...")
            if bundle_manager.stage_bundles_to_node(ssh, node, 'server' if node in config['nodes']['servers'] else 'agent'):
                log_success(f"✅ Bundles staged to {node['hostname']}")
            else:
                log_error(f"❌ Failed to stage bundles to {node['hostname']}")
            
            ssh.close()
            
        except Exception as e:
            log_error(f"Failed to stage bundles to {node['hostname']}: {e}")

def show_deployment_plan(cfg):
    """Display deployment plan for dry run"""
    deployment = cfg['deployment']
    k8s_dist = deployment.get('k8s_distribution', 'rke2')
    airgap_enabled = deployment.get('airgap', {}).get('enabled', True)
    
    click.echo(f"\nDeployment Plan:")
    click.echo(f"  Kubernetes Distribution: {k8s_dist}")
    click.echo(f"  Default OS: {deployment['os']['type']} {deployment['os']['version']}")
    click.echo(f"  Cluster Name: {cfg['cluster'][k8s_dist]['name']}")
    click.echo(f"  Airgapped: {'Yes' if airgap_enabled else 'No'}")
    
    if airgap_enabled:
        local_registry = deployment.get('airgap', {}).get('local_registry', 'Not configured')
        click.echo(f"  Local Registry: {local_registry}")
    
    click.echo(f"\n  Server Nodes ({len(cfg['nodes']['servers'])}):")
    for i, node in enumerate(cfg['nodes']['servers']):
        role = "First Server" if i == 0 else "Server"
        node_os = node.get('os_override', deployment['os'])
        user_info = f"{node['user']}@{node['ip']}"
        if node['user'] != 'root':
            user_info += " (sudo)"
        click.echo(f"    - {node['hostname']} ({user_info}) - {role} - {node_os['type']} {node_os['version']}")
    
    click.echo(f"\n  Agent Nodes ({len(cfg['nodes']['agents'])}):")
    for node in cfg['nodes']['agents']:
        node_os = node.get('os_override', deployment['os'])
        gpu_status = "GPU-enabled" if node.get('gpu_enabled') else "Standard"
        user_info = f"{node['user']}@{node['ip']}"
        if node['user'] != 'root':
            user_info += " (sudo)"
        click.echo(f"    - {node['hostname']} ({user_info}) - {gpu_status} - {node_os['type']} {node_os['version']}")
    
    # Show bundle locations
    # *Update*
    if airgap_enabled:
        click.echo(f"\n  Required Bundles:")
        if k8s_dist == 'rke2':
            rke2_config = deployment.get('rke2', {})
            bundles = [
                ('Airgap Bundle', rke2_config.get('airgap_bundle_path'))
                # ('Images Bundle', rke2_config.get('images_bundle_path')),
                # ('Install Script', rke2_config.get('install_script_path'))
            ]
            for name, path in bundles:
                if path:
                    status = "✅" if os.path.exists(path) else "❌"
                    click.echo(f"    {status} {name}: {path}")

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
    airgap_enabled = deployment.get('airgap', {}).get('enabled', True)
    
    # Count total nodes
    total_nodes = len(cfg['nodes']['servers']) + len(cfg['nodes']['agents'])
    
    click.echo(colorama.Fore.RED + f"Preparing to uninstall {k8s_dist.upper()} from " + 
              colorama.Fore.YELLOW + f"{cfg['cluster'][k8s_dist]['name']}" + 
              colorama.Fore.RED + f" ({total_nodes} nodes)")
    
    if not force:
        confirm = click.confirm(colorama.Fore.RED + f'Are you sure you want to uninstall {k8s_dist.upper()} from all nodes?')
        if not confirm:
            click.echo(colorama.Fore.CYAN + "Uninstall cancelled.")
            return
    
    # Get distribution handler for proper uninstall
    try:
        if airgap_enabled:
            dist_handler = get_airgapped_distribution_handler(k8s_dist)
        else:
            dist_handler = get_distribution_handler(k8s_dist)
    except Exception as e:
        log_error(f"Handler error: {e}")
        return
    
    uninstall_cluster(cfg, dist_handler)
    
    log_success(f"✅ {k8s_dist.upper()} uninstallation complete for cluster '{cfg['cluster'][k8s_dist]['name']}'")
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
    
    click.echo(colorama.Fore.CYAN + "\nAirgapped Environment Features:")
    features = [
        "Local container registry support",
        "Offline bundle staging",
        "Non-root user deployment with sudo",
        "Local package bundle installation",
        "GPU support in disconnected environments"
    ]
    for feature in features:
        click.echo(f"  • {feature}")

@cli.command()
@click.option('--distribution', '-d', type=click.Choice(SUPPORTED_DISTRIBUTIONS), 
              help='Generate config for specific distribution')
@click.option('--os', '-o', type=click.Choice(SUPPORTED_OS), 
              help='Generate config for specific OS')
@click.option('--airgapped', is_flag=True, default=True,
              help='Generate airgapped configuration (default: true)')
@click.option('--output', default='generated-config.yml', 
              help='Output file name (default: generated-config.yml)')
def generate_config(distribution, os, airgapped, output):
    """Generate a sample configuration file for airgapped environments"""
    from deploy.config_generator import generate_sample_config
    
    click.echo(colorama.Fore.CYAN + f"Generating sample airgapped configuration...")
    
    try:
        generate_sample_config(
            distribution=distribution or 'rke2',
            os_type=os or 'rhel',
            airgapped=airgapped,
            output_file=output
        )
        log_success(f"✅ Sample configuration generated: {output}")
        
        click.echo(colorama.Fore.CYAN + "\nNext steps:")
        click.echo(colorama.Fore.YELLOW + f"1. Edit {output} with your specific environment details")
        click.echo(colorama.Fore.YELLOW + f"2. Ensure all bundle paths point to your staged files")
        click.echo(colorama.Fore.YELLOW + f"3. Update node IPs, usernames, and SSH keys")
        click.echo(colorama.Fore.YELLOW + f"4. Configure your local registry settings")
        click.echo(colorama.Fore.YELLOW + f"5. Run: python main.py deploy -c {output} --dry-run")
        
    except Exception as e:
        log_error(f"Failed to generate config: {e}")

@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
def validate(config):
    """Validate airgapped environment and configuration"""
    try:
        cfg = load_config(config)
        
        click.echo(colorama.Fore.CYAN + "Running comprehensive validation...")
        
        validator = AirgapValidator(cfg)
        if validator.run_full_validation():
            log_success("✅ All validations passed - ready for deployment!")
        else:
            log_error("❌ Validation failed - please fix issues before deployment")
            
    except Exception as e:
        log_error(f"Validation error: {e}")

@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
def stage_bundles(config):
    """Stage bundles to all nodes without deploying"""
    try:
        cfg = load_config(config)
        
        # Get distribution handler
        deployment = cfg['deployment']
        k8s_dist = deployment.get('k8s_distribution', 'rke2')
        airgap_enabled = deployment.get('airgap', {}).get('enabled', True)
        
        if airgap_enabled:
            dist_handler = get_airgapped_distribution_handler(k8s_dist)
        else:
            log_error("Bundle staging is only for airgapped deployments")
            return
        
        click.echo(colorama.Fore.CYAN + "Staging bundles to all nodes...")
        stage_bundles_to_all_nodes(cfg, dist_handler)
        log_success("✅ Bundle staging completed")
        
    except Exception as e:
        log_error(f"Bundle staging error: {e}")

@cli.command()
@click.option('--config', '-c', required=True, help='Path to config.yml')
@click.option('--node', help='Check specific node (hostname or IP)')
def health_check(config, node):
    """Run health checks on deployed cluster"""
    try:
        cfg = load_config(config)
        
        deployment = cfg['deployment']
        k8s_dist = deployment.get('k8s_distribution', 'rke2')
        airgap_enabled = deployment.get('airgap', {}).get('enabled', True)
        
        if airgap_enabled:
            dist_handler = get_airgapped_distribution_handler(k8s_dist)
        else:
            dist_handler = get_distribution_handler(k8s_dist)
        
        if node:
            # Check specific node
            target_node = None
            for n in cfg['nodes']['servers'] + cfg['nodes']['agents']:
                if n['hostname'] == node or n['ip'] == node:
                    target_node = n
                    break
            
            if not target_node:
                log_error(f"Node not found: {node}")
                return
            
            if post_install_health_check(target_node, dist_handler):
                log_success(f"✅ Health check passed for {target_node['hostname']}")
            else:
                log_error(f"❌ Health check failed for {target_node['hostname']}")
        else:
            # Check all server nodes
            all_passed = True
            for server_node in cfg['nodes']['servers']:
                if post_install_health_check(server_node, dist_handler):
                    log_success(f"✅ Health check passed for {server_node['hostname']}")
                else:
                    log_error(f"❌ Health check failed for {server_node['hostname']}")
                    all_passed = False
            
            if all_passed:
                log_success("✅ All health checks passed")
            else:
                log_error("❌ Some health checks failed")
                
    except Exception as e:
        log_error(f"Health check error: {e}")

if __name__ == "__main__":
    cli()