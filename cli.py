import click
from db import init_db
from algorithms import plant_leaf, schedule_reviews, show_tree
from output import print_tree, print_schedule

@click.group()
def cli():
    """Ecology CLI: Complete Offline Learning Ecology System"""

@cli.command()
def init():
    """Initialize the ecology database."""
    init_db()
    click.echo("Database initialized.")

@cli.command()
def tree():
    """Show ecology hierarchy as a tree."""
    tree_data = show_tree()
    print_tree(tree_data)

@cli.command()
@click.option('--parent', type=int, required=True, help='Parent node ID')
@click.option('--name', type=str, required=True)
@click.option('--type', type=click.Choice(['leaf', 'sub_branch', 'branch']), required=True)
@click.option('--course', default='', help='Course name')
@click.option('--code', default='', help='Course code')
def plant(parent, name, type, course, code):
    """Plant a node in the ecology."""
    plant_leaf(parent, name, type, course, code)
    click.echo(f"{type} '{name}' planted under parent {parent}.")

@cli.command()
def review():
    """Show and schedule reviews."""
    reviews = schedule_reviews()
    print_schedule(reviews)

if __name__ == '__main__':
    cli()
