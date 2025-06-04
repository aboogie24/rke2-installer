import os
import sys
import time
import socket
import subprocess
import tempfile
import shutil
import hashlib
import json
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union
import colorama
import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

# Global token for node communication
serverToken = None

# Logging functions with colors - supports both general and node-specific logging
import click
from typing import Union, Dict, Any

def log_message(
    node_or_message: Union[str, Dict[str, Any]], 
    message: str = None, 
    color: str = colorama.Fore.CYAN, 
    details: str = None, 
    details_color: str = colorama.Fore.MAGENTA
) -> None:
    """
    Unified logging function for consistent formatting
    
    Usage:
        log_message("General message")  # General logging
        log_message(node, "Node-specific message")  # Node-specific logging
    """
    if message is None:
        # General logging (backwards compatibility)
        general_message = str(node_or_message)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"{color}[{timestamp}] [INFO] {general_message}{colorama.Style.RESET_ALL}"
        click.echo(formatted_msg)
    else:
        # Node-specific logging
        node = node_or_message
        hostname = node.get('hostname', 'unknown') if isinstance(node, dict) else str(node)
        
        base_msg = color + f"[" + colorama.Fore.YELLOW + f"{hostname}" + color + f"] {message}"
        
        if details:
            base_msg += " " + details_color + f"{details}"
        
        base_msg += colorama.Style.RESET_ALL
        click.echo(base_msg)

def log_error(
    node_or_message: Union[str, Dict[str, Any]], 
    message: str = None, 
    details: str = None
) -> None:
    """Log an error message with consistent formatting"""
    if message is None:
        # General error logging
        general_message = str(node_or_message)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"{colorama.Fore.RED}[{timestamp}] [ERROR] {general_message}{colorama.Style.RESET_ALL}"
        click.echo(formatted_msg, err=True)
    else:
        # Node-specific error logging
        log_message(
            node_or_message, 
            message, 
            color=colorama.Fore.RED, 
            details=details, 
            details_color=colorama.Fore.RED
        )

def log_success(
    node_or_message: Union[str, Dict[str, Any]], 
    message: str = None, 
    details: str = None
) -> None:
    """Log a success message with consistent formatting"""
    if message is None:
        # General success logging
        general_message = str(node_or_message)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"{colorama.Fore.GREEN}[{timestamp}] [SUCCESS] {general_message}{colorama.Style.RESET_ALL}"
        click.echo(formatted_msg)
    else:
        # Node-specific success logging
        log_message(
            node_or_message, 
            message, 
            color=colorama.Fore.GREEN, 
            details=details
        )

def log_warning(
    node_or_message: Union[str, Dict[str, Any]], 
    message: str = None, 
    details: str = None
) -> None:
    """Log a warning message with consistent formatting"""
    if message is None:
        # General warning logging
        general_message = str(node_or_message)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"{colorama.Fore.YELLOW}[{timestamp}] [WARNING] {general_message}{colorama.Style.RESET_ALL}"
        click.echo(formatted_msg)
    else:
        # Node-specific warning logging
        log_message(
            node_or_message, 
            message, 
            color=colorama.Fore.YELLOW, 
            details=details, 
            details_color=colorama.Fore.YELLOW
        )


def log_debug(
    node_or_message: Union[str, Dict[str, Any]], 
    message: str = None, 
    details: str = None
) -> None:
    """Log a debug message (only shown if DEBUG env var is set)
    
        Need to fix the debugging issue Log

        Design options this should come from a config value not a 
        OS environment variable
    
    """
    if not os.getenv('DEBUG', '').lower() in ('1', 'true', 'yes'):
        return
        
    if message is None:
        # General debug logging
        general_message = str(node_or_message)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"{colorama.Fore.MAGENTA}[{timestamp}] [DEBUG] {general_message}{colorama.Style.RESET_ALL}"
        click.echo(formatted_msg)
    else:
        # Node-specific debug logging
        log_message(
            node_or_message, 
            message, 
            color=colorama.Fore.MAGENTA, 
            details=details, 
            details_color=colorama.Fore.CYAN
        )



# SSH utility functions
def run_ssh_command(
    ssh_client: paramiko.SSHClient,
    command: str,
    return_output: bool = False,
    timeout: int = 300,
    sudo: bool = False,
    sudo_password: Optional[str] = None
) -> Union[bool, Tuple[str, str, int]]:
    """
    Run a command over SSH
    
    Args:
        ssh_client: Paramiko SSH client
        command: Command to execute
        return_output: Whether to return command output
        timeout: Command timeout in seconds
        sudo: Whether to run with sudo
        sudo_password: Sudo password if required
    
    Returns:
        bool: Success/failure if return_output=False
        tuple: (stdout, stderr, exit_code) if return_output=True
    """
    try:
        # Prepare command with sudo if needed
        if sudo and not command.strip().startswith('sudo'):
            if sudo_password:
                command = f"echo '{sudo_password}' | sudo -S {command}"
            else:
                command = f"sudo {command}"
        
        log_debug(f"Executing SSH command: {command}")
        
        # Execute command
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
        
        # Wait for command completion
        exit_code = stdout.channel.recv_exit_status()
        
        # Read output
        stdout_content = stdout.read().decode('utf-8', errors='replace').strip()
        stderr_content = stderr.read().decode('utf-8', errors='replace').strip()
        
        log_debug(f"Command exit code: {exit_code}")
        if stdout_content:
            log_debug(f"Command stdout: {stdout_content}")
        if stderr_content and exit_code != 0:
            log_debug(f"Command stderr: {stderr_content}")
        
        if return_output:
            return stdout_content, stderr_content, exit_code
        
        if exit_code != 0:
            log_error(f"Command failed with exit code {exit_code}: {command}")
            if stderr_content:
                log_error(f"Error output: {stderr_content}")
            return False
        
        return True
        
    except Exception as e:
        log_error(f"SSH command execution failed: {str(e)}")
        if return_output:
            return "", str(e), -1
        return False

def establish_ssh_connection(
    hostname: str,
    username: str,
    ssh_key_path: str,
    port: int = 22,
    timeout: int = 30,
    sudo_password: Optional[str] = None
) -> Optional[paramiko.SSHClient]:
    """
    Establish SSH connection to a remote host
    
    Args:
        hostname: Target hostname or IP
        username: SSH username
        ssh_key_path: Path to SSH private key
        port: SSH port (default: 22)
        timeout: Connection timeout
        sudo_password: Sudo password for the user
    
    Returns:
        paramiko.SSHClient or None if connection failed
    """
    try:
        # Validate SSH key exists and has correct permissions
        if not os.path.exists(ssh_key_path):
            log_error(f"SSH key not found: {ssh_key_path}")
            return None
        
        # Check SSH key permissions (should be 600 or 400)
        key_perms = oct(os.stat(ssh_key_path).st_mode)[-3:]
        if key_perms not in ['600', '400']:
            log_warning(f"SSH key permissions are {key_perms}, should be 600 or 400")
        
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        log_debug(f"Connecting to {username}@{hostname}:{port}")
        
        # Connect
        ssh.connect(
            hostname=hostname,
            port=port,
            username=username,
            key_filename=ssh_key_path,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout
        )
        
        # Test connection with a simple command
        test_result = run_ssh_command(ssh, "echo 'SSH connection test'", return_output=True)
        if test_result[2] != 0:  # exit_code != 0
            log_error("SSH connection test failed")
            ssh.close()
            return None
        
        # Test sudo access if password provided
        if sudo_password:
            sudo_test = run_ssh_command(
                ssh, "whoami", return_output=True, 
                sudo=True, sudo_password=sudo_password
            )
            if sudo_test[2] != 0 or "root" not in sudo_test[0]:
                log_warning("Sudo access test failed")
        
        log_success(f"SSH connection established to {username}@{hostname}")
        return ssh
        
    except AuthenticationException as e:
        log_error(f"SSH authentication failed for {username}@{hostname}: {e}")
    except NoValidConnectionsError as e:
        log_error(f"No valid SSH connection to {hostname}:{port}: {e}")
    except socket.timeout:
        log_error(f"SSH connection timeout to {hostname}:{port}")
    except SSHException as e:
        log_error(f"SSH connection error to {hostname}: {e}")
    except Exception as e:
        log_error(f"Unexpected SSH error to {hostname}: {e}")
    
    return None

def upload_file_sftp(
    ssh_client: paramiko.SSHClient,
    local_path: str,
    remote_path: str,
    create_dirs: bool = True,
    set_permissions: Optional[str] = None
) -> bool:
    """
    Upload file using SFTP
    
    Args:
        ssh_client: SSH client with established connection
        local_path: Local file path
        remote_path: Remote file path
        create_dirs: Create remote directories if they don't exist
        set_permissions: Set file permissions (e.g., '755', '644')
    
    Returns:
        bool: Success/failure
    """
    try:
        if not os.path.exists(local_path):
            log_error(f"Local file not found: {local_path}")
            return False
        
        # Create remote directories if needed
        if create_dirs:
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                run_ssh_command(ssh_client, f"mkdir -p {remote_dir}", sudo=True)
        
        log_debug(f"Uploading {local_path} to {remote_path}")
        
        # Upload file
        sftp = ssh_client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        
        # Set permissions if specified
        if set_permissions:
            run_ssh_command(ssh_client, f"chmod {set_permissions} {remote_path}", sudo=True)
        
        log_success(f"File uploaded successfully: {os.path.basename(local_path)}")
        return True
        
    except Exception as e:
        log_error(f"Failed to upload file {local_path}: {e}")
        return False

def download_file_sftp(
    ssh_client: paramiko.SSHClient,
    remote_path: str,
    local_path: str,
    create_dirs: bool = True
) -> bool:
    """
    Download file using SFTP
    
    Args:
        ssh_client: SSH client with established connection
        remote_path: Remote file path
        local_path: Local file path
        create_dirs: Create local directories if they don't exist
    
    Returns:
        bool: Success/failure
    """
    try:
        # Create local directories if needed
        if create_dirs:
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
        
        log_debug(f"Downloading {remote_path} to {local_path}")
        
        # Download file
        sftp = ssh_client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        
        log_success(f"File downloaded successfully: {os.path.basename(remote_path)}")
        return True
        
    except Exception as e:
        log_error(f"Failed to download file {remote_path}: {e}")
        return False

# File and directory utilities
def ensure_directory(path: str, permissions: str = '755') -> bool:
    """
    Ensure directory exists with proper permissions
    
    Args:
        path: Directory path
        permissions: Directory permissions (default: '755')
    
    Returns:
        bool: Success/failure
    """
    try:
        os.makedirs(path, exist_ok=True)
        os.chmod(path, int(permissions, 8))
        return True
    except Exception as e:
        log_error(f"Failed to create directory {path}: {e}")
        return False

def calculate_file_checksum(file_path: str, algorithm: str = 'sha256') -> Optional[str]:
    """
    Calculate file checksum
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
    
    Returns:
        str: Checksum hex digest or None if failed
    """
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        log_error(f"Failed to calculate checksum for {file_path}: {e}")
        return None

def verify_file_checksum(file_path: str, expected_checksum: str, algorithm: str = 'sha256') -> bool:
    """
    Verify file checksum
    
    Args:
        file_path: Path to file
        expected_checksum: Expected checksum
        algorithm: Hash algorithm
    
    Returns:
        bool: True if checksum matches
    """
    actual_checksum = calculate_file_checksum(file_path, algorithm)
    if actual_checksum is None:
        return False
    
    matches = actual_checksum.lower() == expected_checksum.lower()
    if matches:
        log_success(f"Checksum verified for {os.path.basename(file_path)}")
    else:
        log_error(f"Checksum mismatch for {os.path.basename(file_path)}")
        log_error(f"Expected: {expected_checksum}")
        log_error(f"Actual:   {actual_checksum}")
    
    return matches

def get_file_size_human(file_path: str) -> str:
    """
    Get human-readable file size
    
    Args:
        file_path: Path to file
    
    Returns:
        str: Human-readable size (e.g., "1.5 MB")
    """
    try:
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except Exception:
        return "Unknown"

def safe_remove(path: str) -> bool:
    """
    Safely remove file or directory
    
    Args:
        path: File or directory path
    
    Returns:
        bool: Success/failure
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception as e:
        log_warning(f"Failed to remove {path}: {e}")
        return False

# Network utilities
def check_port_open(hostname: str, port: int, timeout: int = 5) -> bool:
    """
    Check if a port is open on a host
    
    Args:
        hostname: Target hostname or IP
        port: Port number
        timeout: Connection timeout
    
    Returns:
        bool: True if port is open
    """
    try:
        with socket.create_connection((hostname, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error):
        return False

def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolve hostname to IP address
    
    Args:
        hostname: Hostname to resolve
    
    Returns:
        str: IP address or None if resolution failed
    """
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None

# System utilities
def run_local_command(
    command: str,
    shell: bool = True,
    capture_output: bool = True,
    timeout: int = 300,
    cwd: Optional[str] = None
) -> Tuple[str, str, int]:
    """
    Run a local command
    
    Args:
        command: Command to run
        shell: Run in shell
        capture_output: Capture stdout/stderr
        timeout: Command timeout
        cwd: Working directory
    
    Returns:
        tuple: (stdout, stderr, exit_code)
    """
    try:
        log_debug(f"Running local command: {command}")
        
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        exit_code = result.returncode
        
        log_debug(f"Local command exit code: {exit_code}")
        if stdout:
            log_debug(f"Local command stdout: {stdout}")
        if stderr and exit_code != 0:
            log_debug(f"Local command stderr: {stderr}")
        
        return stdout, stderr, exit_code
        
    except subprocess.TimeoutExpired:
        log_error(f"Local command timed out: {command}")
        return "", "Command timed out", -1
    except Exception as e:
        log_error(f"Local command failed: {command} - {e}")
        return "", str(e), -1

def get_available_disk_space(path: str) -> int:
    """
    Get available disk space in bytes
    
    Args:
        path: Directory path to check
    
    Returns:
        int: Available space in bytes
    """
    try:
        stat = shutil.disk_usage(path)
        return stat.free
    except Exception as e:
        log_error(f"Failed to get disk space for {path}: {e}")
        return 0

def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable string
    
    Args:
        bytes_value: Number of bytes
    
    Returns:
        str: Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

# Configuration utilities
def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON file safely
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        dict: Parsed JSON data or None if failed
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Failed to load JSON file {file_path}: {e}")
        return None

def save_json_file(data: Dict[str, Any], file_path: str, indent: int = 2) -> bool:
    """
    Save data to JSON file
    
    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation
    
    Returns:
        bool: Success/failure
    """
    try:
        ensure_directory(os.path.dirname(file_path))
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent, default=str)
        return True
    except Exception as e:
        log_error(f"Failed to save JSON file {file_path}: {e}")
        return False

# Context managers for temporary files
class TemporaryDirectory:
    """Context manager for temporary directory"""
    
    def __init__(self, prefix: str = "k8s-deploy-", cleanup: bool = True):
        self.prefix = prefix
        self.cleanup = cleanup
        self.path = None
    
    def __enter__(self) -> str:
        self.path = tempfile.mkdtemp(prefix=self.prefix)
        log_debug(f"Created temporary directory: {self.path}")
        return self.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cleanup and self.path and os.path.exists(self.path):
            safe_remove(self.path)
            log_debug(f"Cleaned up temporary directory: {self.path}")

class TemporaryFile:
    """Context manager for temporary file"""
    
    def __init__(self, suffix: str = "", prefix: str = "k8s-deploy-", content: Optional[str] = None):
        self.suffix = suffix
        self.prefix = prefix
        self.content = content
        self.path = None
        self.file_obj = None
    
    def __enter__(self) -> str:
        self.file_obj = tempfile.NamedTemporaryFile(
            mode='w', suffix=self.suffix, prefix=self.prefix, delete=False
        )
        self.path = self.file_obj.name
        
        if self.content:
            self.file_obj.write(self.content)
        
        self.file_obj.close()
        log_debug(f"Created temporary file: {self.path}")
        return self.path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.path and os.path.exists(self.path):
            safe_remove(self.path)
            log_debug(f"Cleaned up temporary file: {self.path}")

# Progress tracking utilities
class ProgressTracker:
    """Simple progress tracker for long operations"""
    
    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
    
    def update(self, increment: int = 1, message: str = ""):
        """Update progress"""
        self.current += increment
        percentage = (self.current / self.total) * 100
        elapsed = time.time() - self.start_time
        
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {int(eta)}s"
        else:
            eta_str = "ETA: --"
        
        status = f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%) {eta_str}"
        if message:
            status += f" - {message}"
        
        log_message(status)
    
    def finish(self, message: str = "Complete"):
        """Mark as finished"""
        elapsed = time.time() - self.start_time
        log_success(f"{self.description}: {message} (took {elapsed:.1f}s)")

# Retry utilities
def retry_operation(
    operation,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple = (Exception,)
) -> Any:
    """
    Retry an operation with exponential backoff
    
    Args:
        operation: Function to retry
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff_factor: Delay multiplier for each retry
        exceptions: Exceptions to catch and retry on
    
    Returns:
        Result of successful operation
    
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return operation()
        except exceptions as e:
            last_exception = e
            if attempt == max_attempts - 1:
                break
            
            wait_time = delay * (backoff_factor ** attempt)
            log_warning(f"Operation failed (attempt {attempt + 1}/{max_attempts}), retrying in {wait_time:.1f}s: {e}")
            time.sleep(wait_time)
    
    raise last_exception

# Validation utilities
def validate_ip_address(ip: str) -> bool:
    """Validate IP address format"""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, ip)
            return True
        except socket.error:
            return False

def validate_hostname(hostname: str) -> bool:
    """Validate hostname format"""
    import re
    # Simple hostname validation
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, hostname)) and len(hostname) <= 253

def validate_port(port: Union[int, str]) -> bool:
    """Validate port number"""
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False