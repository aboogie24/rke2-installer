import paramiko
import colorama
from .utils import log_message, log_error, log_success, log_warning

def post_install_health_check(node):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=node['ip'],
            username=node['user'],
            key_filename=node['ssh_key']
        )

        log_message(node, "Running post-install RKE2 status check...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active rke2-server || systemctl is-active rke2-agent")
        status = stdout.read().decode().strip()
        if status == "active":
            log_success(node, "✅ RKE2 is running.")
        else:
            log_error(node, "❌ RKE2 is not active. Check logs with 'journalctl -u rke2-server -f'")

        stdin, stdout, stderr = ssh.exec_command("echo {node['password']} | sudo -S /var/lib/rancher/rke2/bin/kubectl get nodes --kubeconfig /etc/rancher/rke2/rke2.yaml")
        result = stdout.read().decode()
        error = stderr.read().decode()
        if result:
            log_message(node, "🧩 Cluster Nodes:", details=f"\n{result}")
        elif error:
            log_warning(node, "⚠️ Unable to get nodes:", details=error)

        ssh.close()
    except Exception as e:
        log_error(node, "Error checking health:", details=str(e))