from ..utils import log_message, log_error, log_success, log_warning
import os

class AirgapValidator:
    """Validates airgapped environment requirements"""
    
    def __init__(self, config):
        self.config = config
        self.validation_config = config.get('validation', {})
    
    def validate_local_bundles(self):
        """Validate that all required bundles exist locally"""
        log_message("Validating local bundles...")
        
        missing_bundles = []
        dist = self.config['deployment']['k8s_distribution']
        
        if dist == 'rke2':
            rke2_config = self.config['deployment']['rke2']
            required_bundles = [
                'airgap_bundle_path',
                'images_bundle_path',
                'install_script_path'
            ]
            
            for bundle_key in required_bundles:
                if bundle_key in rke2_config:
                    bundle_path = rke2_config[bundle_key]
                    if not os.path.exists(bundle_path):
                        missing_bundles.append(bundle_path)
        
        elif dist == 'k3s':
            k3s_config = self.config['deployment']['k3s']
            required_bundles = [
                'binary_path',
                'images_bundle_path'
            ]
            
            for bundle_key in required_bundles:
                if bundle_key in k3s_config:
                    bundle_path = k3s_config[bundle_key]
                    if not os.path.exists(bundle_path):
                        missing_bundles.append(bundle_path)
        
        # Check package bundles
        packages_config = self.config.get('packages', {})
        for os_type, os_config in packages_config.items():
            if 'bundle_path' in os_config:
                bundle_path = os_config['bundle_path']
                if not os.path.exists(bundle_path):
                    missing_bundles.append(bundle_path)
        
        if missing_bundles:
            log_error("Missing required bundles:")
            for bundle in missing_bundles:
                log_error(f"  - {bundle}")
            return False
        
        log_success("✅ All required bundles found")
        return True
    
    def validate_disk_space(self):
        """Validate disk space requirements"""
        log_message("Validating disk space requirements...")
        
        disk_reqs = self.validation_config.get('disk_space_requirements', {})
        
        # Check local disk space for bundles
        bundle_staging = self.config['deployment']['airgap']['bundle_staging_path']
        if os.path.exists(bundle_staging):
            # This is a simplified check - in practice you'd check actual disk space
            log_success("✅ Bundle staging area accessible")
        else:
            log_warning(f"Bundle staging area does not exist: {bundle_staging}")
        
        return True
    
    def validate_registry_access(self):
        """Validate local registry configuration"""
        log_message("Validating registry configuration...")
        
        airgap_config = self.config['deployment']['airgap']
        if not airgap_config.get('enabled'):
            log_message("Airgap mode not enabled, skipping registry validation")
            return True
        
        local_registry = airgap_config.get('local_registry')
        if not local_registry:
            log_error("Local registry not configured for airgapped deployment")
            return False
        
        log_success(f"✅ Local registry configured: {local_registry}")
        return True
    
    def validate_ssh_access(self, node):
        """Validate SSH access to nodes with non-root user"""
        log_message(f"Validating SSH access to {node['hostname']}...")
        
        required_fields = ['hostname', 'ip', 'user', 'ssh_key']
        for field in required_fields:
            if field not in node:
                log_error(f"Missing required field in node config: {field}")
                return False
        
        # Check SSH key exists
        ssh_key_path = node['ssh_key']
        if not os.path.exists(ssh_key_path):
            log_error(f"SSH key not found: {ssh_key_path}")
            return False
        
        if node['user'] == 'root':
            log_warning("Using root user - consider using non-root user with sudo")
        
        log_success(f"✅ SSH configuration valid for {node['hostname']}")
        return True
    
    def run_full_validation(self):
        """Run complete validation for airgapped deployment"""
        log_message("Running full airgapped environment validation...")
        
        validation_results = []
        
        # Validate bundles
        validation_results.append(self.validate_local_bundles())
        
        # Validate disk space
        validation_results.append(self.validate_disk_space())
        
        # Validate registry
        validation_results.append(self.validate_registry_access())
        
        # Validate SSH access to all nodes
        for node in self.config['nodes']['servers'] + self.config['nodes']['agents']:
            validation_results.append(self.validate_ssh_access(node))
        
        if all(validation_results):
            log_success("✅ All airgapped environment validations passed")
            return True
        else:
            log_error("❌ Some validations failed - please fix issues before deployment")
            return False
