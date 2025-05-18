import click
import yaml
import subprocess
import paramiko
from pathlib import Path

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

    click.echo(f"Deploying RKE2 cluster: {cfg['cluster']['name']}")

    # Server nodes
    for node in cfg['nodes']['servers']:
        click.echo(f"Setting up server: {node['hostname']} ({node['ip']})")
        setup_node(node, cfg, is_server=True)

    # Agent nodes
    for node in cfg['nodes']['agents']:
        click.echo(f"Setting up agent: {node['hostname']} ({node['ip']})")
        setup_node(node, cfg, is_server=False)

def setup_node(node, cfg, is_server):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Depending on how big the bundle is change this path
    remote_bundle_path = "/tmp/rke2-airgapped-bundle.tar.gz"
    extract_path = cfg['cluster']['tar_extract_path']

    try:
        ssh.connect(
            hostname=node['ip'],
            username=node['user'],
            key_filename=node['ssh_key']
        )
        sftp = ssh.open_sftp()

        # Example: Copy tarball to node
        click.echo(f"Uploading rke2 bundle to  {node['hostname']}...") 
        sftp.put(cfg['cluster']['airgap_bundle_path'], remote_bundle_path)

        # Extract, install etc. (will be expanded later)
        click.echo(f"Extracting bundle on node {node['hostname']}...") 
        ssh.exec_command(f"mkdir -p {cfg['cluster']['tar_extract_path']} && tar -xvzf {remote_bundle_path} -C {extract_path}")

        # Install RPMs
        click.echo(f"Installing RKE2 RPMs on {node['hostname']}...")
        rpm_install_cmd = f"yum install -y {cfg['cluster']['rke2_rpm_path']}/*.rpm"
        stdin, stdout, stderr = ssh.exec_command(rpm_install_cmd)

        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            click.echo(f"[{node['hostname']}] RPMs installed successfully.")
        else:
            error_output = stderr.read().decode()
            click.echo(f"[{node['hostname']}] RPM installation failed:\n{error_output}")
        
        sftp.close()
        ssh.close()
        click.echo(f"[{node['hostname']}] Extraction complete")

    except Exception as e:
        click.echo(f"Error setting up node {node['hostname']}: {e}")

if __name__ == "__main__":
    cli()
