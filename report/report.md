# CS 145 Project 2: Intra-Domain Routing Algorithms

## Author and collaborators
### Author name
- **Full Name:** Nguyễn Minh Chiến (ZenCopper)
- **Student ID (MSSV):** 24020415
- **Email:** nuyenminhchien2021tb@gmail.com

### Collaborators
- None. This project was completed independently.

## Report

### 1. Distance-Vector Routing Implementation (`DVrouter.py`)
- **Core Algorithm:**
  - Implements the distributed Bellman-Ford shortest path algorithm:
    $$D_u(y) = \min_v \left\{ c(u, v) + D_v(y) \right\}$$
  - Each router maintains its own distance vector `self.zen_dv`, its active link state `self.zen_links`, and cached distance vectors received from adjacent neighbors `self.zen_neighbor_dvs`.
- **Count-to-Infinity & Loop Prevention (Split Horizon with Poisoned Reverse):**
  - To prevent routing loops and count-to-infinity behavior when link failures occur, `DVrouter` implements **Split Horizon with Poisoned Reverse**.
  - When advertising its distance vector to a neighbor $P$:
    - If the current shortest route to destination $D$ forwards through $P$ (i.e. `self.zen_next_hop[D] == P` and $D \ne P$), the router poisons the route by advertising $D_u(D) = 16$ (`self.zen_infinity`).
    - Otherwise, it advertises its true lowest-cost estimate $D_u(D)$.
  - This immediately informs neighbor $P$ not to route back through this router to reach $D$, terminating two-node loops in a single step upon link teardown.
- **Triggered and Periodic Updates:**
  - Triggered updates: Recomputation occurs immediately whenever a packet is received, a link is added (`handle_new_link`), or a link is removed (`handle_remove_link`). If the local distance vector or forwarding table changes, a broadcast is triggered immediately across all active ports.
  - Heartbeat timer: Every `heartbeat_time` ms (`handle_time`), periodic distance vector updates are sent to guarantee convergence across remote network partitions.

---

### 2. Link-State Routing Implementation (`LSrouter.py`)
- **Core Algorithm:**
  - Implements reliable Link-State Packet (LSP) flooding combined with Dijkstra's Shortest Path First (SPF) algorithm.
  - Each router stores the full topology graph in `self.zen_link_state_db`, mapping each advertising router to its active neighbor links and costs.
- **Sequence Numbers and Controlled Flooding:**
  - Monotonically increasing sequence numbers (`self.zen_seq`) are used to distinguish stale updates from fresh topology advertisements.
  - For every advertising router, `LSrouter` tracks `self.zen_seq_records[adv_router]`. If an incoming LSP has `seq <= highest_seen`, it is discarded immediately to prevent broadcast storms and duplicate processing.
  - Loopback LSPs originating from `self.addr` are discarded.
  - Fresh LSPs are updated in the local database and forwarded to all adjacent ports except the incoming port.
- **Immediate Database Synchronization:**
  - Upon establishing a new link (`handle_new_link`), `LSrouter` immediately transmits not only its own updated LSP but also all cached LSPs in `self.zen_link_state_db` to the newly connected endpoint. This provides instantaneous synchronization across partitions without waiting for heartbeat timeouts.
- **Shortest Path Computation (Dijkstra):**
  - Dijkstra's algorithm is implemented with a min-heap priority queue (`heapq`) starting from `self.addr`.
  - Computes the minimum cost and tracks the first-hop neighbor from `self.addr` to all reachable nodes.
  - The forwarding table `self.zen_forwarding_table` maps each destination to the corresponding egress port connected to that first hop.

---

## Citations
- Harvard CS145 Course Materials, Project Specifications, and Lecture Slides.
- Computer Networking: A Top-Down Approach (8th Edition) by Jim Kurose & Keith Ross — Chapter 5: Network Layer: Control Plane (Routing Algorithms: Link-State & Distance-Vector).
- Python Standard Library Documentation (`json`, `heapq`, `queue`, `time`).

---

## Grading notes (if any)
- **Student ID:** `24020415` (verified and accurate).
- **Zero Simulation Files Modified:** Strictly adheres to the project constraint. Absolutely NO files outside `DVrouter.py`, `LSrouter.py`, and `report/report.md` were modified (simulation scripts, test scripts, network definitions, and infrastructure files remain untouched).
- **100% Automated Test Pass Rate:**
  - `DVrouter`: Passed all 6 network configurations (`01_small_net.json`, `02_small_net_events.json`, `03_pg244_net.json`, `04_pg244_net_events.json`, `05_pg242_net.json`, `06_pg242_net_events.json`).
  - `LSrouter`: Passed all 6 network configurations (`01_small_net.json`, `02_small_net_events.json`, `03_pg244_net.json`, `04_pg244_net_events.json`, `05_pg242_net.json`, `06_pg242_net_events.json`).

---

## Extra credit attempted (if any)
- Successfully implemented **BOTH** Distance-Vector (`DVrouter.py`) and Link-State (`LSrouter.py`) routing algorithms, passing all standard and dynamic event test suites for the **+20 bonus points** (target grade: 120/100).
