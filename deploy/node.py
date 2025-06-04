import click
import os
import paramiko
import colorama
from .utils import log_message, log_error, log_success, log_warning
from .config import write_server_config_yaml, configure_registry
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
        stdin, stdout, stderr = ssh.exec_command(f"echo {node['password']} | sudo -S  mkdir -p {extract_path}")
        err = stderr.read().decode('utf-8')
        out = stdout.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()

        if exit_code == 0: 
            log_success(node, "Creating Extraction directory Complete")
        else: 
            log_error(node, "Error creating directory:", details=err)

        # Extract preserving path structure but without top-level directory
        extract_cmd = f"echo {node['password']} | sudo -S  tar -xzf {remote_bundle_path} --strip-components=1 -C {extract_path}"
        log_message(node, "Extracting bundle...")
        
        # Execute with output capture
        stdin, stdout, stderr = ssh.exec_command(extract_cmd)
        
        # Wait for command to complete and show output
        extraction_output = stdout.read().decode('utf-8')
        extraction_error = stderr.read().decode('utf-8')

        if extraction_error:
            log_error(node, "Error during extraction:", details=extraction_error)
            
        else:
            log_success(node, "Extraction completed successfully")
            
        # Verify extraction by listing the target directory
        stdin, stdout, stderr = ssh.exec_command(f"ls -la {extract_path}")
        directory_contents = stdout.read().decode('utf-8')
        log_message(node, "Extracted contents:", details=f"\n{directory_contents}")

        # Configure Registry
        configure_registry(ssh, node, cfg)

        # Install RPMs
        # This is hardcoded as of right now
        # Update to make this more dynamic in the future
        log_message(node, "Installing RKE2 RPMs...")
        # rpm_install_cmd = f"echo {node['password']} | sudo -S  yum install -y {extract_path}/rpm/*.rpm"
        rpm_install_cmds = [
            f"echo {node['password']} | sudo -S rpm -ivh {extract_path}/rpms/rke2-selinux-0.18-1.el8.noarch.rpm",
            f"echo {node['password']} | sudo -S rpm -ivh {extract_path}/rpms/rke2-common-1.32.3~rke2r1-0.el8.x86_64.rpm",
            f"echo {node['password']} | sudo -S rpm -ivh {extract_path}/rpms/rke2-server-1.32.3~rke2r1-0.el8.x86_64.rpm",
            f"echo {node['password']} | sudo -S rpm -ivh {extract_path}/rpms/rke2-agent-1.32.3~rke2r1-0.el8.x86_64.rpm"
        ]
        # stdin, stdout, stderr = ssh.exec_command(rpm_install_cmd)
        for cmd in rpm_install_cmds:
            log_message(node, "Installing RPM", details=cmd)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code != 0:
                err = stderr.read().decode()
                log_error(node, f"Failed to run: {cmd}", details=err)
            else:
                cmd_output = stdout.read().decode().strip()
                if cmd_output and "version" in cmd:
                    log_message(node, "Installed:", details=f"\n{cmd_output}")

        prepare_binary(ssh, node)

        server_ip = cfg['nodes']['servers'][0]['ip']

        if is_server:
            log_message(node, "Writing RKE2 config.yaml...")
            write_server_config_yaml(ssh, node, is_first_server, cfg)

        # After RPM install
        log_message(node, f"Configuring systemd service for", details=f"{'server' if is_server else 'agent'}")
        firewalld = cfg['cluster']['firewalld']
        configure_systemd(ssh, extract_path, is_server, server_ip, node, firewalld)

        if is_server and is_first_server:
            # Wait for RKE2 to be fully operational
            log_message(node, "Waiting for RKE2 to be ready before deploying kubectl and other tools...")
            stdin, stdout, stderr = ssh.exec_command(
                f"echo {node['password']} | sudo -S cat /etc/rancher/rke2/rke2.yaml"
            )
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code == 0:
                log_message(node, "RKE2 configuration detected, deploying kubectl...")
                deploy_kubectl(ssh, node, extract_path)
                if 'extra_tools' in cfg and cfg['extra_tools']:
                    log_message(node, f"Installing additional tools: {', '.join(cfg['extra_tools'])}")
                    
                    if 'k9s' in cfg['extra_tools']:
                        install_k9s(ssh, node, extract_path)
                    if 'helm' in cfg['extra_tools']:
                        install_helm(ssh, node, extract_path)
                    if 'flux' in cfg['extra_tools']:
                        install_flux(ssh, node, extract_path)
            else:
                log_warning(node, "Timed out waiting for RKE2 configuration, skipping kubectl deployment")
            
        
        sftp.close()
        ssh.close()

    except Exception as e:
        log_error(node, "Error setting up node:", details=str(e))

def prepare_binary(ssh, node):
    """Prepare the RKE2 binary and images directory"""
    log_message(node, "Preparing rke2 binary...")

    list_cmd = f"echo {node['password']} | sudo -S ls -lart /opt/rke2/images"
    log_message(node, "Executing: ", details=list_cmd)
    stdin, stdout, stderr = ssh.exec_command(list_cmd)
    files_output = stdout.read().decode('utf-8').strip()

    if not files_output: 
        log_error(node, "Unable to find Images")
        
    commands = [
        f"echo {node['password']} | sudo -S  cp /opt/rke2/rke2/bin/rke2 /usr/local/bin/rke2",
        f"echo {node['password']} | sudo -S  chmod +x /usr/local/bin/rke2",
        f"echo {node['password']} | sudo -S  mkdir -p /var/lib/rancher/rke2/agent/images",
        f"echo {node['password']} | sudo -S  ls -lart /opt/rke2/images/",
        # f"bash -c \ 'echo {node['password']} | sudo -S  cp /opt/rke2/images/*.tar /var/lib/rancher/rke2/agent/images/'",
        # f"echo {node['password']} | sudo -S  find /opt/rke2/images/ -name '*.tar' -exec cp {} /var/lib/rancher/rke2/agent/images/ \\;",
        f"echo {node['password']} | sudo -S  ls -lart /var/lib/rancher/rke2/agent/images/",
        # f"echo {node['password']} | sudo -S  chmod 644 /var/lib/rancher/rke2/agent/images/rke2-images.linux-amd64.tar.zst"
    ]
    for cmd in commands:
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()
        # log_success(node, f"Successful command {out}")
        if exit_code != 0:
            err = stderr.read().decode()
            log_error(node, f"Failed to run: {cmd}", details=err)
    
    # Start moving images
    log_message(node, "Moving Images to correct location")
    for f in files_output.split('\n'):
        file_name = f.split()[-1]
        
        cmd = f'echo {node['password']} | sudo -S  cp /opt/rke2/images/{file_name} /var/lib/rancher/rke2/agent/images/'
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        

def deploy_kubectl(ssh, node, extract_path):
    """Deploy kubectl from the RKE2 bundle to the first server node"""
    log_message(node, "Deploying kubectl from RKE2 bundle...")
    
    commands = [
        # Copy kubectl binary to /usr/local/bin
        f"echo {node['password']} | sudo -S  cp {extract_path}/bin/kubectl /usr/local/bin/kubectl",
        # Update Path
        "export PATH=/usr/local/bin:$PATH",
        # Make it executable
        f"echo {node['password']} | sudo -S  chmod +x /usr/local/bin/kubectl",
        # Create symbolic link to the RKE2 kubeconfig for the current user
        "mkdir -p $HOME/.kube",
        f"echo {node['password']} | sudo -S  cp /etc/rancher/rke2/rke2.yaml $HOME/.kube/config",
        f"echo {node['password']} | sudo -S  chown $(id -u):$(id -g) $HOME/.kube/config",
        # Make kubectl usable for root as well
        f"echo {node['password']} | sudo -S  mkdir -p /root/.kube",
        f"echo {node['password']} | sudo -S  cp /etc/rancher/rke2/rke2.yaml /root/.kube/config",
        # Test kubectl functionality
        f"echo {node['password']} | sudo -S kubectl version --client"
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

def install_k9s(ssh, node, extract_path):
    """Install k9s CLI tool from the RKE2 bundle"""
    log_message(node, "Installing k9s Kubernetes CLI tool...")
    
    # # Check if k9s exists in the bundle
    # log_message(node, f"Command: test -f {extract_path}/bin/k9s && echo 'exists")
    # stdin, stdout, stderr = ssh.exec_command(f"test -f {extract_path}/bin/k9s && echo 'exists'")
    # if stdout.read().decode().strip() != 'exists':
    #     log_warning(node, "k9s binary not found in bundle. Skipping installation.")
    #     return False
    
    commands = [
        f"echo {node['password']} | sudo -S  cp {extract_path}/bin/k9s /usr/local/bin/k9s",
        f"echo {node['password']} | sudo -S  chmod +x /usr/local/bin/k9s",
        # "mkdir -p ~/.kube",
        # "echo {node['password']} | sudo -S  cp /etc/rancher/rke2/rke2.yaml ~/.kube/config",
        # "echo {node['password']} | sudo -S  chown $(id -u):$(id -g) ~/.kube/config",
        # "chmod 600 ~/.kube/config",
        "k9s version || echo 'k9s installed but version check failed'"
    ]
    
    for cmd in commands:
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode()
            log_warning(node, f"Command '{cmd}' may have issues:", details=err)
        else:
            output = stdout.read().decode().strip()
            if output and 'version' in cmd:
                log_message(node, "k9s version info:", details=output)
    
    log_success(node, "k9s Kubernetes UI tool installed successfully")
    return True

def install_helm(ssh, node, extract_path):
    """Install Helm from the airgapped bundle"""
    log_message(node, "Installing Helm package manager...")
    
    # # Check if helm exists in the bundle
    # stdin, stdout, stderr = ssh.exec_command(f"test -f {extract_path}/bin/helm && echo 'exists'")
    # if stdout.read().decode().strip() != 'exists':
    #     log_warning(node, "Helm binary not found in bundle. Skipping installation.")
    #     return False
    
    commands = [
        f"echo {node['password']} | sudo -S  cp {extract_path}/bin/helm /usr/local/bin/helm",
        f"echo {node['password']} | sudo -S  chmod +x /usr/local/bin/helm",
        "helm version || echo 'Helm installed but version check failed'",
        # Initialize Helm (optional)
        "helm repo list || true"
    ]
    
    for cmd in commands:
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode()
            log_warning(node, f"Command '{cmd}' may have issues:", details=err)
        else:
            output = stdout.read().decode().strip()
            if output and 'version' in cmd:
                log_message(node, "Helm version info:", details=output)
    
    log_success(node, "Helm package manager installed successfully")
    return True

def install_flux(ssh, node, extract_path):
    """Install Flux GitOps CLI from the airgapped bundle"""
    log_message(node, "Installing Flux GitOps CLI...")
    
    # # Check if flux exists in the bundle
    # stdin, stdout, stderr = ssh.exec_command(f"test -f {extract_path}/bin/flux && echo 'exists'")
    # if stdout.read().decode().strip() != 'exists':
    #     log_warning(node, "Flux binary not found in bundle. Skipping installation.")
    #     return False
    
    commands = [
        f"echo {node['password']} | sudo -S  cp {extract_path}/bin/flux /usr/local/bin/flux",
        f"echo {node['password']} | sudo -S  chmod +x /usr/local/bin/flux",
        "flux --version || echo 'Flux installed but version check failed'"
    ]
    
    for cmd in commands:
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode()
            log_warning(node, f"Command '{cmd}' may have issues:", details=err)
        else:
            output = stdout.read().decode().strip()
            if output and 'version' in cmd:
                log_message(node, "Flux version info:", details=output)
    
    # Add auto-completion (optional)
    completion_cmds = [
        "mkdir -p ~/.config/fish/completions",
        "flux completion fish > ~/.config/fish/completions/flux.fish || true",
        "echo 'source <(flux completion bash)' >> ~/.bashrc || true"
    ]
    
    for cmd in completion_cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd)
    
    log_success(node, "Flux GitOps CLI installed successfully")
    log_message(node, "Note: For a complete Flux installation in airgapped environments, manual bootstrap steps are required.")
    return True
