# RKE2 Installer Test Suite

This comprehensive test suite ensures the reliability, security, and performance of the RKE2 installer for airgapped environments.

## 📁 Test Structure

```
tests/
├── README.md                          # This file
├── conftest.py                        # Pytest configuration and fixtures
├── pytest.ini                        # Pytest settings
├── test_runner.py                     # Comprehensive test runner
├── quick_tests.py                     # Quick validation tests
├── run_simple_tests.py               # Simple test runner
├── unit/                              # Unit tests
│   ├── test_main_cli.py              # CLI functionality tests
│   ├── test_node_deployment.py       # Node deployment tests
│   ├── test_health_checks.py         # Health check tests
│   ├── test_config_validation_fixed.py # Config validation tests
│   ├── test_handlers_fixed.py        # Handler tests
│   └── test_utils.py                 # Utility function tests
├── integration/                       # Integration tests
│   └── test_deployment_workflows.py  # Full deployment workflow tests
├── e2e/                              # End-to-end tests
│   └── test_full_deployment_scenarios.py # Complete deployment scenarios
├── scenarios/                         # Scenario-based tests
│   └── test_security_scenarios.py    # Security-focused tests
└── utils/                            # Test utilities
```

## 🧪 Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Coverage**: CLI functions, node deployment logic, health checks, utilities
- **Execution Time**: Fast (< 30 seconds)
- **Dependencies**: Minimal, heavily mocked

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions and workflows
- **Coverage**: Complete deployment workflows, multi-distribution support
- **Execution Time**: Medium (1-5 minutes)
- **Dependencies**: Mocked external services

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete system functionality
- **Coverage**: Production-like deployments, disaster recovery, performance
- **Execution Time**: Slow (5-30 minutes)
- **Dependencies**: Full system simulation

### Scenario Tests (`tests/scenarios/`)
- **Purpose**: Test specific use cases and edge cases
- **Coverage**: Security scenarios, error handling, edge cases
- **Execution Time**: Variable
- **Dependencies**: Context-specific

## 🏷️ Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Tests that take significant time
- `@pytest.mark.performance` - Performance benchmarking tests
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.smoke` - Quick validation tests
- `@pytest.mark.gpu` - Tests requiring GPU hardware

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests (excluding slow tests)
python tests/test_runner.py

# Run all tests including slow E2E tests
python tests/test_runner.py --all --include-slow

# Run quick validation
python tests/test_runner.py --quick
```

### Specific Test Categories

```bash
# Unit tests only
python tests/test_runner.py --unit

# Integration tests only
python tests/test_runner.py --integration

# End-to-end tests only
python tests/test_runner.py --e2e

# Security tests only
python tests/test_runner.py --security

# Performance tests only
python tests/test_runner.py --performance

# Smoke tests for quick validation
python tests/test_runner.py --smoke
```

### Using pytest directly

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run tests with specific marker
pytest -m "unit and not slow" -v

# Run tests with coverage
pytest --cov=. --cov-report=html tests/unit/

# Run specific test file
pytest tests/unit/test_main_cli.py -v

# Run specific test method
pytest tests/unit/test_main_cli.py::TestMainCLI::test_load_config_valid_file -v
```

### Advanced Options

```bash
# Verbose output with detailed logs
python tests/test_runner.py --unit --verbose

# Generate coverage report
python tests/test_runner.py --coverage

# Run linting
python tests/test_runner.py --lint

# Run only failed tests from last run
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto tests/unit/
```

## 📊 Test Coverage

The test suite aims for comprehensive coverage:

- **Unit Tests**: 90%+ code coverage for core modules
- **Integration Tests**: Complete workflow coverage
- **E2E Tests**: Production scenario coverage
- **Security Tests**: Security vulnerability coverage

### Generating Coverage Reports

```bash
# HTML coverage report
python tests/test_runner.py --coverage
# Report available at htmlcov/index.html

# Terminal coverage report
pytest --cov=. --cov-report=term-missing tests/unit/

# XML coverage report (for CI/CD)
pytest --cov=. --cov-report=xml tests/unit/
```

## 🔧 Test Configuration

### Fixtures (`conftest.py`)

Common fixtures available across all tests:

- `sample_config` - Standard test configuration
- `temp_config_file` - Temporary configuration file
- `mock_ssh_client` - Mocked SSH client
- `mock_bundle_files` - Mock bundle files for testing
- `test_environment` - Test environment setup

### Environment Variables

- `TESTING=true` - Indicates test environment
- `DEBUG=true` - Enable debug logging in tests

### Mock Strategy

Tests use comprehensive mocking to:
- Avoid external dependencies
- Ensure consistent test environments
- Enable testing of error conditions
- Provide fast test execution

## 🏗️ Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, patch

class TestNewFeature:
    """Test new feature functionality"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies"""
        with patch('module.dependency') as mock_dep:
            mock_dep.return_value = True
            yield mock_dep
    
    def test_feature_success(self, mock_dependencies):
        """Test successful feature operation"""
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = feature_function(input_data)
        
        # Assert
        assert result is True
        mock_dependencies.assert_called_once()
    
    def test_feature_failure(self, mock_dependencies):
        """Test feature failure handling"""
        # Arrange
        mock_dependencies.side_effect = Exception("Test error")
        
        # Act & Assert
        with pytest.raises(Exception):
            feature_function({})
```

### Integration Test Template

```python
@pytest.mark.integration
class TestFeatureIntegration:
    """Integration tests for feature"""
    
    @pytest.fixture
    def integration_setup(self):
        """Setup integration test environment"""
        # Setup code
        yield
        # Cleanup code
    
    def test_feature_workflow(self, integration_setup):
        """Test complete feature workflow"""
        # Test implementation
        pass
```

### Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
2. **Arrange-Act-Assert**: Structure tests clearly
3. **One Assertion Per Test**: Focus on single behaviors
4. **Mock External Dependencies**: Keep tests isolated
5. **Use Fixtures**: Reuse common setup code
6. **Test Edge Cases**: Include error conditions and boundary cases
7. **Document Complex Tests**: Add docstrings for complex test logic

## 🔍 Debugging Tests

### Running Single Tests

```bash
# Run specific test with verbose output
pytest tests/unit/test_main_cli.py::TestMainCLI::test_load_config_valid_file -v -s

# Run with pdb debugger
pytest tests/unit/test_main_cli.py::TestMainCLI::test_load_config_valid_file --pdb

# Run with custom markers
pytest -m "unit and not slow" --tb=long
```

### Common Issues

1. **Import Errors**: Ensure PYTHONPATH includes project root
2. **Mock Issues**: Verify mock paths match actual import paths
3. **Fixture Scope**: Check fixture scope matches test requirements
4. **Async Tests**: Use pytest-asyncio for async test support

## 🚀 Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        python tests/test_runner.py --all
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: python tests/test_runner.py --unit --integration
        language: system
        pass_filenames: false
```

## 📈 Performance Testing

Performance tests measure:
- Deployment time for various cluster sizes
- Memory usage during operations
- Network efficiency
- Resource utilization

```bash
# Run performance tests
python tests/test_runner.py --performance

# Run with profiling
pytest --profile tests/e2e/test_full_deployment_scenarios.py
```

## 🔒 Security Testing

Security tests validate:
- Input sanitization
- Authentication mechanisms
- Authorization controls
- Secure communication
- Vulnerability scanning

```bash
# Run security tests
python tests/test_runner.py --security

# Run with security markers
pytest -m security -v
```

## 📝 Test Reports

### HTML Reports

```bash
# Generate HTML test report
pytest --html=reports/report.html --self-contained-html
```

### JUnit XML (for CI/CD)

```bash
# Generate JUnit XML report
pytest --junitxml=reports/junit.xml
```

### Custom Reports

The test runner generates comprehensive reports including:
- Test execution summary
- Performance metrics
- Coverage statistics
- Failed test details

## 🤝 Contributing

When contributing tests:

1. Follow the existing test structure
2. Add appropriate markers
3. Include both positive and negative test cases
4. Update documentation for new test categories
5. Ensure tests are deterministic and isolated
6. Add integration tests for new features
7. Update the test runner if needed

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## 🆘 Troubleshooting

### Common Test Failures

1. **Import Errors**: Check PYTHONPATH and module structure
2. **Mock Failures**: Verify mock patch paths
3. **Fixture Issues**: Check fixture scope and dependencies
4. **Timeout Issues**: Increase timeout for slow operations
5. **Resource Issues**: Ensure proper cleanup in fixtures

### Getting Help

1. Check test logs for detailed error messages
2. Run tests with `-v` flag for verbose output
3. Use `--tb=long` for detailed tracebacks
4. Review fixture setup and teardown
5. Verify mock configurations

---

**Happy Testing! 🧪✨**

This test suite ensures the RKE2 installer is robust, secure, and ready for production deployments in airgapped environments.
