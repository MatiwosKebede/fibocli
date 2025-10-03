# Hierarchical Learning Ecology with Wave-based Progression and Fibonacci Review Scheduling

## 1. Hierarchy Overview

The system models knowledge as a **tree-like learning ecology**:

```
Ecology
 └─ Forest
     └─ Tree
         └─ Super-branch
             └─ Branch
                 └─ Sub-branch
                     └─ Leaves (atomic learning units)
```

* **Leaves**: smallest unit of learning, e.g., a concept, fact, or skill.
* **Sub-branches**: group related leaves.
* **Branches, Super-branches, Trees, Forests, Ecology**: progressively higher-level aggregates.

**Key Principle:** A parent node is only considered “complete” when all of its children (direct descendants) are completed.

---

## 2. Planting Waves

Learning units are introduced in **waves**, following **Fibonacci progression**:

* **Wave number:** Each parent node tracks a `wave_number` starting from 1.
* **Wave quota:** Number of children in a wave is `Fib(wave_number)`.
* **Sequential execution:** Children within a wave are learned sequentially:

  * Child 2 starts **after Child 1 is completed**.
  * Multiple waves proceed in order; the next wave starts **after the previous wave completes**.

**Example:**
Sub-branch `X` with 4 waves of leaves:

1. **Wave 1:** 1 leaf → complete → next wave starts
2. **Wave 2:** 1 leaf → complete → next wave starts
3. **Wave 3:** 2 leaves → Leaf 2 starts after Leaf 1 finishes
4. **Wave 4:** 3 leaves → sequential execution
   …and so on.

* Every new **sub-branch** starts its wave count from 1.
* Every new **branch** starts planting its sub-branches from Wave 1, independent of other branches.

---

## 3. Review Scheduling: Fibonacci-Based Intervals

* **Leaf Reviews:** After completing a leaf, schedule reviews using **Fibonacci-based intervals**:

```
Next Review Interval (days) = Base Completion Days × Fib(Review Index)
```

* **Example:** Leaf base completion = 3 days → review gaps:

| Wave # | Review Interval |
|--------|----------------|
| 1      | 3 days         |
| 2      | 3 days         |
| 3      | 6 days         |
| 4      | 9 days         |
| 5      | 15 days        |
| 6      | 24 days        |

* **Integration Reviews:** After all children of a parent node are complete:

  * Schedule a **single review for the parent**, aggregating all child learning.
  * Interval can be sum of children base completion × Fibonacci index.

---

## 4. Completion & Propagation Logic

1. **Leaf Completion:** Marks the leaf as done. Triggers:

   * Next leaf in the wave (if any) starts.
   * If last leaf of the wave → next wave starts.
2. **Sub-branch Completion:** Occurs when all leaves and waves are finished. Triggers:

   * **Sub-branch integration review** consolidating all leaves.
   * Notifies the parent branch to start next child sub-branch (if any).
3. **Branch/Super-branch/Tree/Forest/Ecology Completion:** Follows the same principle:

   * Complete only when all direct children are done.
   * Schedule **integration review** at each level.
4. **Recursive Propagation:** Completion and integration reviews propagate **upwards** through the hierarchy, creating a clear chain of knowledge consolidation.

---

## 5. Summary of Rules

| Concept             | Rule                                                                                                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------- |
| Leaf                | Smallest unit; review scheduled via Fibonacci intervals; sequential within wave.                            |
| Sub-branch          | Complete when all leaves complete; schedule integration review.                                             |
| Branch+             | Complete when all children complete; schedule integration review.                                           |
| Wave                | Independent per parent; children inside a wave are sequential; number of children = Fibonacci(wave_number). |
| Review Intervals    | `Next Review = Base Completion Days × Fibonacci Index`.                                                     |
| Sequential Chaining | Child[i+1] starts after Child[i] completes.                                                                 |
| Integration Review  | After all children complete, for knowledge consolidation at parent level.                                   |

---

## 6. Example Flow

* **Sub-branch X** has 3 leaves and base completion 3 days:

  1. Leaf 1 → complete → schedule next review in 3 days
  2. Leaf 2 → complete → schedule next review in 3 days
  3. Leaf 3 → complete → schedule next review in 6 days

* **Sub-branch integration review** triggers after Leaf 3 completes.

* **Branch integration review** triggers after all sub-branches complete.

* The **entire ecology grows like a living Fibonacci tree**, waves planting progressively, and review intervals naturally expand for long-term retention.

---

✅ **Key Advantages**

1. **Scalable:** Works from leaf to ecology.
2. **Sequential & Structured:** No chaos—children follow waves and parents follow integration logic.
3. **Optimized for Memory:** Fibonacci intervals for reviews align with cognitive science.
4. **Traceable Progress:** Wave numbers + integration reviews allow tracking growth over time.

---
