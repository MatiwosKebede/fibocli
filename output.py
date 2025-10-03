# output.py
from rich.tree import Tree
from rich import print as rprint
from rich.table import Table
from rich.console import Console
from db import get_conn
import json

console = Console()

def print_tree(nodes):
    """Print hierarchy as a tree using rich"""
    # Find the ecology node to start
    ecology = next((n for n in nodes if n["node_type"] == "ecology"), None)
    if not ecology:
        rprint("[red]No ecology found.[/red]")
        return
    tree = Tree(f"[bold green]{ecology['name']}[/bold green] (Ecology, ID: {ecology['id']})")
    
    # Organize nodes by parent
    node_map = {n["id"]: n for n in nodes}
    children = {t: [] for t in ["ecology", "forest", "tree", "super_branch", "branch", "sub_branch"]}
    for n in nodes:
        if n["node_type"] != "ecology" and n["parent_id"]:
            parent_type = next(p["node_type"] for p in nodes if p["id"] == n["parent_id"])
            children[parent_type].append(n)

    def add_children(parent_node, parent_type, parent_id):
        for child in children[parent_type]:
            if child["parent_id"] == parent_id:
                status_icon = status_icons.get(child["status"], child["status"])
                child_node = tree.add(f"{status_icon} {child['name']} ({child['node_type'].capitalize()}, ID: {child['id']})")
                next_type = {
                    "ecology": "forest",
                    "forest": "tree",
                    "tree": "super_branch",
                    "super_branch": "branch",
                    "branch": "sub_branch",
                    "sub_branch": "leaf"
                }.get(parent_type)
                if next_type:
                    add_children(child_node, next_type, child["id"])

    add_children(tree, "forest", ecology["id"])
    rprint(tree)

def print_reviews(reviews):
    """Print pending reviews in a table"""
    table = Table(title="Pending Reviews")
    table.add_column("ID")
    table.add_column("Target")
    table.add_column("Type")
    table.add_column("Due")
    table.add_column("Duration (min)")
    for r in reviews:
        table.add_row(
            str(r["id"]),
            str(r["target_id"]),
            r["target_type"].capitalize(),
            r["scheduled_date"],
            str(r["estimated_duration"])
        )
    rprint(table)

def print_schedule(placements):
    """Print scheduled items in a table"""
    table = Table(title="Weekly Schedule")
    table.add_column("Date")
    table.add_column("Time")
    table.add_column("Type")
    table.add_column("Item")
    table.add_column("Duration (min)")
    for p in placements:
        start = p["start_datetime"]
        table.add_row(
            start[:10],
            start[11:16],
            p["type"].capitalize(),
            f"{p['related_type'] or ''} ID: {p['related_id'] or ''}",
            str(p["duration"])
        )
    rprint(table)

def print_progress_chart(user_id):
    """Show a progress chart for leaves"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT status, COUNT(*) as count 
            FROM v_leaf_status 
            WHERE sub_branch_id IN (
                SELECT id FROM sub_branches 
                WHERE branch_id IN (
                    SELECT id FROM branches 
                    WHERE super_branch_id IN (
                        SELECT id FROM super_branches 
                        WHERE tree_id IN (
                            SELECT id FROM trees 
                            WHERE forest_id IN (
                                SELECT id FROM forests 
                                WHERE ecology_id IN (
                                    SELECT id FROM ecologies 
                                    WHERE user_id = ?
                                )
                            )
                        )
                    )
                )
            ) 
            GROUP BY status
        """, (user_id,))
        data = c.fetchall()
    
    labels = [row["status"] for row in data]
    values = [row["count"] for row in data]
    
    chart_data = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Leaf Status Distribution",
                "data": values,
                "backgroundColor": ["#36A2EB", "#FF6384", "#FFCE56"],
                "borderColor": ["#2A8ABF", "#D94F70", "#D9B13B"],
                "borderWidth": 1
            }]
        },
        "options": {
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "title": {"display": True, "text": "Number of Leaves"}
                },
                "x": {
                    "title": {"display": True, "text": "Status"}
                }
            },
            "plugins": {
                "legend": {"display": True, "position": "top"}
            }
        }
    }
    
    console.print("[bold blue]Leaf Progress Chart[/bold blue]")
    console.print(f"Chart data: {json.dumps(chart_data, indent=2)}")
    # In a real implementation, this would render a Chart.js chart in a UI
    # For CLI, we print the JSON structure
