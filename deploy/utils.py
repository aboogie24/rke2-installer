import click
import colorama

# Global token for node communication
serverToken = None

def log_message(node, message, color=colorama.Fore.CYAN, details=None, details_color=colorama.Fore.MAGENTA):
    """Unified logging function for consistent formatting"""
    base_msg = color + f"[" + colorama.Fore.YELLOW + f"{node['hostname']}" + color + f"] {message}"
    
    if details:
        base_msg += " " + details_color + f"{details}"
        
    click.echo(base_msg)

def log_error(node, message, details=None):
    """Log an error message with consistent formatting"""
    log_message(node, message, color=colorama.Fore.RED, details=details, details_color=colorama.Fore.RED)

def log_success(node, message, details=None):
    """Log a success message with consistent formatting"""
    log_message(node, message, color=colorama.Fore.GREEN, details=details)

def log_warning(node, message, details=None):
    """Log a warning message with consistent formatting"""
    log_message(node, message, color=colorama.Fore.YELLOW, details=details, details_color=colorama.Fore.YELLOW)

def run_ssh_command(ssh_client, command, return_output=False, timeout=300):
    """Run a command over SSH"""
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        
        stdout_content = stdout.read().decode().strip()
        stderr_content = stderr.read().decode().strip()
        
        if return_output:
            return stdout_content, stderr_content, exit_code
        
        if exit_code != 0:
            log_error(f"Command failed: {command}")
            log_error(f"Exit code: {exit_code}")
            log_error(f"Stderr: {stderr_content}")
            return False
        
        if stdout_content:
            log_message(f"Command output: {stdout_content}")
        
        return True
        
    except Exception as e:
        log_error(f"SSH command execution failed: {str(e)}")
        if return_output:
            return "", str(e), -1
        return False
