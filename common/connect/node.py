import paramiko
import logging 
import os
import socket

from deploy.utils import log_message, log_error, log_success, log_warning, log_debug

def load_private_key(key_path, password=None):
    """
    Tries to load any supported private key type (OpenSSH, RSA, ECDSA, Ed25519).
    """
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"SSH key not found at {key_path}")

    loaders = [
        ("Ed25519", paramiko.Ed25519Key),
        ("ECDSA", paramiko.ECDSAKey),
        ("RSA", paramiko.RSAKey),
        ("DSA", paramiko.DSSKey),
    ]

    for name, key_cls in loaders:
        try:
            key = key_cls.from_private_key_file(key_path, password=password)
            logging.info(f"✅ Loaded {name} key from {key_path}")
            return key
        except paramiko.ssh_exception.PasswordRequiredException:
            raise Exception(f"🔒 Key at {key_path} is password protected. Provide a password.")
        except paramiko.ssh_exception.SSHException:
            # Try next format
            continue

    raise Exception(f"❌ Could not load private key: unsupported or invalid format at {key_path}")


def connect_node(node, timeout=30):
    """
    Establish SSH connection to a node with enhanced error handling and validation
    
    Args:
        node: Node dictionary containing connection details (ip, hostname, user, ssh_key)
        timeout: Connection timeout in seconds (default: 30)
    
    Returns:
        paramiko.SSHClient or None if connection failed
    """
    hostname = node.get('hostname', 'unknown')
    ip = node['ip']
    username = node['user']
    ssh_key_path = node['ssh_key']
    port = node.get('port', 22)
    sudo_password = node.get('sudo_password')
    
    try:
        # Validate SSH key exists
        if not os.path.exists(ssh_key_path):
            log_error(f"SSH key not found: {ssh_key_path}")
            return None
        
        # Check SSH key permissions (should be 600 or 400)
        key_perms = oct(os.stat(ssh_key_path).st_mode)[-3:]
        if key_perms not in ['600', '400']:
            log_warning(f"SSH key permissions are {key_perms} for {hostname}, should be 600 or 400")
        
        log_message(f"Loading SSH key for {hostname}...")
        pkey = load_private_key(ssh_key_path)
        log_debug(f"Loaded key type: {type(pkey).__name__}")
        
        log_message(f"Connecting to {hostname} ({username}@{ip}:{port})...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        ssh.connect(
            hostname=ip,
            port=port,
            username=username,
            pkey=pkey,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout
        )
        
        # Test connection with a simple command
        log_debug("Testing SSH connection...")
        stdin, stdout, stderr = ssh.exec_command("echo 'SSH connection test'", timeout=10)
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            log_error(f"SSH connection test failed for {hostname}")
            ssh.close()
            return None
        
        # Test sudo access if password provided
        if sudo_password:
            log_debug("Testing sudo access...")
            test_cmd = f"echo '{sudo_password}' | sudo -S whoami"
            stdin, stdout, stderr = ssh.exec_command(test_cmd, timeout=10)
            exit_code = stdout.channel.recv_exit_status()
            sudo_output = stdout.read().decode('utf-8', errors='replace').strip()
            
            if exit_code != 0 or "root" not in sudo_output:
                log_warning(f"Sudo access test failed for {hostname}")
        
        log_success(f"SSH connection established to {hostname}")
        return ssh
        
    except paramiko.AuthenticationException as e:
        log_error(f"SSH authentication failed for {hostname}: {e}")
    except paramiko.ssh_exception.NoValidConnectionsError as e:
        log_error(f"No valid SSH connection to {hostname}:{port}: {e}")
    except socket.timeout:
        log_error(f"SSH connection timeout to {hostname}:{port}")
    except paramiko.SSHException as e:
        log_error(f"SSH connection error to {hostname}: {e}")
    except Exception as e:
        log_error(f"Unexpected SSH error connecting to {hostname}: {e}")
    
    return None
