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
    else:
        config['token'] = cfg['cluster']['join_token']
        config['server'] = f"https://{

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
    
    # Properly format the config with yaml dump
    config_yaml = yaml.dump(config, default_flow_style=False)
    remote_cmd = f"sudo mkdir -p /etc/rancher/rke2 && echo '{config_yaml}' | sudo tee /etc/rancher/rke2/config.yaml > /dev/null"
    
    log_message(node, "Creating config.yaml with content:", details=f"\n{config_yaml}")
    stdin, stdout, stderr = ssh.exec_command(remote_cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code == 0:
        log_success(node, "Dynamic server config.yaml written.")
    else:
        log_error(node, "Failed to write dynamic config.yaml:", details=stderr.read().decode())

def configure_registry(ssh, node, cfg):
    """Configure container registry settings including insecure registries"""
    if 'registry' not in cfg.get('cluster', {}):
        return

    registry_config = cfg['cluster']['registry']
    log_message(node, "Configuring container registry settings...")
    
    # Convert the registry config to YAML
    registry_yaml = yaml.dump(registry_config, default_flow_style=False)
    
    # Create the registries.yaml file
    registries_cmd = f"sudo mkdir -p /etc/rancher/rke2 && echo '{registry_yaml}' | sudo tee /etc/rancher/rke2/registries.yaml > /dev/null"
    
    log_message(node, "Creating registry configuration:")
    log_message(node, "Registry config:", details=f"\n{registry_yaml}")
    
    stdin, stdout, stderr = ssh.exec_command(registries_cmd)
    exit_code = stdout.channel.recv_exit_status()
    
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
