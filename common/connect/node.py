import paramiko
import logging 
import os

from deploy.utils import log_message, log_error, log_success

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


def connect_node(node):
    """Establish SSH connection to a node"""
    log_message("Loading Key")
    pkey = load_private_key(node['ssh_key'])
    log_message(f"{pkey}")
    log_message(f"Connecting to {node['hostname']} at {node['ip']}...")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        paramiko.util.log_to_file("paramiko_debug.log")
        ssh.connect(
            hostname=node['ip'],
            username=node['user'],
            pkey=pkey,
            # key_filename=node['ssh_key'],
            look_for_keys=False,
            allow_agent=False
        )
        log_message(f"Connected to {node['hostname']}")
        return ssh
    except paramiko.AuthenticationException as e:
        log_error(f"Authentication failed for {node['hostname']}: {e}")
        return None
    except paramiko.SSHException as e:
        log_error(f"SSH error for {node['hostname']}: {e}")
        return None
    except Exception as e:
        log_error(f"Failed to connect to {node['hostname']}: {e}")
        return None
