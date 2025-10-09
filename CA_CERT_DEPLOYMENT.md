# Registry CA Certificate Deployment for RKE2

This document describes the implementation of automatic CA certificate deployment for private container registries in RKE2 clusters.

## Overview

The CA certificate deployment feature automatically configures containerd to trust your private registry by deploying the CA certificate to the correct location on each node after RKE2 installation.

## Configuration

Add the following configuration to your `config-update.yml` file:

```yaml
cluster:
  rke2:
    registry:
      # Path to CA certificate on your local machine
      ca_cert_path: /opt/certs/registry/ca.crt
      
      # Registry hostname (used for creating the containerd certs.d directory)
      registry_host: registry.internal.local:5000
      
      mirrors:
        "*":
          endpoints:
            - "https://registry.internal.local:5000"
      
      configs:
        "registry.internal.local:5000":
          tls:
            insecure_skip_verify: true
          auth:
            username: "registry-user"
            password: "registry-password"
```

## How It Works

### 1. Bundle Staging
- During the bundle staging phase, the `BundleManager` checks if a `ca_cert_path` is configured
- If found, it uploads the CA certificate to the staging path on each node (e.g., `/opt/rke2/ca.crt`)

### 2. Certificate Deployment
- After RKE2 installation, the OS handler deploys the certificate to the containerd certs.d directory
- Target location: `/var/lib/rancher/rke2/agent/etc/containerd/certs.d/{registry_host}/ca.crt`
- Example: `/var/lib/rancher/rke2/agent/etc/containerd/certs.d/registry.internal.local:5000/ca.crt`

### 3. Containerd Configuration
- RKE2's containerd automatically recognizes certificates in the certs.d directory structure
- No manual containerd configuration changes required
- Certificate is immediately available for image pulls

## Implementation Details

### Files Modified

1. **config-update.yml**
   - Added `ca_cert_path` and `registry_host` fields to registry configuration

2. **deploy/airgap/bundle_manager.py**
   - Added `_stage_registry_ca_cert()` method to upload CA cert during bundle staging
   - Updated `_stage_rke2_bundles()` to call CA cert staging

3. **deploy/os_handlers/rhel_handler.py**
   - Added `deploy_registry_ca_cert()` method to deploy cert to containerd certs.d directory
   - Creates target directory structure with proper permissions
   - Sets appropriate file ownership (root:root) and permissions (644)

4. **deploy/os_handlers/ubuntu_handler.py**
   - Added identical `deploy_registry_ca_cert()` method for Ubuntu support

5. **deploy/distributions/rke2_handler.py**
   - Updated `install_distribution()` to accept `os_handler` parameter
   - Added CA cert deployment after RKE2 installation
   - Checks for CA cert configuration and calls OS handler method

6. **deploy/node.py**
   - Updated `setup_node()` to pass `os_handler` to `install_distribution()`

## Usage

1. Place your registry CA certificate on your local machine (the machine running space-jam)

2. Update your configuration file with the CA cert path and registry host:
   ```yaml
   cluster:
     rke2:
       registry:
         ca_cert_path: /path/to/your/ca.crt
         registry_host: your-registry.example.com:5000
   ```

3. Run your deployment as normal:
   ```bash
   python main.py --config config-update.yml
   ```

4. The CA certificate will be automatically deployed to all nodes

## Verification

After deployment, verify the certificate is in place:

```bash
# SSH to any node
ssh user@node-ip

# Check if certificate exists
sudo ls -la /var/lib/rancher/rke2/agent/etc/containerd/certs.d/registry.internal.local:5000/ca.crt

# Verify certificate contents
sudo cat /var/lib/rancher/rke2/agent/etc/containerd/certs.d/registry.internal.local:5000/ca.crt
```

## Certificate Requirements

- Format: PEM-encoded X.509 certificate
- Must be the CA certificate that signed your registry's TLS certificate
- Can be a certificate chain (multiple certificates in one file)

## Troubleshooting

### Certificate Not Found
- Verify the `ca_cert_path` in your config points to the correct file
- Check file permissions - space-jam needs to be able to read the certificate

### Images Still Failing to Pull
- Verify the `registry_host` matches your registry exactly (including port)
- Check if the CA certificate is valid and matches your registry's certificate
- Restart containerd on the node: `sudo systemctl restart containerd` (for non-RKE2 containerd)
- For RKE2, restart the RKE2 service: `sudo systemctl restart rke2-server` or `sudo systemctl restart rke2-agent`

### Permission Denied
- Ensure the certificate has proper ownership (root:root) and permissions (644)
- The deployment script automatically sets these, but manual verification may help

## Notes

- The CA certificate is deployed **after** RKE2 installation but **before** services start
- If you update the CA certificate, you'll need to manually deploy it to existing nodes or redeploy
- This feature is compatible with both airgapped and online deployments
- Works with both server and agent nodes
