
# 🌿 Ecology CLI v1.2

**Version:** 1.2
**Date:** October 06, 2025
**Author:** Matiwos Kebede

A **fully offline, hierarchical learning management system (CLI)** designed for structured study of sequential resources (books, courses, programming topics, etc.), with **wave-based planting**, **Fibonacci sequencing**, **unlock/prerequisite management**, and **adaptive spaced reviews**.

---

## 🚀 Features

### Hierarchy & Structure

* 🌍 **Ecology → 🌳 Forest → 🌲 Tree → 🌴 super_branch Branch → 🌿 Branch → 🍀 Sub-Branch → 🍃 Leaf**
* Wave-based planting:

  * Nodes are planted in **waves**.
  * **Fibonacci sequence** determines number of child nodes per wave.
  * Continuous leaf numbering across waves and concurrent sub-branches.
* Each node has a **status**:

  * `locked` – cannot be planted until prerequisites complete.
  * `unlocked` – ready to plant.
  * `active` – currently planting/studying.
  * `pending` – paused.
  * `completed` – planting/review finished.

### Prerequisites & Unlock Logic

* Nodes unlock **sequentially** using prerequisites.
* Completing a node triggers:

  * Update of dependent nodes.
  * Unlocking of next wave.
  * Integration period (10% of total child planting duration).
* Automation ensures **first node at each level is unlocked by default**.

### Review & Scheduling

* Leaf, sub-branch, and parent nodes have **review durations** calculated using:

  * `difficulty × importance / understanding`
  * Integration periods and child averages for higher-level nodes.
* Review gap follows **Fibonacci-based spaced repetition**.
* Only **unlocked/pending nodes** are scheduled for review.

### Automation

* `create resource --prerequisites sequential` automatically creates chained nodes.
* Completing nodes triggers:

  * Unlocking next nodes/waves.
  * Propagation of attributes (`understanding`, `difficulty`, `importance`, `planting_duration`) up the hierarchy.
* Wave completion + integration triggers **next wave unlock**.

---

## 🛠️ Installation

```bash
git clone https://github.com/<your-username>/ecology-cli.git
cd ecology-cli
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

---

## ⚡ CLI Commands

```bash
fibocli init [--overwrite]                   # Initialize DB
fibocli signup | login | logout | whoami
fibocli create [ecology|forest|tree|...] --name <name> [--template <template>]
fibocli create resource --template <template> --prerequisites sequential
fibocli plant --node-type <type> --node-id <id> --duration <hh:mm>
fibocli update-status --node <id> --status <active|pending|completed>
fibocli unlock --node <id>                  # Manual unlock override
fibocli status --node <id>                  # Show timers, attributes, wave
fibocli list-nodes --node-type leaf
fibocli hierarchy                             # Display hierarchy (Rich Tree)
fibocli schedule-reviews [date]
fibocli list-reviews
fibocli perform-review --review-id <id> --understanding <0.1-1.0>
fibocli reschedule-review <id> <YYYY-MM-DD>
fibocli pack --week <start-date>
fibocli backup | restore
```

---

## 📂 Database (High-level)

* Tables for each node type: `ecology`, `forest`, `tree`, `super_branch`, `branch`, `sub_branch`, `leaf`.
* Columns:

  * `id`, `name`, `parent_id`, `status`, `planting_duration`, `study_days`, `difficulty`, `importance`, `understanding`, `created_at`, `completed_at`.
* `prerequisites` table:

  * `(node_type, node_id, prerequisite_type, prerequisite_id, is_completed)`
* `waves` table:

  * Tracks `wave_index`, `fibonacci_index`, `state`, child nodes per wave.
* `reviews` table:

  * `(id, node_type, node_id, scheduled_date, duration_hours, is_integration, fibonacci_index, status, created_at, completed_at)`

---

## 📈 Wave & Leaf Logic

* **Wave progression** follows Fibonacci sequence:

  * Wave 1 → 1 leaf
  * Wave 2 → 1 leaf
  * Wave 3 → 2 leaves
  * Wave 4 → 3 leaves …
* **Leaf numbering** is continuous across waves and concurrent sub-branches.
* **Sub-branch waves**: multiple sub-branches can be planted concurrently based on Fibonacci wave count.
* **Integration period**: 10% of child planting duration after each wave.
* **Parent nodes** automatically propagate attributes from children.

---

## 📝 Example Workflow

1. Create resource `The Linux Command Line`:

   * Chapters auto-created as leaves with sequential prerequisites.
2. Plant **Chapter 1** (status → active):

   * Record 90 min planting.
3. Complete **Chapter 1**:

   * Status → completed.
   * Unlocks **Chapter 2** automatically.
   * Schedules first review for Chapter 1.
4. Next wave of leaves/sub-branch unlocks after:

   * Current wave leaves completed.
   * Integration period (10%) finished.
5. Parent branch/tree attributes updated automatically.

---

## ⚙️ Limitations

* No password reset via CLI.
* Single-user offline only.
* Settings (difficulty/importance/understanding multipliers) fixed; can be made user-editable in future versions.
* Multi-user, sync, and GUI planned for later versions.

---

## 🌟 Future Improvements

* GUI with drag-and-drop hierarchy.
* Multi-user collaboration and cloud sync.
* Customizable review formulas.
* AI-assisted auto-scheduling of nodes based on study habits.
* Gamification: badges, progress bars, streaks.

---

## 🔗 References

* [Rich library](https://rich.readthedocs.io/) for CLI tree visualization.
* Fibonacci sequence for wave-based learning: classical sequence applied to adaptive learning.
