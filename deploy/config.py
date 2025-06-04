import yaml
import colorama
import click
from .utils import log_message, log_error, log_success

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
        "pause-image", "disable", "airgap", "selinux"
    ]

    for key in optional_fields:
        if key in cfg['cluster']:
            config[key] = cfg['cluster'][key]
    
    # Properly format the config with yaml dump
    config_yaml = yaml.dump(config, default_flow_style=False)
    remote_cmds = [
        f"echo {node['password']} | sudo -S mkdir -p /etc/rancher/rke2",
        f"echo '{config_yaml}' | tee /tmp/config.yaml > /dev/null",
        f"echo {node['password']} | sudo -S cp /tmp/config.yaml /etc/rancher/rke2/config.yaml"
    ]


    log_message(node, "Creating config.yaml with content:", details=f"\n{config_yaml}")
    for cmd in remote_cmds:
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

def configure_registry(ssh, node, cfg):
    """Configure container registry settings including insecure registries"""
    if 'registry' not in cfg.get('cluster', {}):
        return

    registry_config = cfg['cluster']['registry']
    log_message(node, "Configuring container registry settings...")
    
    # Convert the registry config to YAML
    registry_yaml = yaml.dump(registry_config, default_flow_style=False)
    
    # Create the registries.yaml file
    registries_cmds = [
        f"echo {node['password']} | sudo -S mkdir -p /etc/rancher/rke2",
        f"echo '{registry_yaml}' | tee /tmp/registries.yaml", 
        f"echo {node['password']} | sudo -S cp /tmp/registries.yaml /etc/rancher/rke2/registries.yaml "
    ]
#                 f"""echo {node['password']}  | sudo -S bash -c 'cat > /etc/rancher/rke2/registries.yaml << EOF
# {registry_yaml}
# EOF'"""
    
    log_message(node, "Creating registry configuration:")
    log_message(node, "Registry config:", details=f"\n{registry_yaml}")
    
    for cmd in registries_cmds:
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
    
    if exit_code == 0:
        log_success(node, "Registry configuration created successfully")
    else:
        log_error(node, "Failed to create registry configuration:", details=stderr.read().decode())
    
    # Check if we're configuring insecure registries
    insecure_registries = []
    for registry, config in registry_config.get('configs', {}).items():
        if config.get('tls', {}).get('insecure_skip_verify'):
            insecure_registries.append(registry)
    
    if insecure_registries:
        log_message(node, f"Configured insecure registries: {', '.join(insecure_registries)}")