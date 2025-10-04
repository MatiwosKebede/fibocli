import pytest
from click.testing import CliRunner
from cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_init_command(runner, setup_db):
    """Test the init command."""
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "Database initialized" in result.output

def test_signup_command(runner, setup_db):
    """Test the signup command."""
    result = runner.invoke(cli, ["signup", "John Doe", "johndoe", "john@example.com", "password123"])
    assert result.exit_code == 0
    assert "User created successfully" in result.output

def test_create_forest_invalid_ecology(runner, setup_db):
    """Test creating a forest with invalid ecology ID."""
    runner.invoke(cli, ["signup", "John Doe", "johndoe", "john@example.com", "password123"])
    runner.invoke(cli, ["login", "johndoe", "password123"])
    result = runner.invoke(cli, ["create-forest", "999", "Forest 1"])
    assert result.exit_code != 0
    assert "Invalid or deleted ecology_id" in result.output
