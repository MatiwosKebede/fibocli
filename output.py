from rich.tree import Tree
from rich import print as rprint
from rich.table import Table
from rich.console import Console
from rich.text import Text
from db import get_conn
import json  # Kept for potential future use

console = Console()

# --- Configuration ---
status_icons = {
    "locked": "[grey]🔒[/grey]",
    "unlocked": "[yellow]○[/yellow]",
    "active": "[blue]▶[/blue]",
    "completed": "[green]✓[/green]"
}

# Mapping status to a color for the progress bar
STATUS_COLORS = {
    "locked": "grey",
    "unlocked": "yellow",
    "active": "blue",
    "completed": "green"
}

# --- Utility Functions ---
def print_tree(nodes):
    """Print hierarchy as a tree using rich, including course_name, resource_type, and prerequisites."""
    ecology = next((n for n in nodes if n["node_type"] == "ecology"), None)
    if not ecology:
        rprint("[red]No ecology found.[/red]")
        return
    tree_label = f"[bold green]{ecology['name']}[/bold green] (Ecology, ID: {ecology['id']}, Status: {ecology['status'].capitalize()}"
    if ecology["course_name"]:
        tree_label += f", Course: {ecology['course_name']}"
    tree_label += ")"
    tree = Tree(tree_label)
    
    node_map = {n["id"]: n for n in nodes}
    children = {t: [] for t in ["ecology", "forest", "tree", "super_branch", "branch", "sub_branch", "leaf"]}
    for n in nodes:
        if n["node_type"] != "ecology" and n["parent_id"]:
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
            status_icon = status_icons.get(child.get("status", "unknown"), "[red]?[/red]")
            label_parts = [
                f"{status_icon} [b]{child['name']}[/b]",
                f"({child['node_type'].capitalize()}, ID: {child['id']}, Status: {child['status'].capitalize()})"
            ]
            if child.get("course_name"):
                label_parts.append(f"Course: {child['course_name']}")
            if child["node_type"] == "leaf" and child.get("resource_type"):
                label_parts.append(f"Type: {child['resource_type'].capitalize()}")
            if child["node_type"] in ("sub_branch", "leaf") and child.get("prerequisites"):
                prereq_names = [p["name"] for p in child["prerequisites"] if p["name"]]
                if prereq_names:
                    label_parts.append(f"Prereqs: {', '.join(prereq_names)}")

            child_node = parent_node.add(" ".join(label_parts))
            add_children(child_node, next_node_type, child["id"])

    add_children(tree, "ecology", ecology["id"])
    rprint(tree)
    
def print_reviews(reviews):
    """Print pending reviews in a table with course_name and status."""
    table = Table(title="[bold red]Pending Reviews[/bold red]")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Target", style="bold")
    table.add_column("Type")
    table.add_column("Course", style="dim")
    table.add_column("Status", style="yellow")
    table.add_column("Due", style="magenta")
    table.add_column("Duration (min)", justify="right")
    
    for r in reviews:
        course = r.get("course_name", "-")
        status = r.get("status", "unknown").capitalize()
        table.add_row(
            str(r["id"]),
            f"{r['name']} (ID: {r['target_id']})",
            r["target_type"].capitalize(),
            course,
            status,
            r["scheduled_date"],
            str(r["estimated_duration"])
        )
    rprint(table)

def print_schedule(placements):
    """Print scheduled items in a table with course_name."""
    table = Table(title="[bold blue]Weekly Schedule[/bold blue]")
    table.add_column("Date", style="cyan")
    table.add_column("Time", style="yellow")
    table.add_column("Type", style="bold")
    table.add_column("Item", style="dim")
    table.add_column("Course")
    table.add_column("Duration (min)", justify="right")
    
    for p in placements:
        start = p["day"]  # Updated to use 'day' from pack_schedule_for_week
        course = p.get("course_name", "-")
        item_text = f"{p['name']} (ID: {p['review_id']})"
        
        table.add_row(
            start,
            "08:00",  # Simplified, as pack_schedule_for_week assumes 08:00 start
            "Review",
            item_text,
            course,
            str(p["duration"])
        )
    rprint(table)

def print_progress_chart(user_id: int):
    """
    Shows a progress chart for leaves with resource_type breakdown.
    Upgraded with:
    - Rich.Table for text-based bar chart
    - Status-based visualization (locked, unlocked, active, completed)
    - Summary statistics with status counts
    - Sorting by total count
    """
    console = Console()

    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT 
                    l.status,
                    l.resource_type,
                    COUNT(*) as count
                FROM leaves l
                WHERE l.sub_branch_id IN (
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
                ) AND l.is_deleted = 0
                GROUP BY l.status, l.resource_type
                ORDER BY l.resource_type, l.status
                """,
                (user_id,)
            )
            data = c.fetchall()
        except sqlite3.OperationalError as e:
            console.print(f"[red]❌ Database error: {e}. Ensure the leaves table exists and includes status and resource_type columns.[/red]")
            return

    if not data:
        console.print("[yellow]No leaf data available for progress chart.[/yellow]")
        return

    # Calculate total count and summary statistics
    total_count = sum(row["count"] for row in data)
    if total_count == 0:
        console.print("[yellow]Total leaf count is zero, cannot draw chart.[/yellow]")
        return

    # Group data by resource_type for summary
    type_summary = {}
    for row in data:
        resource_type = row["resource_type"].capitalize() if row["resource_type"] else "Unknown"
        status = row["status"]
        count = row["count"]
        if resource_type not in type_summary:
            type_summary[resource_type] = {"total": 0, "statuses": {}}
        type_summary[resource_type]["total"] += count
        type_summary[resource_type]["statuses"][status] = {"count": count}

    # Sort resource_types by total count (descending)
    sorted_types = sorted(type_summary.items(), key=lambda x: x[1]["total"], reverse=True)

    # Create the Rich Table
    table = Table(
        title=f"[bold #4BC0C0]Leaf Progress Breakdown (Total Leaves: {total_count})[/bold #4BC0C0]",
        show_header=True,
        header_style="bold magenta",
        border_style="dim white"
    )
    table.add_column("Resource Type", style="cyan", min_width=15)
    table.add_column("Status", style="bold", min_width=10)
    table.add_column("Count", justify="right", style="white", min_width=5)
    table.add_column("Progress Bar", style="dim", min_width=55)

    # Set maximum bar length
    MAX_BAR_LENGTH = 40

    # Populate the table
    for resource_type, summary in sorted_types:
        for status in sorted(summary["statuses"].keys()):
            count = summary["statuses"][status]["count"]
            percentage = count / total_count if total_count > 0 else 0
            bar_length = int(percentage * MAX_BAR_LENGTH)
            color = STATUS_COLORS.get(status, "white")
            filled_bar = Text("█" * bar_length, style=f"bold {color}")
            empty_bar = Text(" " * (MAX_BAR_LENGTH - bar_length), style="dim white")
            progress_text = Text.assemble(
                filled_bar,
                empty_bar,
                Text(f" {percentage:.1%}", style="white")
            )
            table.add_row(
                resource_type,
                status.capitalize(),
                str(count),
                progress_text
            )
        # Add a separator row for each resource_type
        table.add_row("", "", "", "", style="dim white")

    # Add summary statistics
    status_totals = {}
    for row in data:
        status = row["status"]
        status_totals[status] = status_totals.get(status, 0) + row["count"]

    console.print(table)
    console.print("\n[bold cyan]Summary Statistics:[/bold cyan]")
    summary_table = Table(show_header=False, border_style="dim white")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")
    for status, count in sorted(status_totals.items()):
        percentage = count / total_count if total_count > 0 else 0
        summary_table.add_row(
            f"{status.capitalize()} Leaves",
            f"{count} ({percentage:.1%})"
        )
    console.print(summary_table)