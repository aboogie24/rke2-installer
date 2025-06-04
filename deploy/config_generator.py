import yaml
import os

def generate_sample_config(distribution='rke2', os_type='rhel', airgapped=True, output_file='generated-config.yml'):
    """Generate a sample configuration file for the specified distribution and OS"""
    
    # Base configuration template updated for airgapped environments
    config = {
        'deployment': {
            'k8s_distribution': distribution,
            'os': {
                'type': os_type,
                'version': get_default_os_version(os_type)
            },
            'airgap': {
                'enabled': airgapped,
                'local_registry': 'registry.internal.local:5000',
                'bundle_staging_path': '/opt/k8s-bundles',
                'image_staging_path': '/opt/container-images'
            }
        },
        'cluster': {
            'name': f'airgapped-{distribution}-cluster',
            'domain': 'internal.local',
            'token': 'K1078d6efc5ece52ed16e86a6d19bddfb222e89862efc74b7f9187f203fbc06fa00::server:a3dab4acb8829dedba9b7fe99966c153',
            'cluster_cidr': '10.42.0.0/16',
            'service_cidr': '10.43.0.0/16',
            'cni': ['multus', 'canal'],
            'disable_network_policy': False,
            'write_kubeconfig_mode': '0644',
            'disable': ['rke2-ingress-nginx'],
            'registry': {
                'mirrors': {
                    "*": {
                        'endpoints': ['https://registry.internal.local:5000']
                    },
                    "docker.io": {
                        'endpoints': ['https://registry.internal.local:5000/docker.io']
                    },
                    "quay.io": {
                        'endpoints': ['https://registry.internal.local:5000/quay.io']
                    },
                    "gcr.io": {
                        'endpoints': ['https://registry.internal.local:5000/gcr.io']
                    },
                    "registry.k8s.io": {
                        'endpoints': ['https://registry.internal.local:5000/registry.k8s.io']
                    }
                },
                'configs': {
                    'registry.internal.local:5000': {
                        'tls': {
                            'insecure_skip_verify': True
                        },
                        'auth': {
                            'username': 'registry-user',
                            'password': 'registry-password'
                        }
                    }
                }
            }
        },
        'nodes': {
            'servers': [
                {
                    'hostname': f'{distribution}-server-1',
                    'ip': '10.0.4.10',
                    'user': 'k8s-admin',  # Updated to non-root user
                    'ssh_key': '.ssh/cluster_key',
                    'sudo_password': '',  # Added for sudo access
                    'staging_paths': {
                        'bundles': '/home/k8s-admin/staging/bundles',
                        'images': '/home/k8s-admin/staging/images'
                    }
                }
            ],
            'agents': [
                {
                    'hostname': f'{distribution}-agent-1',
                    'ip': '10.0.4.177',
                    'user': 'k8s-admin',  # Updated to non-root user
                    'ssh_key': '.ssh/cluster_key',
                    'sudo_password': '',  # Added for sudo access
                    'gpu_enabled': False,
                    'staging_paths': {
                        'bundles': '/home/k8s-admin/staging/bundles',
                        'images': '/home/k8s-admin/staging/images'
                    },
                    'labels': {
                        'node-role.kubernetes.io/worker': 'true',
                        'environment': 'production'
                    }
                }
            ]
        },
        'packages': get_os_packages(os_type),
        'extra_tools': ['k9s', 'helm', 'flux'],
        'security': {
            'ssh': {
                'strict_host_key_checking': False,
                'connection_timeout': 30,
                'command_timeout': 600
            },
            'sudo': {
                'preserve_env': True,
                'required_vars': ['PATH', 'HOME']
            },
            'certificates': {
                'ca_bundle_path': '/opt/certs/internal-ca-bundle.crt',
                'registry_certs_path': '/opt/certs/registry'
            }
        },
        'validation': {
            'required_bundles': get_required_bundles(distribution),
            'required_tools': ['tar', 'gzip'],
            'network_checks': [
                'registry.internal.local:5000',
                'ntp.internal.local'
            ],
            'disk_space_requirements': {
                'staging_area': '10GB',
                'var_lib_rancher': '50GB',
                'var_lib_containerd': '100GB'
            }
        }
    }
    
    # Add distribution-specific configuration
    if distribution == 'rke2':
        config['deployment']['rke2'] = {
            'version': 'v1.32.3',
            'airgap_bundle_path': '/opt/k8s-bundles/rke2-airgap-bundle.tar.gz',
            'images_bundle_path': '/opt/k8s-bundles/rke2-images.linux-amd64.tar.gz',
            'rpm_bundle_path': '/opt/k8s-bundles/rke2-rpms.tar.gz',
            'binary_bundle_path': '/opt/k8s-bundles/rke2.linux-amd64.tar.gz',
            'install_script_path': '/opt/k8s-bundles/install.sh',
            'systemd_service_path': '/etc/systemd/system/'
        }
        
    elif distribution == 'eks-anywhere':
        config['deployment']['eks_anywhere'] = {
            'version': 'v0.18.0',
            'bundle_path': '/opt/k8s-bundles/eks-anywhere-bundle.tar.gz',
            'cluster_spec_path': '/opt/eks-anywhere/cluster.yaml',
            'images_bundle_path': '/opt/k8s-bundles/eks-anywhere-images.tar.gz'
        }
        
    elif distribution == 'vanilla' or distribution == 'kubeadm':
        config['deployment']['vanilla_k8s'] = {
            'version': 'v1.32.3',
            'container_runtime': 'containerd',
            'cni_plugin': 'calico',
            'kubeadm_bundle_path': '/opt/k8s-bundles/kubeadm-bundle.tar.gz',
            'images_bundle_path': '/opt/k8s-bundles/k8s-images.tar.gz'
        }
        
    elif distribution == 'k3s':
        config['deployment']['k3s'] = {
            'version': 'v1.32.3+k3s1',
            'datastore': 'sqlite',
            'binary_path': '/opt/k8s-bundles/k3s',
            'images_bundle_path': '/opt/k8s-bundles/k3s-airgap-images-amd64.tar.gz'
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
    """Get OS-specific package configurations for airgapped environments"""
    if os_type in ['rhel', 'centos', 'rocky']:
        return {
            os_type: {
                'bundle_path': f'/opt/k8s-bundles/{os_type}-packages.tar.gz',
                'base_packages': [
                    'container-selinux',
                    'iptables',
                    'libnetfilter_conntrack',
                    'libnfnetlink',
                    'libnftnl',
                    'libseccomp',
                    'tar',
                    'wget',
                    'curl',
                    'yum-utils'
                ],
                'gpu_packages': [
                    'nvidia-container-toolkit',
                    'nvidia-container-runtime'
                ],
                'gpu_bundle_path': f'/opt/k8s-bundles/nvidia-packages-{os_type}.tar.gz'
            }
        }
    elif os_type in ['ubuntu', 'debian']:
        return {
            os_type: {
                'bundle_path': f'/opt/k8s-bundles/{os_type}-packages.tar.gz',
                'base_packages': [
                    'apt-transport-https',
                    'ca-certificates',
                    'curl',
                    'gnupg',
                    'lsb-release',
                    'iptables',
                    'software-properties-common'
                ],
                'gpu_packages': [
                    'nvidia-container-toolkit',
                    'nvidia-container-runtime'
                ],
                'gpu_bundle_path': f'/opt/k8s-bundles/nvidia-packages-{os_type}.tar.gz'
            }
        }
    
    return {}

def get_required_bundles(distribution):
    """Get list of required bundles for validation"""
    if distribution == 'rke2':
        return [
            'rke2-airgap-bundle.tar.gz',
            'rke2-images.linux-amd64.tar.gz',
            'container-runtime-bundle.tar.gz'
        ]
    elif distribution == 'k3s':
        return [
            'k3s',
            'k3s-airgap-images-amd64.tar.gz'
        ]
    elif distribution == 'eks-anywhere':
        return [
            'eks-anywhere-bundle.tar.gz',
            'eks-anywhere-images.tar.gz'
        ]
    elif distribution in ['vanilla', 'kubeadm']:
        return [
            'kubeadm-bundle.tar.gz',
            'k8s-images.tar.gz'
        ]
    
    return []