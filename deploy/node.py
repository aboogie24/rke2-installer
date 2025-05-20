import click
import os
import paramiko
import colorama
from .utils import log_message, log_error, log_success, log_warning
from .config import write_server_config_yaml
from .systemd import configure_systemd

def setup_node(node, cfg, is_server, is_first_server=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Depending on how big the bundle is change this path
    remote_bundle_path = "/tmp/rke2-airgap-bundle.tar.gz"
    extract_path = cfg['cluster']['tar_extract_path']

    try:
        if not os.path.exists(cfg['cluster']['airgap_bundle_path']): 
            log_error(node, f"Error: Source file {cfg['cluster']['airgap_bundle_path']} does not exist!")
            return False
        
        log_message(node, "Connecting to", details=f"{node['ip']}...")
        ssh.connect(
            hostname=node['ip'],
            username=node['user'],
            key_filename=node['ssh_key']
        )

        log_message(node, "Opening SFTP connection...")
        sftp = ssh.open_sftp()

        # Get file size for progress tracking
        file_size = os.path.getsize(cfg['cluster']['airgap_bundle_path'])
        log_message(node, "Uploading", details=f"{file_size/1024/1024:.2f} MB")

        # Upload with progress callback for large files
        def progress_callback(transferred, total):
            percentage = (transferred / total) * 100
            if percentage % 10 < 0.1:  # Report every ~10%
                log_message(node, "Transfer progress:", details=f"{percentage:.1f}% ({transferred/1024/1024:.2f} MB)")

        # Perform the actual file transfer
        sftp.put(
            cfg['cluster']['airgap_bundle_path'], 
            remote_bundle_path,
            callback=progress_callback if file_size > 10*1024*1024 else None  # Only use callback for files >10MB
        )

        # Verify the file exists on the remote system
        try:
            sftp.stat(remote_bundle_path)
            log_success(node, "Successfully uploaded bundle")
            
        except IOError:
            log_error(node, "Failed to verify file on remote system!")
            return False
        
        # First, check the content structure of the tar file
        log_message(node, "Checking tar file structure...")
        stdin, stdout, stderr = ssh.exec_command(f"tar -tf {remote_bundle_path} | head -10")
        tar_contents = stdout.read().decode('utf-8')
        log_message(node, "Tar contents (first 10 entries):", details=f"\n{tar_contents}")

        # Create the target directory and ensure permissions
        log_message(node, "Creating extraction directory...")
        stdin, stdout, stderr = ssh.exec_command(f"sudo mkdir -p {extract_path}")
        err = stderr.read().decode('utf-8')
        if err:
            log_error(node, "Error creating directory:", details=err)

        # Extract preserving path structure but without top-level directory
        extract_cmd = f"sudo tar -xzf {remote_bundle_path} --strip-components=1 -C {extract_path}"
        log_message(node, "Extracting bundle...")
        
        # Execute with output capture
        stdin, stdout, stderr = ssh.exec_command(extract_cmd)
        
        # Wait for command to complete and show output
        extraction_output = stdout.read().decode('utf-8')
        extraction_error = stderr.read().decode('utf-8')

        if extraction_error:
            log_error(node, "Error during extraction:", details=extraction_error)
            return False
        else:
            log_success(node, "Extraction completed successfully")
            
        # Verify extraction by listing the target directory
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {extract_path}")
        directory_contents = stdout.read().decode('utf-8')
        log_message(node, "Extracted contents:", details=f"\n{directory_contents}")

        # Install RPMs
        log_message(node, "Installing RKE2 RPMs...")
        rpm_install_cmd = f"sudo yum install -y {extract_path}/rpm/*.rpm"
        stdin, stdout, stderr = ssh.exec_command(rpm_install_cmd)

        prepare_binary(ssh, node)

        server_ip = cfg['nodes']['servers'][0]['ip']

        if is_server:
            log_message(node, "Writing RKE2 config.yaml...")
            write_server_config_yaml(ssh, node, is_first_server, cfg)

        # After RPM install
        log_message(node, f"Configuring systemd service for", details=f"{'server' if is_server else 'agent'}")
        configure_systemd(ssh, extract_path, is_server, server_ip, node)

        if is_server and is_first_server:
            # Wait for RKE2 to be fully operational
            log_message(node, "Waiting for RKE2 to be ready before deploying kubectl...")
            stdin, stdout, stderr = ssh.exec_command(
                "timeout 120 bash -c 'until [ -f /etc/rancher/rke2/rke2.yaml ]; do sleep 2; done'"
            )
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code == 0:
                log_message(node, "RKE2 configuration detected, deploying kubectl...")
                deploy_kubectl(ssh, node, extract_path)
            else:
                log_warning(node, "Timed out waiting for RKE2 configuration, skipping kubectl deployment")

        # exit_code = stdout.channel.recv_exit_status()
        # if exit_code == 0:
        #     log_success(node, "RPMs installed successfully.")
        # else:
        #     error_output = stderr.read().decode()
        #     log_error(node, "RPM installation failed:", details=f"\n{error_output}")
        
        sftp.close()
        ssh.close()

    except Exception as e:
        log_error(node, "Error setting up node:", details=str(e))

def prepare_binary(ssh, node):
    """Prepare the RKE2 binary and images directory"""
    log_message(node, "Preparing rke2 binary...")
    commands = [
        "sudo cp /opt/rke2/bin/rke2 /usr/local/bin/rke2",
        "sudo chmod +x /usr/local/bin/rke2",
        "sudo mkdir -p /var/lib/rancher/rke2/agent/images/",
        "sudo cp /opt/rke2/images/rke2-images.linux-amd64.tar.zst /var/lib/rancher/rke2/agent/images/",
        "sudo chmod 644 /var/lib/rancher/rke2/agent/images/rke2-images.linux-amd64.tar.zst"
    ]
    for cmd in commands:
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode()
            log_error(node, f"Failed to run: {cmd}", details=err)

def deploy_kubectl(ssh, node, extract_path):
    """Deploy kubectl from the RKE2 bundle to the first server node"""
    log_message(node, "Deploying kubectl from RKE2 bundle...")
    
    commands = [
        # Copy kubectl binary to /usr/local/bin
        f"sudo cp {extract_path}/bin/kubectl /usr/local/bin/kubectl",
        # Make it executable
        "sudo chmod +x /usr/local/bin/kubectl",
        # Create symbolic link to the RKE2 kubeconfig for the current user
        "mkdir -p $HOME/.kube",
        "sudo cp /etc/rancher/rke2/rke2.yaml $HOME/.kube/config",
        "sudo chown $(id -u):$(id -g) $HOME/.kube/config",
        # Make kubectl usable for root as well
        "sudo mkdir -p /root/.kube",
        "sudo cp /etc/rancher/rke2/rke2.yaml /root/.kube/config",
        # Test kubectl functionality
        "kubectl version --client"
    ]
    
    for cmd in commands:
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            err = stderr.read().decode()
            log_error(node, f"Failed to run: {cmd}", details=err)
        else:
            cmd_output = stdout.read().decode().strip()
            if cmd_output and "version" in cmd:
                log_message(node, "Kubectl version info:", details=f"\n{cmd_output}")
    
    # Verify kubectl works by getting nodes
    log_message(node, "Verifying kubectl functionality...")
    stdin, stdout, stderr = ssh.exec_command("kubectl get nodes")
    exit_code = stdout.channel.recv_exit_status()
    
    if exit_code == 0:
        nodes_output = stdout.read().decode()
        log_success(node, "Kubectl successfully installed and configured:", details=f"\n{nodes_output}")
    else:
        err = stderr.read().decode()
        log_warning(node, "Kubectl installed but test command failed:", details=err)