# RKE2 Installer

## Tarball Directory structure
```
rke2-airgap-bundle/
├── rke2/                                # From rke2.linux-amd64.tar.gz
│   ├── bin/
│   └── share/systemd/
├── rpms/                                # From rke2-rpm.tar.gz
│   ├── rke2-common-*.rpm
│   ├── rke2-server-*.rpm
│   ├── rke2-agent-*.rpm
│   └── rke2-selinux-*.rpm
├── images/
│   └── rke2-airgap-images.tar
├── systemd/
│   ├── rke2-server.service
│   └── rke2-agent.service
└── install.sh                           # Custom script for automation

```

### Downloading the RKE2 packages
```
# Download the rke2.linux tar
curl -sfL https://github.com/rancher/rke2/releases/download/v1.32.3+rke2r1/rke2.linux-amd64.tar.gz -o rke2.linux-amd64.tar.gz

# Download the rke2 images
curl -OLs https://github.com/rancher/rke2/releases/download/v1.32.3%2Brke2r2/rke2-images.linux-amd64.tar.zst -o rke2-images-all.linux-amd64.tar.gz

# Download rpm packages for RKE2
sudo dnf install dnf-plugins-core -y
sudo dnf download --resolve rke2-common rke2-server rke2-agent rke2-selinux

# Download Kubectl
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
```

### How to Build the Bundle
```
mkdir -p rke2-airgap-bundle/{rke2,rpms,images,systemd}

# Extract Rancher's offline RKE2 binary bundle
tar -xzf rke2.linux-amd64.tar.gz -C rke2-airgap-bundle/rke2

# Extract RPMs
cp rke2-agent-1.27.16~rke2r2-0.el8.x86_64.rpm rke2-airgap-bundle/rpms/.
cp rke2-common-1.27.16~rke2r2-0.el8.x86_64.rpm rke2-airgap-bundle/rpms/.
cp rke2-selinux-0.18-1.el8.noarch.rpm rke2-airgap-bundle/rpms/.
cp rke2-server-1.27.16~rke2r2-0.el8.x86_64.rpm rke2-airgap-bundle/rpms/.

# Move the airgap image tar into the structure
mv rke2-airgap-images.tar rke2-airgap-bundle/images/

# Copy systemd service files if you want them predefined (optional)
cp rke2-airgap-bundle/rke2/lib/systemd/system/rke2-*.service rke2-airgap-bundle/systemd/.

# (Optional) Add install.sh
cat <<EOF > rke2-airgap-bundle/install.sh
#!/bin/bash
echo "Placeholder for install automation logic"
EOF
chmod +x rke2-airgap-bundle/install.sh
```
### Create Tarball
Create this tarball from a machine online.... More information to follow
```
tar -cvzf rke2-airgap-bundle.tar.gz rke2-airgap-bundle/
```

# rke2-installer

Update the `config.yaml` file with the predefined token. 

## How to Create the Token
```
openssl rand -hex 32
```

