# Grid Universe

> Modular, deterministic ECS gridworld for RL research, teaching, and rapid prototyping.

Entity–Component–System engine with ordered systems, procedural generators, Gymnasium wrapper, and extensible movement/objective registries. Build puzzles and action mechanics with portals, powerups, hazards, keys/doors, enemies, and pathfinding – all deterministic and reproducible.

---

<p align="center">
    <a href="https://grid-universe.github.io/grid-universe/">Docs</a> •
    <a href="LICENSE">MIT License</a>
</p>

<p align="center">
    <em>ECS gridworld with procedural generation, deterministic replay, Gymnasium wrapper, and pluggable movements & objectives.</em>
</p>

<p align="center">
    <img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-blue" />
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green" />
    <img alt="Type Checked" src="https://img.shields.io/badge/types-mypy_strict-informational" />
    <img alt="Lint: Ruff" src="https://img.shields.io/badge/lint-ruff-ff69b4" />
    <img alt="Docs" src="https://img.shields.io/badge/docs-mkdocs%20material-374151" />
</p>

## Features

- **ECS core** – Fast component stores with explicit clone or in-place stepping
- **Deterministic** – Procedural generation and rendering derive randomness from explicit seeds
- **Fast iteration** – `GridState` ↔ ECS `State` conversion
- **Rich mechanics** – Portals, keys/doors, pushables, hazards, enemies, powerups (speed, immunity, phasing)
- **RL ready** – Gymnasium env with image obs, structured info, 7-action discrete space
- **Procedural** – Maze generator with configurable density
- **Extensible** – Plugin movement/objectives via registries

---

## Contents

[Hello World](#hello-world) • [Installation](#installation) • [Quick Start](#quick-start) • [ECS Tick Order](#ecs-tick-order) • [Extending](#extending) • [Development](#development)

---

## Hello World

Minimal procedural usage:

```python
from grid_universe.examples.maze import generate
from grid_universe.actions import Action
from grid_universe.step import step

state = generate(width=6, height=6, seed=0)
for a in [Action.RIGHT, Action.DOWN, Action.PICK_UP]:
    state = step(state, a)
print(state.score, state.turn, state.win, state.lose)
```

More examples below. Full API documentation is available at https://grid-universe.github.io/grid-universe/.

---

## Installation

**Requires Python 3.13+**

```bash
pip install -e .              # base
pip install -e ".[dev]"       # + tests, lint, mypy
pip install -e ".[doc]"       # + mkdocs
```

---

## Quick Start

**Procedural Maze**
```python
from grid_universe.examples.maze import generate
from grid_universe.actions import Action
from grid_universe.step import step

state = generate(width=7, height=7, seed=42)
state = step(state, Action.UP)
```

**Manual Level**
```python
from grid_universe.grid.gridstate import GridState
from grid_universe.grid.factories import create_agent, create_exit
from grid_universe.grid.convert import to_state
from grid_universe.movements import CardinalMovement
from grid_universe.objectives import ExitObjective

gridstate = GridState(
  width=5,
  height=5,
  movement=CardinalMovement(),
  objective=ExitObjective(),
  seed=123,
  step_cost=1,
)
gridstate.add((1, 1), create_agent())
gridstate.add((3, 3), create_exit())
state = to_state(gridstate)
```

**Gymnasium**
```python
from grid_universe.env import GridUniverseEnv
from grid_universe.examples.maze import generate

env = GridUniverseEnv(initial_state_fn=generate, width=7, height=7, seed=7)
obs, info = env.reset()
obs, reward, term, trunc, info = env.step(0)  # Action.UP
```

**Determinism**: use explicit seeds for procedural generation and rendering.

---

## ECS Tick Order

Each `step()` returns an updated state. By default, it works on a clone of the
input state. Use `step(..., in_place=True)` to update the input state directly
on hot paths.

The action pipeline runs in this order:

1. `snapshot_positions` – capture positions for movement interactions
2. `moving_system` – autonomous movers
3. `pathfinding_system` – chasers
4. **Action** – movement/pickup/use-key with sub-steps: push → move → trail → portal → damage → tile → win/lose
5. `status_tick_system` – effect timers
6. `tile_cost_system` – apply costs
7. `turn_system` – increment turn
8. `status_cleanup_system` + `remove_entities` – cleanup

Entities = integer IDs; components live in plain dict stores; systems update
`State` and `StepContext` directly.

---

**Movements** (via `MOVEMENT_REGISTRY`): `cardinal`, `wrap`, `slippery`, `windy`, `gravity`, `mirror`

**Objectives** (via `OBJECTIVE_REGISTRY`): `exit`, `collect`, `collect_and_exit`, `unlock`, `push`

**Gym Env**: `Discrete(7)` actions, `(H,W,4)` RGBA image obs + info dict (agent health/effects/inventory, score, turn). Reward = delta score.

---

## Extending

- **Movement**: Subclass `BaseMovement` with `name`, `description`, `function` → register in `MOVEMENT_REGISTRY`
- **Objective**: Subclass `BaseObjective` with `name`, `description`, `functions` → register in `OBJECTIVE_REGISTRY`  
- **Component**: Add dataclass to `State` + `Entity` + converters
- **System**: Update `State` and `StepContext` directly; insert in `step()` order
- **Rendering**: Extend `DEFAULT_IMAGE_MAP` or add recolor rules

**Rules**: derive randomness from explicit seeds; update positions through
`set_position_component` / `remove_position_component`; no global state.



---

## Structure

```
grid_universe/
  state.py, step.py           # Core State, step pipeline
  actions.py                  # Action enum
  movements.py, objectives.py # Registries for movements/objectives
  env.py                      # Gymnasium wrapper
  components/                 # properties/ (Position, Health, etc.), effects/ (Speed, Immunity, etc.)
  systems/                    # Systems (movement, portal, damage, collectible, etc.)
  grid/                       # Grid representation
  renderer/                   # Image renderer, texture loading
  utils/                      # ECS, grid, status, inventory, maze gen, etc.
  examples/                   # maze.py, gameplay_levels.py, cipher_objective_levels.py
  assets/                     # Texture packs
tests/, docs/, scripts/
```

---

## Development

```bash
pytest                    # tests
ruff format . && ruff check . --fix  # lint
mypy grid_universe        # types
mkdocs serve              # docs at http://127.0.0.1:8000
```

**Principles**: determinism, composable systems, explicit registries, clear state-update boundaries.

---

## License

MIT – see [LICENSE](LICENSE).
