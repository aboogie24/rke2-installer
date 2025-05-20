import click
import yaml
import subprocess
import paramiko
import os
import colorama
from pathlib import Path

serverToken=None

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
    for i, node in enumerate(cfg['nodes']['servers']):
        is_first_server = (i == 0)
        click.echo(f"Setting up {'first' if is_first_server else 'joining'} server: {node['hostname']} ({node['ip']})")
        setup_node(node, cfg, is_server=True, is_first_server=is_first_server)

    # Agent nodes
    for node in cfg['nodes']['agents']:
        click.echo(f"Setting up agent: {node['hostname']} ({node['ip']})")
        setup_node(node, cfg, is_server=False)
    
    # Post-install health check
    for node in cfg['nodes']['servers'] + cfg['nodes']['agents']:
        post_install_health_check(node)

def setup_node(node, cfg, is_server, is_first_server=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Depending on how big the bundle is change this path
    remote_bundle_path = "/tmp/rke2-airgap-bundle.tar.gz"
    extract_path = cfg['cluster']['tar_extract_path']

    try:

        if not os.path.exists(cfg['cluster']['airgap_bundle_path']): 
            click.echo(f"Error: Source file {cfg['cluster']['airgap_bundle_path']} does not exist!")
            return False
        
        click.echo(f"Connecting to {node['hostname']} ({node['ip']})...")
        ssh.connect(
            hostname=node['ip'],
            username=node['user'],
            key_filename=node['ssh_key']
        )

        click.echo(f"Opening SFTP connection...")
        sftp = ssh.open_sftp()

        # Get file size for progress tracking
        file_size = os.path.getsize(cfg['cluster']['airgap_bundle_path'])
        click.echo(f"Uploading {file_size/1024/1024:.2f} MB to {node['hostname']}...")

        # Upload with progress callback for large files
        def progress_callback(transferred, total):
            percentage = (transferred / total) * 100
            if percentage % 10 < 0.1:  # Report every ~10%
                click.echo(f"Transfer progress: {percentage:.1f}% ({transferred/1024/1024:.2f} MB)")

        # Perform the actual file transfer
        sftp.put(
            cfg['cluster']['airgap_bundle_path'], 
            remote_bundle_path,
            callback=progress_callback if file_size > 10*1024*1024 else None  # Only use callback for files >10MB
        )

        # Verify the file exists on the remote system
        try:
            sftp.stat(remote_bundle_path)
            click.echo(f"✅ Successfully uploaded bundle to {node['hostname']}")
            
            # Continue with extraction or other operations
            # ...
            
        except IOError:
            click.echo(f"❌ Failed to verify file on remote system!")
            return False
        
        # First, check the content structure of the tar file
        click.echo(f"Checking tar file structure on {node['hostname']}...")
        stdin, stdout, stderr = ssh.exec_command(f"tar -tf {remote_bundle_path} | head -10")
        tar_contents = stdout.read().decode('utf-8')
        click.echo(f"Tar contents (first 10 entries): {tar_contents}")

        # Create the target directory and ensure permissions
        click.echo(f"Creating extraction directory on {node['hostname']}...")
        stdin, stdout, stderr = ssh.exec_command(f"sudo mkdir -p {extract_path}")
        if stderr.read():
            click.echo(f"Error creating directory: {stderr.read().decode('utf-8')}")

        # Option 1: Extract preserving path structure but without top-level directory
        extract_cmd = f"sudo tar -xzf {remote_bundle_path} --strip-components=1 -C {extract_path}"

        # Execute with output capture
        stdin, stdout, stderr = ssh.exec_command(extract_cmd)
        
        # Wait for command to complete and show output
        extraction_output = stdout.read().decode('utf-8')
        extraction_error = stderr.read().decode('utf-8')

        if extraction_error:
            click.echo(f"Error during extraction: {extraction_error}")
            return False
        else:
            click.echo(f"Extraction completed successfully on {node['hostname']}")
            
        # Verify extraction by listing the target directory
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {extract_path}")
        directory_contents = stdout.read().decode('utf-8')
        click.echo(f"Extracted contents: {directory_contents}")

        # Install RPMs
        click.echo(f"Installing RKE2 RPMs on {node['hostname']}...")
        rpm_install_cmd = f"yum install -y {cfg['cluster']['rke2_rpm_path']}/*.rpm"
        stdin, stdout, stderr = ssh.exec_command(rpm_install_cmd)

        def prepare_binary(ssh):
            # Move and set execute permissions for rke2 binary
            commands = [
                "cp /opt/rke2/rke2/bin/rke2 /usr/local/bin/rke2",
                "chmod +x /usr/local/bin/rke2",
                "mkdir -p /var/lib/rancher/rke2/agent/images/",
                "cp /opt/rke2/images/rke2-images.linux-amd64.tar.zst /var/lib/rancher/rke2/agent/images/",
                "chmod 644 /var/lib/rancher/rke2/agent/images/rke2-images.linux-amd64.tar.zst"
            ]
            for cmd in commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    print(f"Failed to run: {cmd}\n{stderr.read().decode()}")
        
        click.echo(f"Preparing rke2 binary on {node['hostname']}...")
        prepare_binary(ssh)

        server_ip = cfg['nodes']['servers'][0]['ip']

        if is_server:
            click.echo(f"Writing RKE2 config.yaml on {node['hostname']}...")
            write_server_config_yaml(ssh, node, is_first_server, cfg)

        # After RPM install
        click.echo(f"Configuring systemd service for {'server' if is_server else 'agent'} on {node['hostname']}...")
        configure_systemd(ssh, extract_path, is_server, server_ip, node)


        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            click.echo(f"[{node['hostname']}] RPMs installed successfully.")
        else:
            error_output = stderr.read().decode()
            click.echo(f"[{node['hostname']}] RPM installation failed:\n{error_output}")
        
        sftp.close()
        ssh.close()

    except Exception as e:
        click.echo(f"Error setting up node {node['hostname']}: {e}")

def post_install_health_check(node):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=node['ip'],
            username=node['user'],
            key_filename=node['ssh_key']
        )

        click.echo(f"Running post-install RKE2 status check on {node['hostname']}...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active rke2-server || systemctl is-active rke2-agent")
        status = stdout.read().decode().strip()
        if status == "active":
            click.echo(f"✅ RKE2 is running on {node['hostname']}.")
        else:
            click.echo(f"❌ RKE2 is not active on {node['hostname']}. Check logs with 'journalctl -u rke2-server -f'")

        stdin, stdout, stderr = ssh.exec_command("/var/lib/rancher/rke2/bin/kubectl get nodes --kubeconfig /etc/rancher/rke2/rke2.yaml")
        result = stdout.read().decode()
        error = stderr.read().decode()
        if result:
            click.echo(f"🧩 Cluster Nodes:\n{result}")
        elif error:
            click.echo(f"⚠️ Unable to get nodes: {error}")

        ssh.close()
    except Exception as e:
        click.echo(f"Error checking health on node {node['hostname']}: {e}")


def configure_systemd(ssh, extract_path, is_server, server_ip, node):
    global serverToken
    service_type = "server" if is_server else "agent"
    service_file = f"{extract_path}/systemd/rke2-{service_type}.service"
    target_path = f"/etc/systemd/system/rke2-{service_type}.service"

    commands = [
        f"cp {service_file} {target_path}",
        "systemctl daemon-reexec",
        "systemctl daemon-reload",
        f"systemctl enable rke2-{service_type}.service"
    ]

    if service_type == 'agent':
        click.echo(f"    Running agent Connection on {node['hostname']}")
        agent_connection(ssh, serverToken, server_ip)

    if service_type == 'server': 
        firewall_rules = [
            "firewall-cmd --permanent --add-port=9345/tcp",
            "firewall-cmd --permanent --add-port=6443/tcp",
            "firewall-cmd --permanent --add-port=8472/udp",
            "firewall-cmd --permanent --add-port=10250/tcp",
            "firewall-cmd --reload"
        ]
        commands.extend(firewall_rules)

    commands.append(f"systemctl start rke2-{service_type}.service")
    commands.append(f"systemctl status rke2-{service_type}.service --no-pager")

    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode()
            print(f"Error running '{cmd}': {err}")
    if service_type == 'server': 
        serverToken = get_server_token(ssh) 

def write_server_config_yaml(ssh, node, is_first_server, cfg):
    config = {
        "token": cfg['cluster']['token'],
        "node-name": node['hostname']
    }

    if is_first_server: 
        config['cluster-init'] = True

    # Dynamically generate tls-san from node info
    tls_san = [node['ip'], node['hostname']]
    if 'domain' in cfg['cluster']: 
        tls_san.append(f"{node['hostname']}.{cfg['cluster']['domain']}")
    config['tls-san'] = tls_san

    optional_fields = [
        "cluster-cidr", "service-cidr", "cni", "disable-network-policy",
        "write-kubeconfig-mode", "kube-apiserver-arg", "container-runtime-endpoint",
        "pause-image", "disable"
    ]

    for key in optional_fields:
        if key in cfg['cluster']:
            config[key] = cfg['cluster'][key]
    
    config_yaml = yaml.dump(config, default_flow_style=False)
    remote_cmd = f"mkdir -p /etc/rancher/rke2 && echo '{config}' > /etc/rancher/rke2/config.yaml"
    stdin, stdout, stderr = ssh.exec_command(remote_cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code == 0:
        click.echo(f"[{node['hostname']}] dynamic server config.yaml written.")
    else:
        click.echo(f"[{node['hostname']}] Failed to write dynamic config.yaml:\n{stderr.read().decode()}")

def agent_connection(ssh, server_token, server_ip):
    try:
        config_content = f"""server: https://{server_ip}:9345
token: {server_token}
""" 
        cmd = f"mkdir -p /etc/rancher/rke2 && echo '{config_content}' > /etc/rancher/rke2/config.yaml"

        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            click.echo("     Agent config.yaml created successfully.")
        else:
            click.echo("Error creating agent config.yaml:\n", stderr.read().decode())
    except Exception as e:
        click.echo(f"     Failed to configure agent: {e}")

def get_server_token(ssh):
    try:
        # Execute the command to read the token
        stdin, stdout, stderr = ssh.exec_command("cat /var/lib/rancher/rke2/server/node-token")
        
        # Read the output and error streams
        node_token = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8')
        
        # Check if there was an error
        if error:
            click.echo(f"Error retrieving node token: {error}")
            return None
        
        # Check if the token was retrieved
        if not node_token:
            click.echo("Warning: Node token is empty")
            return None
            
        click.echo("Successfully retrieved node token")
        return node_token

    except Exception as e:
        click.echo(f"Exception retrieving node token: {str(e)}")
        return None


if __name__ == "__main__":
    cli()
