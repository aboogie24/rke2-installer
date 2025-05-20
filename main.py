#!/usr/bin/env python3
import click
import yaml
import colorama
from deploy.node import setup_node
from deploy.health import post_install_health_check

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
def deploy(config):
    """Deploy RKE2 Cluster"""
    cfg = load_config(config)

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

if __name__ == "__main__":
    cli()