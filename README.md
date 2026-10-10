*This project has been created as part of the 42 curriculum by smachado.*

# Fly-in

## Description

**Fly-in** routes a fleet of drones from a start hub to an end hub through a
graph of zones, in the **fewest possible simulation turns**, while respecting
every movement and capacity rule:

- each zone holds at most `max_drones` drones at a time (default 1; the start
  and end hubs are unlimited);
- each connection lets at most `max_link_capacity` drones start crossing it in
  the same turn (default 1);
- entering a zone costs 1 turn (`normal`, `priority`) or 2 turns
  (`restricted`, where the drone spends one turn *on the connection* and must
  arrive on the next one); `blocked` zones can never be entered;
- `priority` zones are preferred when two routes take the same time.

The program reads a map file, plans every drone, validates the plan turn by
turn against the rules, and prints one line per turn in the required
`D<ID>-<zone>` / `D<ID>-<connection>` format, with a colored view of the
simulation when run in a terminal.

The project is written in Python 3.10+, fully object-oriented and type-safe
(`flake8` and `mypy --strict` clean), and uses **no graph library**: the graph,
Dijkstra and the time-based scheduler are implemented by hand.

## Instructions

Requirements: Python 3.10 or later and `make`.

```bash
make install                                   # creates venv/ and installs flake8, mypy, pytest
make run                                       # runs maps/easy/01_linear_path.txt
make run MAP=maps/hard/02_capacity_hell.txt    # runs another map
./main.py maps/medium/03_priority_puzzle.txt   # same thing, directly
./main.py --no-color maps/easy/02_simple_fork.txt   # plain output only
```

| Target | What it does |
|---|---|
| `make install` | create the virtual environment and install the dependencies |
| `make run` | run the simulation (`MAP=...` to choose the map) |
| `make debug` | run the simulation under `pdb` |
| `make lint` | `flake8 .` + `mypy` with the flags required by the subject |
| `make lint-strict` | `flake8 .` + `mypy . --strict` |
| `make test` | run the unit tests (`pytest`) |
| `make clean` / `make fclean` | remove caches / caches + `venv/` |

Errors never end in a traceback: an invalid map prints
`Erro de parsing na linha N: <cause>`, an unreachable end hub prints
`Erro: não existe caminho ...`, and the program exits with code 1.

## Algorithm explanation

### Pipeline

```
Parser ──► Map ──► Scheduler (+ PathFinder, ReservationTable) ──► plan
                                                                  │
          Renderer ◄── one line per turn ◄── Simulation (the judge) ◄┘
```

| Class | Role |
|---|---|
| `Parser` | reads the file, validates every line, builds the `Map` (clear `ParseError` with line and cause) |
| `Zone`, `Connection`, `Drone`, `Map` | the data model and a hand-made adjacency-list graph |
| `PathFinder` | Dijkstra for one drone on an empty map |
| `ReservationTable` | "agenda" of what is already taken: drones per (zone, turn) and crossings per (connection, turn) |
| `Scheduler` | plans every drone in time, respecting the reservations |
| `Simulation` | **the judge**: validates and executes each turn, independently of the planner |
| `Renderer` | colored terminal output, per-turn panel and final metrics |

Planning (the *player*) and rule checking (the *judge*) are deliberately
separate: every plan is replayed by `Simulation.apply_turn()`, which checks
all the rules again. A planner bug can therefore never produce an invalid
output silently.

### 1. Dijkstra (`PathFinder`)

The cost of a move is the cost of **entering** the destination zone
(1, or 2 for `restricted`); `blocked` zones are never pushed in the queue.
A priority queue (`heapq`) always expands the cheapest zone first, so the
first time the end hub leaves the queue its cost is minimal. Paths are
compared by the key `(cost, -number_of_priority_zones)`: a cheaper path always
wins, and on a tie the path with more `priority` zones wins.

It is run once, to detect a disconnected map (clear error instead of an
infinite loop) and to know the minimal cost `C` of the map.

Plain BFS was rejected: it minimises the number of zones, not the number of
turns (a route through two `restricted` zones has fewer zones but takes longer).

### 2. Scheduling in time with reservations (`Scheduler`)

Several drones cannot simply follow the same shortest path: capacities would
be exceeded. The scheduler uses **prioritised planning with a reservation
table** (the idea behind *cooperative pathfinding*):

1. Drones are planned one by one, in order D1, D2, …, Dn.
2. Each drone runs the same Dijkstra, but on states **(turn, zone)**. From
   `(t, z)` it may:
   - **wait**: go to `(t+1, z)` if zone `z` still has room at turn `t+1`;
   - **move** to a neighbour `v` (not `blocked`) if the connection still has
     room at turn `t+1` and `v` has room on arrival: turn `t+1`, or `t+2` for a
     `restricted` zone (the drone is on the connection during `t+1`).
3. The first time the end hub is reached is the earliest possible arrival;
   ties prefer `priority` zones.
4. The path is written into the reservation table, and the next drone plans
   around it. Paths are converted to "moves per turn" for the judge.

Why it works well:

- **Conflicts** are solved by construction: whoever plans first books first.
- **Distribution over several paths** emerges by itself: when the short route
  is booked at some turn, the next drone finds a parallel route or waits.
- **No deadlock**: start and end hubs are unlimited, so a drone can always
  wait at the start until earlier drones are gone.
- **Always terminates**: after the last reserved turn `L` the map is empty, so
  every drone arrives by `L + C`; states beyond that bound are never explored.

Every official map is solved at the optimum given by the subject
(see the benchmark table below), including the challenger map.

### Complexity, caching and memory

With `Z` zones, `E` connections, `D` drones and `T` the number of turns:

- `PathFinder`: `O((Z + E) log Z)`, computed **once**.
- One drone in time: at most `Z·T` states, each expanding its neighbours plus
  "wait", so `O((Z + E)·T·log(Z·T))`; all drones: `D` times that.
- Paths are **not recalculated**: each drone is planned exactly once and its
  reservations are cached in two dictionaries.
- Memory: the reservation table holds `O(D·T)` entries; one search holds at
  most `O(Z·T)` states.

In practice every official map is planned in under 0.15 s, and 300 drones on a
capacity-1 map in well under a second.

### The judge (`Simulation`)

For each turn it checks, before moving anyone (a turn is atomic):
destination is a neighbour and not `blocked`; drones on a `restricted`
connection arrive on the next turn (they cannot wait); per-connection usage
`≤ max_link_capacity` (only drones *starting* a crossing count, so an arriving
drone frees the connection the same turn); per-zone occupancy at the end of the
turn `≤ max_drones` (space freed this turn can be reused this turn, so a
single-file column advances one step per turn).

## Visual representation

When the output is a terminal, the simulation is shown in color:

- zone names are painted with the `color=` from the map (ANSI true color; a
  name-to-RGB table covers the colors used by the maps, `rainbow` is drawn
  letter by letter, and an unknown color is simply left uncolored);
- drone IDs are bold, and a drone in transit to a `restricted` zone shows the
  connection dimmed;
- after each turn, a panel lists the drones in every occupied zone (with its
  color and type), the drones in transit, and how many were delivered;
- at the end, metrics: delivery turn, cost and waiting turns per drone, total
  turns, average delivery and moves per turn.

This makes it easy to *see* the algorithm: drones splitting into parallel
routes, queues forming in front of a bottleneck, and the two-turn crossing of
`restricted` zones.

When the output is redirected (file or pipe), or with `--no-color`, the program
prints **only** the required format, with no escape codes, no panel and no
metrics, so the output can be checked automatically.

## Example input and output

`maps/easy/02_simple_fork.txt`:

```
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

`./main.py maps/easy/02_simple_fork.txt` (4 turns, the optimum):

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

A `restricted` zone appears as a connection for one turn, then as the zone:

```
D1-start-r
D1-r
D1-goal
```

### Benchmarks (official maps)

| Map | Drones | Turns | Subject optimum |
|---|---|---|---|
| easy/01 linear path | 2 | 4 | 4 |
| easy/02 simple fork | 4 | 4 | 4 |
| easy/03 basic capacity | 4 | 4 | 4 |
| medium/01 dead end trap | 5 | 8 | 8 |
| medium/02 circular loop | 6 | 10 | 10 |
| medium/03 priority puzzle | 5 | 6 | 6 |
| hard/01 maze nightmare | 8 | 13 | 13 |
| hard/02 capacity hell | 12 | 16 | 16 |
| hard/03 ultimate challenge | 15 | 26 | 26 |
| challenger/01 the impossible dream | 25 | 43 | 43 |

Extra maps: `maps/custom/` (cycle, multiple bottlenecks, disconnected graph,
only `restricted` zones, blocked shortcut) and `maps/broken/` (malformed files,
each must produce a clear error).

## Resources

- Dijkstra's algorithm — <https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm>
- D. Silver, *Cooperative Pathfinding* (AIIDE 2005) — reservation tables and
  planning in space-time, the idea behind the scheduler.
- Python `heapq` — <https://docs.python.org/3/library/heapq.html>
- Python `argparse` — <https://docs.python.org/3/library/argparse.html>
- ANSI escape codes (true color) — <https://en.wikipedia.org/wiki/ANSI_escape_code>
- mypy documentation — <https://mypy.readthedocs.io/>
- PEP 8 / PEP 257 — <https://peps.python.org/pep-0008/>, <https://peps.python.org/pep-0257/>

### Use of AI

An AI assistant (Claude) was used throughout the project as a pair programmer
and reviewer:

- **Parser**: reviewing my parser, pointing out bugs (inverted condition,
  wrong indentation in the metadata loop, crashes on lines without `:`) and
  suggesting the missing validations and the shared metadata helper.
- **Design discussions**: separating the judge (`Simulation`) from the planner,
  and choosing reservation-based scheduling over "k fixed paths + deadlock
  detection".
- **Implementation**: writing parts of the pathfinding, scheduler, renderer and
  `main.py` step by step, each step reviewed, tested and explained before
  moving on.
- **Tests and documentation**: generating test cases (edge cases, malformed
  maps, stress tests) and drafting this README.

Every part was read, run and discussed so that I can explain and modify it
myself; the test suite (`make test`) checks all the rules and every official
map.
