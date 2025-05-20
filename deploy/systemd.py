import colorama
import click
from .utils import log_message, log_error, log_success, log_warning, serverToken

def configure_systemd(ssh, extract_path, is_server, server_ip, node):
    global serverToken
    service_type = "server" if is_server else "agent"
    service_file = f"{extract_path}/systemd/rke2-{service_type}.service"
    target_path = f"/etc/systemd/system/rke2-{service_type}.service"

    commands = [
        f"sudo cp {service_file} {target_path}",
        "sudo systemctl daemon-reexec",
        "sudo systemctl daemon-reload",
        f"sudo systemctl enable rke2-{service_type}.service"
    ]

    if service_type == 'agent':
        log_message(node, "Running agent connection...")
        agent_connection(ssh, serverToken, server_ip, node)

    if service_type == 'server': 
        log_message(node, "Configuring firewall rules...")
        firewall_rules = [
            "sudo firewall-cmd --permanent --add-port=9345/tcp",
            "sudo firewall-cmd --permanent --add-port=6443/tcp",
            "sudo firewall-cmd --permanent --add-port=8472/udp",
            "sudo firewall-cmd --permanent --add-port=10250/tcp",
            "sudo firewall-cmd --reload"
        ]
        commands.extend(firewall_rules)

    commands.append(f"sudo systemctl start rke2-{service_type}.service")
    commands.append(f"sudo systemctl status rke2-{service_type}.service --no-pager")

    for cmd in commands:
        log_message(node, "Executing:", details=cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode()
            log_error(node, f"Error running '{cmd}':", details=err)
        else:
            cmd_output = stdout.read().decode()
            if 'status' in cmd:
                log_message(node, "Command output:", details=f"\n{cmd_output}")
            
    if service_type == 'server': 
        log_message(node, "Retrieving node token...")
        serverToken = get_server_token(ssh, node) 

def agent_connection(ssh, server_token, server_ip, node):
    try:
        if not server_token:
            log_warning(node, "Warning: Server token is empty or not retrieved yet!")
            return
            
        config_content = f"""server: https://{server_ip}:9345
token: {server_token}
""" 
        cmd = f"sudo mkdir -p /etc/rancher/rke2 && echo '{config_content}' | sudo tee /etc/rancher/rke2/config.yaml > /dev/null"

        log_message(node, "Creating agent config with:", details=f"\n{config_content}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            log_success(node, "Agent config.yaml created successfully.")
        else:
            log_error(node, "Error creating agent config.yaml:", details=stderr.read().decode())
    except Exception as e:
        log_error(node, "Failed to configure agent:", details=str(e))

def get_server_token(ssh, node):
    try:
        # Execute the command to read the token
        stdin, stdout, stderr = ssh.exec_command("sudo cat /var/lib/rancher/rke2/server/node-token")
        
        # Read the output and error streams
        node_token = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8')
        
        # Check if there was an error
        if error:
            log_error(node, "Error retrieving node token:", details=error)
            return None
        
        # Check if the token was retrieved
        if not node_token:
            log_warning(node, "Warning: Node token is empty")
            return None
            
        log_success(node, "Successfully retrieved node token:", details=f"{node_token[:10]}...")
        return node_token

    except Exception as e:
        log_error(node, "Exception retrieving node token:", details=str(e))
        return None