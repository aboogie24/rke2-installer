import yaml
import os

def generate_sample_config(distribution='rke2', os_type='rhel', output_file='generated-config.yml'):
    """Generate a sample configuration file for the specified distribution and OS"""
    
    # Base configuration template
    config = {
        'deployment': {
            'k8s_distribution': distribution,
            'os': {
                'type': os_type,
                'version': get_default_os_version(os_type)
            }
        },
        'cluster': {
            'name': f'my-{distribution}-cluster',
            'domain': 'example.com',
            'token': 'K1078d6efc5ece52ed16e86a6d19bddfb222e89862efc74b7f9187f203fbc06fa00::server:a3dab4acb8829dedba9b7fe99966c153',
            'cluster_cidr': '10.42.0.0/16',
            'service_cidr': '10.43.0.0/16',
            'cni': ['multus', 'canal'],
            'disable_network_policy': False,
            'write_kubeconfig_mode': '0644',
            'disable': ['ingress-nginx']
        },
        'nodes': {
            'servers': [
                {
                    'hostname': f'{distribution}-server-1',
                    'ip': '10.0.4.10',
                    'user': 'root',
                    'ssh_key': '.ssh/cluster_key'
                }
            ],
            'agents': [
                {
                    'hostname': f'{distribution}-agent-1',
                    'ip': '10.0.4.177',
                    'user': 'root',
                    'ssh_key': '.ssh/cluster_key',
                    'gpu_enabled': False
                }
            ]
        },
        'packages': get_os_packages(os_type),
        'extra_tools': ['k9s', 'helm', 'flux']
    }
    
    # Add distribution-specific configuration
    if distribution == 'rke2':
        config['deployment']['rke2'] = {
            'version': 'v1.32.3',
            'airgap_bundle_path': '/opt/rke2-airgap-bundle.tar.gz',
            'rpm_path': '/opt/rke2/rpms',
            'tar_extract_path': '/opt/rke2',
            'systemd_service_path': '/etc/systemd/system/'
        }
        
        config['cluster']['registry'] = {
            'mirrors': {
                'registry.example.com': {
                    'endpoints': ['https://registry.example.com']
                }
            },
            'configs': {
                'registry.example.com': {
                    'tls': {
                        'insecure_skip_verify': True
                    }
                }
            }
        }
        
    elif distribution == 'eks-anywhere':
        config['deployment']['eks_anywhere'] = {
            'version': 'v0.18.0',
            'bundle_manifest_url': 'https://anywhere-assets.eks.amazonaws.com/releases/eks-a/manifest.yaml',
            'cluster_spec_path': '/opt/eks-anywhere/cluster.yaml'
        }
        
    elif distribution == 'vanilla' or distribution == 'kubeadm':
        config['deployment']['vanilla_k8s'] = {
            'version': 'v1.32.3',
            'container_runtime': 'containerd',
            'cni_plugin': 'calico'
        }
        
    elif distribution == 'k3s':
        config['deployment']['k3s'] = {
            'version': 'v1.32.3+k3s1',
            'datastore': 'sqlite'
        }
    
    # Write configuration file
    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    return output_file

def get_default_os_version(os_type):
    """Get default OS version for the specified OS type"""
    defaults = {
        'rhel': '9',
        'ubuntu': '22.04',
        'centos': '8',
        'rocky': '9',
        'debian': '12'
    }
    return defaults.get(os_type, '9')

def get_os_packages(os_type):
    """Get OS-specific package configurations"""
    if os_type in ['rhel', 'centos', 'rocky']:
        return {
            os_type: {
                'base_packages': [
                    'container-selinux',
                    'iptables',
                    'libnetfilter_conntrack',
                    'libnfnetlink',
                    'libnftnl',
                    'libseccomp',
                    'tar',
                    'wget',
                    'curl'
                ],
                'gpu_packages': [
                    'nvidia-container-toolkit',
                    'nvidia-container-runtime'
                ]
            }
        }
    elif os_type in ['ubuntu', 'debian']:
        return {
            os_type: {
                'base_packages': [
                    'apt-transport-https',
                    'ca-certificates',
                    'curl',
                    'gnupg',
                    'lsb-release',
                    'iptables'
                ],
                'gpu_packages': [
                    'nvidia-container-toolkit',
                    'nvidia-container-runtime'
                ]
            }
        }
    
    return {}
