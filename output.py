from rich.console import Console
from rich.table import Table
from rich.tree import Tree

def print_tree(tree_data):
    console = Console()
    tree = Tree("Ecology")
    for leaf in tree_data:
        tree.add(f"Leaf: {leaf[1]} (ID: {leaf[0]})")
    console.print(tree)

def print_schedule(schedule):
    console = Console()
    table = Table(title="Review Schedule")
    table.add_column("Node")
    table.add_column("Due Date")
    table.add_column("Duration (min)")
    for row in schedule:
        table.add_row(row['node'], row['due_date'], str(row['duration']))
    console.print(table)
