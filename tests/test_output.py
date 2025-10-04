import pytest
from click.testing import CliRunner
from models import create_user, create_ecology, create_forest, create_tree
from output import print_tree

@pytest.fixture
def runner():
    return CliRunner()

def test_print_tree(runner, setup_db):
    """Test printing a tree hierarchy."""
    user_id = create_user("John Doe", "johndoe", "john.doe@example.com", "password123")
    ecology_id = create_ecology(user_id, "Ecology 1")
    forest_id = create_forest(user_id, ecology_id, "Forest 1")
    tree_id = create_tree(user_id, forest_id, "Tree 1")
    result = runner.invoke(print_tree, [str(tree_id)])
    assert result.exit_code == 0
    assert "Tree 1" in result.output
