# output.py
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

console = Console()

def print_tree(nodes):
    t = Tree("🌳 Ecology Hierarchy")
    # nodes: list of dicts from v_hierarchy_overview; we'll print leaves last
    roots = [n for n in nodes if n["node_type"]=="ecology"]
    # naive grouping for readability
    for e in roots:
        et = t.add(f"📚 Ecology: {e['name']} (id={e['id']})")
        # find forests with parent_id == e.id
        forests = [n for n in nodes if n["node_type"]=="forest" and n["parent_id"]==e["id"]]
        for f in forests:
            ft = et.add(f"🌲 Forest: {f['name']} (id={f['id']})")
            trees = [n for n in nodes if n["node_type"]=="tree" and n["parent_id"]==f["id"]]
            for tr in trees:
                trt = ft.add(f"🌳 Tree: {tr['name']} (id={tr['id']})")
                sbs = [n for n in nodes if n["node_type"]=="super_branch" and n["parent_id"]==tr["id"]]
                for sb in sbs:
                    sbt = trt.add(f"🔸 SuperBranch: {sb['name']} (id={sb['id']})")
                    brs = [n for n in nodes if n["node_type"]=="branch" and n["parent_id"]==sb["id"]]
                    for br in brs:
                        brt = sbt.add(f"➿ Branch: {br['name']} (id={br['id']})")
                        sbs2 = [n for n in nodes if n["node_type"]=="sub_branch" and n["parent_id"]==br["id"]]
                        for s in sbs2:
                            brt.add(f"🍃 Sub-branch: {s['name']} (id={s['id']})")
    console.print(t)

def print_schedule(items):
    table = Table(title="📅 Schedule")
    table.add_column("Type")
    table.add_column("Related")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Priority", justify="right")
    for it in items:
        table.add_row(it.get("type", ""), str(it.get("related")), str(it.get("start")), str(it.get("end")), str(it.get("priority","")))
    console.print(table)

def print_reviews(revs):
    table = Table(title="📝 Reviews")
    table.add_column("ID")
    table.add_column("Target")
    table.add_column("Due")
    table.add_column("Est Duration")
    for r in revs:
        table.add_row(str(r["id"]), f"{r['target_type']}:{r['target_id']}", r["scheduled_date"], str(r["estimated_duration"]))
    console.print(table)

