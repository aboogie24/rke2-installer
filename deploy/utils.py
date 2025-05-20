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