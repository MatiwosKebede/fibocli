from rich.tree import Tree
from rich import print as rprint
from rich.table import Table
from rich.console import Console
from rich.text import Text
from db import get_conn
import json # Kept in case you use it elsewhere, but not needed for the new chart

console = Console()

# --- Configuration ---
status_icons = {
    "pending": "[yellow]○[/yellow]",
    "active": "[blue]▶[/blue]",
    "completed": "[green]✓[/green]"
}

# Mapping status to a color for the progress bar
STATUS_COLORS = {
    "pending": "yellow",
    "active": "blue",
    "completed": "green"
}

# --- Utility Functions (Kept original logic, just including for completeness) ---

def print_tree(nodes):
    """Print hierarchy as a tree using rich, including course_name and resource_type"""
    ecology = next((n for n in nodes if n["node_type"] == "ecology"), None)
    if not ecology:
        rprint("[red]No ecology found.[/red]")
        return
    tree_label = f"[bold green]{ecology['name']}[/bold green] (Ecology, ID: {ecology['id']}"
    if ecology["course_name"]:
        tree_label += f", Course: {ecology['course_name']}"
    tree_label += ")"
    tree = Tree(tree_label)
    
    node_map = {n["id"]: n for n in nodes}
    children = {t: [] for t in ["ecology", "forest", "tree", "super_branch", "branch", "sub_branch"]}
    for n in nodes:
        if n["node_type"] != "ecology" and n["parent_id"]:
            # NOTE: This parent_type lookup is inefficient for large datasets.
            # A more robust solution would be to pre-process the data into a tree structure
            # before calling print_tree. For now, it keeps the original logic intact.
            parent_node = node_map.get(n["parent_id"])
            if parent_node:
                parent_type = parent_node["node_type"]
                children[parent_type].append(n)

    def add_children(parent_node, parent_type, parent_id):
        next_node_type = {
            "ecology": "forest",
            "forest": "tree",
            "tree": "super_branch",
            "super_branch": "branch",
            "branch": "sub_branch",
            "sub_branch": "leaf"
        }.get(parent_type)

        if not next_node_type:
             return

        for child in sorted([c for c in children.get(parent_type, []) if c.get("parent_id") == parent_id], key=lambda x: x["name"]):
            status_icon = status_icons.get(child.get("status", "unknown"), child.get("status", "?"))
            
            label_parts = [
                f"{status_icon} [b]{child['name']}[/b]", 
                f"({child['node_type'].capitalize()}, ID: {child['id']})"
            ]
            if child.get("course_name"):
                label_parts.append(f"Course: {child['course_name']}")
            if child["node_type"] == "leaf" and child.get("resource_type"):
                label_parts.append(f"Type: {child['resource_type'].capitalize()}")

            child_node = parent_node.add(" ".join(label_parts))
            
            # Recursive call for the next level
            add_children(child_node, next_node_type, child["id"])

    # Start the recursion from the ecology node looking for 'forest' children
    add_children(tree, "ecology", ecology["id"])
    rprint(tree)

def print_reviews(reviews):
    """Print pending reviews in a table with course_name"""
    table = Table(title="[bold red]Pending Reviews[/bold red]")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Target", style="bold")
    table.add_column("Type")
    table.add_column("Course", style="dim")
    table.add_column("Due", style="magenta")
    table.add_column("Duration (min)", justify="right")
    
    for r in reviews:
        course = r.get("course_name", "-")
        table.add_row(
            str(r["id"]),
            f"{r['name']} (ID: {r['target_id']})",
            r["target_type"].capitalize(),
            course,
            r["scheduled_date"],
            str(r["estimated_duration"])
        )
    rprint(table)

def print_schedule(placements):
    """Print scheduled items in a table with course_name"""
    table = Table(title="[bold blue]Weekly Schedule[/bold blue]")
    table.add_column("Date", style="cyan")
    table.add_column("Time", style="yellow")
    table.add_column("Type", style="bold")
    table.add_column("Item", style="dim")
    table.add_column("Course")
    table.add_column("Duration (min)", justify="right")
    
    for p in placements:
        start = p["start_datetime"]
        course = p.get("course_name", "-")
        item_text = f"{p['related_type'].capitalize() if p['related_type'] else ''} ID: {p['related_id'] or ''}"
        
        table.add_row(
            start[:10],
            start[11:16],
            p["type"].capitalize(),
            item_text,
            course,
            str(p["duration"])
        )
    rprint(table)

# --- Upgraded Function for CLI Bar Chart ---

def print_progress_chart(user_id):
    """
    Shows a progress chart for leaves with resource_type breakdown.
    UPGRADED to use rich.Table for a text-based bar chart.
    """
    with get_conn() as conn:
        c = conn.cursor()
        # Your original SQL query is fine for getting the data
        c.execute(
            """
            SELECT status, resource_type, COUNT(*) as count 
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
            GROUP BY status, resource_type
            ORDER BY resource_type, status
            """,
            (user_id,)
        )
        data = c.fetchall()
    
    if not data:
        console.print("[yellow]No leaf data available for progress chart.[/yellow]")
        return
    
    # 1. Calculate the total count to determine the scale of the bars
    total_count = sum(row["count"] for row in data)
    if total_count == 0:
        console.print("[yellow]Total leaf count is zero, cannot draw chart.[/yellow]")
        return
        
    # Set the maximum bar length (e.g., 50 characters)
    MAX_BAR_LENGTH = 50
    
    # 2. Create the Rich Table for the visualization
    table = Table(title=f"[bold #4BC0C0]Leaf Progress Breakdown (Total: {total_count})[/bold #4BC0C0]", show_header=True, header_style="bold magenta")
    table.add_column("Resource Type", style="cyan", min_width=15)
    table.add_column("Status", style="bold", min_width=10)
    table.add_column("Count", justify="right", style="white", min_width=5)
    table.add_column("Progress Bar", style="dim", min_width=MAX_BAR_LENGTH + 2)

    # 3. Process data and populate the table
    for row in data:
        status = row["status"]
        resource_type = row["resource_type"].capitalize()
        count = row["count"]
        
        # Calculate bar length
        percentage = (count / total_count)
        bar_length = int(percentage * MAX_BAR_LENGTH)
        
        # Get color for the bar
        color = STATUS_COLORS.get(status, "white")
        
        # Create the Rich Text bar
        # Filled part of the bar
        filled_bar = Text("█" * bar_length, style=f"bold {color} on {color}")
        # Unfilled part of the bar (to maintain consistent bar length)
        empty_bar = Text(" " * (MAX_BAR_LENGTH - bar_length), style="dim white on black")
        
        # Combine and add percentage label
        progress_text = Text.assemble(
            filled_bar,
            empty_bar,
            Text(f" ({percentage:.1%})", style="white")
        )
        
        table.add_row(
            resource_type,
            status.capitalize(),
            str(count),
            progress_text
        )

    rprint(table)