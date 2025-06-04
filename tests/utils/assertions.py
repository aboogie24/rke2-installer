import re

def assert_command_executed(mock_ssh, command_pattern):
    """Assert that a command matching the pattern was executed"""
    executed_commands = mock_ssh.commands_executed
    pattern = re.compile(command_pattern)
    
    matching_commands = [cmd for cmd in executed_commands if pattern.search(cmd)]
    
    assert matching_commands, f"Command pattern '{command_pattern}' not found in executed commands: {executed_commands}"

def assert_file_uploaded(mock_ssh, local_path, remote_path):
    """Assert that a file was uploaded via SFTP"""
    sftp_calls = mock_ssh.open_sftp.return_value.put.call_args_list
    
    for call in sftp_calls:
        if call[0][0] == local_path and call[0][1] == remote_path:
            return
    
    assert False, f"File upload from {local_path} to {remote_path} not found in SFTP calls"

def assert_config_contains(config, path, expected_value):
    """Assert that config contains expected value at given path"""
    current = config
    for key in path.split('.'):
        assert key in current, f"Key '{key}' not found in config path '{path}'"
        current = current[key]
    
    assert current == expected_value, f"Expected '{expected_value}' at path '{path}', got '{current}'"

def assert_log_contains(caplog, level, message_pattern):
    """Assert that log contains message at given level"""
    import logging
    
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    expected_level = level_map.get(level.lower(), logging.INFO)
    pattern = re.compile(message_pattern)
    
    matching_records = [
        record for record in caplog.records
        if record.levelno == expected_level and pattern.search(record.message)
    ]
    
    assert matching_records, f"Log message pattern '{message_pattern}' at level '{level}' not found"
