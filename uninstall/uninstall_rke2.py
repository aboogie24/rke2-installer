import click
import yaml
import colorama
import paramiko

from deploy.utils import log_message, log_error, log_success, log_warning, run_ssh_command


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
        
        log_message(node, "Connected to", details=node['hostname'])
        
        service_type = "server" if is_server else "agent"
        sudo_password = node.get('sudo_password', '')
        
        # Step 1: Stop and disable the RKE2 service
        log_message(node, f"Stopping RKE2 {service_type} service...")
        commands = [
            f"systemctl stop rke2-{service_type}",
            f"systemctl disable rke2-{service_type}"
        ]
        
        for cmd in commands:
            stdout, stderr, exit_code = run_ssh_command(
                ssh, cmd, return_output=True, sudo=True, sudo_password=sudo_password
            )
            if exit_code != 0:
                log_warning(node, f"Warning during command '{cmd}':", details=stderr)
        
        # Step 2: Run the uninstall script
        log_message(node, "Running RKE2 uninstall script...")
        uninstall_paths = [
            "/usr/local/bin/rke2-uninstall.sh",  # Tarball installation
            "/usr/bin/rke2-uninstall.sh"         # RPM installation
        ]
        
        uninstall_success = False
        for script_path in uninstall_paths:
            stdout, stderr, exit_code = run_ssh_command(
                ssh, f"test -f {script_path} && echo 'exists'", return_output=True
            )
            if 'exists' in stdout:
                stdout, stderr, exit_code = run_ssh_command(
                    ssh, script_path, return_output=True, sudo=True, sudo_password=sudo_password
                )
                if exit_code == 0:
                    log_success(node, f"Uninstall script at {script_path} executed successfully")
                    uninstall_success = True
                    break
                else:
                    log_error(node, f"Uninstall script failed:", details=stderr)
        
        if not uninstall_success:
            log_warning(node, "Uninstall script not found, attempting manual cleanup...")
        
        # Step 3: Additional cleanup for any left behind files
        log_message(node, "Cleaning up remaining RKE2 files and directories...")
        cleanup_commands = [
            "rm -rf /var/lib/rancher/rke2",
            "rm -rf /etc/rancher/rke2",
            "rm -rf /var/lib/kubelet",
            "rm -rf /opt/rke2",
            "rm -f /usr/local/bin/rke2",
            "rm -f /usr/local/bin/kubectl",
            "rm -f /usr/bin/rke2",
            "rm -f /etc/systemd/system/rke2-*.service",
            "rm -f /usr/share/rke2"
        ]
        
        for cmd in cleanup_commands:
            run_ssh_command(ssh, cmd, sudo=True, sudo_password=sudo_password)
            # Not checking exit code for cleanup - some files might not exist
        
        # Step 4: Remove network interfaces
        log_message(node, "Cleaning up network interfaces...")
        network_commands = [
            "ip link delete flannel.1 2>/dev/null || true",
            "ip link delete cni0 2>/dev/null || true",
            "ip link delete vxlan.calico 2>/dev/null || true"
        ]
        
        for cmd in network_commands:
            run_ssh_command(ssh, cmd, sudo=True, sudo_password=sudo_password)
        
        # Step 5: Reset firewall rules if it's a server
        if is_server:
            log_message(node, "Resetting firewall rules...")
            firewall_commands = [
                "firewall-cmd --permanent --remove-port=9345/tcp || true",
                "firewall-cmd --permanent --remove-port=6443/tcp || true", 
                "firewall-cmd --permanent --remove-port=8472/udp || true",
                "firewall-cmd --permanent --remove-port=10250/tcp || true",
                "firewall-cmd --reload || true"
            ]
            
            for cmd in firewall_commands:
                run_ssh_command(ssh, cmd, sudo=True, sudo_password=sudo_password)
        
        log_success(node, f"RKE2 {service_type} uninstalled successfully")
        ssh.close()
        
    except Exception as e:
        log_error(node, f"Error uninstalling RKE2:", details=str(e))
