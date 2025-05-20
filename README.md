# RKE2 Installer - Space Jam

![Space Jam](https://img.shields.io/badge/Space%20Jam-RKE2%20Installer-blue)
![Version](https://img.shields.io/badge/Version-0.1.0-green)
![Created by](https://img.shields.io/badge/Created%20by-the%20Astronaut(AB)-yellowgreen)

A comprehensive tool for airgapped deployment of RKE2 Kubernetes clusters.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Airgap Bundle Structure](#airgap-bundle-structure)
- [Creating the Bundle](#creating-the-bundle)
  - [Downloading Components](#downloading-components) 
  - [Building the Bundle](#building-the-bundle)
  - [Creating the Tarball](#creating-the-tarball)
- [Installation with Space Jam CLI](#installation-with-space-jam-cli)
  - [Configuration](#configuration)
  - [Deployment Commands](#deployment-commands)
  - [Uninstallation](#uninstallation)
- [Manual Installation](#manual-installation)
- [Troubleshooting](#troubleshooting)

## Overview

Space Jam is an airgapped deployment tool for RKE2 Kubernetes clusters. It automates the installation process across multiple nodes, handling both server and agent configurations. This tool is designed for environments without internet access, using pre-packaged bundles.

## Prerequisites

- Linux servers with SSH access
- Python 3.6+
- Required packages (install with `pip install -r requirements.txt`):
  - click
  - PyYAML
  - colorama
  - paramiko

## Airgap Bundle Structure

The RKE2 airgap bundle uses the following structure:

```
rke2-airgap-bundle/
├── rke2/                                # RKE2 binaries and core files
│   ├── bin/                             # Contains rke2 and kubectl binaries
│   └── share/systemd/                   # Systemd service templates
├── rpms/                                # RPM packages for RKE2
│   ├── rke2-common-*.rpm
│   ├── rke2-server-*.rpm
│   ├── rke2-agent-*.rpm
│   └── rke2-selinux-*.rpm
├── images/                              # Container images
│   └── rke2-images.linux-amd64.tar.zst  # Compressed airgap images
├── systemd/                             # Systemd service files
│   ├── rke2-server.service
│   └── rke2-agent.service
└── install.sh                           # Custom automation script (optional)
```

## Creating the Bundle

### Downloading Components

From a machine with internet access, download all required components:

```bash
# Create directories for downloads
mkdir -p rke2-downloads
cd rke2-downloads

# Download the RKE2 binary tarball (update version as needed)
curl -sfL https://github.com/rancher/rke2/releases/download/v1.32.3+rke2r1/rke2.linux-amd64.tar.gz -o rke2.linux-amd64.tar.gz

# Download the RKE2 images
curl -OLs https://github.com/rancher/rke2/releases/download/v1.32.3+rke2r1/rke2-images.linux-amd64.tar.zst

# Download RPM packages (for RPM-based distributions)
sudo dnf install dnf-plugins-core -y
sudo dnf download --resolve rke2-common rke2-server rke2-agent rke2-selinux

# Download kubectl (optional if using the one included in rke2)
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl

# Download k9s 
K9S_VERSION=$(curl -s https://api.github.com/repos/derailed/k9s/releases/latest | grep -oP '"tag_name": "\K(.*)(?=")')

# Download the appropriate binary
curl -Lo k9s.tar.gz https://github.com/derailed/k9s/releases/download/${K9S_VERSION}/k9s_Linux_amd64.tar.gz

# Extract the binary
tar -xzf k9s.tar.gz k9s
chmod +x k9s
```

### Building the Bundle

Organize the downloaded components into the bundle structure:

```bash
mkdir -p rke2-airgap-bundle/{rke2,rpms,images,systemd}

# Extract RKE2 binary tarball
tar -xzf rke2.linux-amd64.tar.gz -C rke2-airgap-bundle/rke2

# Copy RPM packages
cp rke2-*.rpm rke2-airgap-bundle/rpms/

# Copy the images tarball
cp rke2-images.linux-amd64.tar.zst rke2-airgap-bundle/images/

# Copy systemd service files
cp rke2-airgap-bundle/rke2/lib/systemd/system/rke2-*.service rke2-airgap-bundle/systemd/

# Optional: Add custom install script
cat <<EOF > rke2-airgap-bundle/install.sh
#!/bin/bash
# Custom installation logic
EOF
chmod +x rke2-airgap-bundle/install.sh
```

### Creating the Tarball

Create a compressed tarball of the bundle:

```bash
tar -cvzf rke2-airgap-bundle.tar.gz rke2-airgap-bundle/
```

## Installation with Space Jam CLI

### Configuration

Create a `config.yaml` file with your cluster configuration:

```yaml
cluster:
  name: "my-rke2-cluster"
  token: "your-cluster-token"  # Generate with: openssl rand -hex 32
  airgap_bundle_path: "/path/to/rke2-airgap-bundle.tar.gz"
  tar_extract_path: "/opt/rke2"
  domain: "example.com"  # Optional
  
  # Optional Kubernetes networking configuration
  cluster-cidr: "10.42.0.0/16"
  service-cidr: "10.43.0.0/16"
  
  # Optional CNI selection
  cni:
    - "canal"  # Or multus, calico, etc.

nodes:
  servers:
    - hostname: "rke2-server-1"
      ip: "192.168.1.101"
      user: "username"
      ssh_key: "/path/to/ssh/private_key"
    
    - hostname: "rke2-server-2"
      ip: "192.168.1.102"
      user: "username"
      ssh_key: "/path/to/ssh/private_key"
  
  agents:
    - hostname: "rke2-agent-1"
      ip: "192.168.1.103"
      user: "username"
      ssh_key: "/path/to/ssh/private_key"
    
    - hostname: "rke2-agent-2"
      ip: "192.168.1.104"
      user: "username"
      ssh_key: "/path/to/ssh/private_key"
```

### Deployment Commands

Deploy your RKE2 cluster:

```bash
# Install required Python packages
pip install -r requirements.txt

# Deploy the cluster
python rke2-deploy/main.py deploy --config config.yaml
```

### Uninstallation

To uninstall RKE2 from all nodes:

```bash
# With confirmation prompt
python rke2-deploy/main.py uninstall --config config.yaml

# Force uninstall without confirmation
python rke2-deploy/main.py uninstall --config config.yaml --force
```

## Manual Installation

If you prefer to install manually instead of using the CLI:

1. Copy the bundle to each node:
   ```bash
   scp rke2-airgap-bundle.tar.gz user@node:/tmp/
   ```

2. Extract the bundle:
   ```bash
   mkdir -p /opt/rke2
   tar -xzf /tmp/rke2-airgap-bundle.tar.gz --strip-components=1 -C /opt/rke2
   ```

3. Install RPM packages:
   ```bash
   yum install -y /opt/rke2/rpms/*.rpm
   ```

4. Configure the first server node:
   ```bash
   mkdir -p /etc/rancher/rke2
   cat > /etc/rancher/rke2/config.yaml << EOF
   token: "your-cluster-token"
   cluster-init: true
   tls-san:
     - "server-ip"
     - "server-hostname"
   EOF
   ```

5. Start the RKE2 service:
   ```bash
   # For server nodes
   systemctl enable --now rke2-server
   
   # For agent nodes (after getting the token from the first server)
   systemctl enable --now rke2-agent
   ```

## Troubleshooting

- **Connection Issues**: Verify SSH connectivity and keys
- **Service Failures**: Check logs with `journalctl -u rke2-server -f` or `journalctl -u rke2-agent -f`
- **Networking Issues**: Ensure firewall rules allow RKE2 ports (6443, 9345, 10250, 8472)
- **Node Token Issues**: Manually retrieve the node token from a server with `cat /var/lib/rancher/rke2/server/node-token`

---

Created by: the Astronaut(AB)