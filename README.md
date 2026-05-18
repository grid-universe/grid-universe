# Grid Universe

> A deterministic Entity-Component-System gridworld for games, agents, and rapid
> research prototypes.

Grid Universe is a small, strongly typed Python engine for turn-based grid
worlds. It combines an ECS simulation core, a grid-centric state representation,
a Gymnasium environment wrapper, procedural examples, and a Pillow/NumPy
renderer. Built-in mechanics include movement variants, portals, keys and
doors, pushable boxes, hazards, enemies, power-ups, rewards, costs, and
objective registries.

<p align="center">
  <a href="https://grid-universe.github.io/grid-universe/">Docs</a> |
  <a href="LICENSE">MIT License</a>
</p>

<p align="center">
  <img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-blue" />
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green" />
  <img alt="Types: mypy strict" src="https://img.shields.io/badge/types-mypy%20strict-informational" />
  <img alt="Lint: Ruff" src="https://img.shields.io/badge/lint-ruff-ff69b4" />
  <img alt="Docs: MkDocs Material" src="https://img.shields.io/badge/docs-mkdocs%20material-374151" />
</p>

## Features

- **Two state models**: use `GridState` for spatial state, `State` for ECS simulation
- **Deterministic by design**: generation and rendering are driven by explicit seeds
- **Gymnasium ready**: `Discrete(7)` actions with image or symbolic observations
- **Composable mechanics**: components plus ordered systems, without inheritance-heavy game objects
- **Built-in registries**: movements and objectives can be swapped per level
- **Renderer included**: image maps, grouped recoloring, corner icons, and movement glyphs

## Installation

Grid Universe requires Python 3.13 or newer.

```bash
pip install -e .
pip install -e ".[dev]"
pip install -e ".[doc]"
```

## Quick Start

Run a procedural maze directly through the simulation step function:

```python
from grid_universe.actions import Action
from grid_universe.examples.maze import generate
from grid_universe.step import step

state = generate(width=7, height=7, seed=42)
state = step(state, Action.RIGHT)
state = step(state, Action.DOWN)
state = step(state, Action.PICK_UP)

print(state.score, state.turn, state.win, state.lose)
```

Build a small grid state, then convert it to ECS state:

```python
from grid_universe.grid.convert import to_state
from grid_universe.grid.factories import create_agent, create_exit
from grid_universe.grid.gridstate import GridState
from grid_universe.movements import CardinalMovement
from grid_universe.objectives import ExitObjective

grid = GridState(
    width=5,
    height=5,
    movement=CardinalMovement(),
    objective=ExitObjective(),
    seed=123,
    step_cost=1,
)
grid.add((1, 1), create_agent())
grid.add((3, 3), create_exit())

state = to_state(grid)
```

Use the Gymnasium wrapper for RL-style loops:

```python
from grid_universe.env import GridUniverseEnv
from grid_universe.examples.maze import generate

env = GridUniverseEnv(initial_state_fn=generate, width=7, height=7, seed=7)
obs, info = env.reset()
obs, reward, terminated, truncated, info = env.step(0)  # Action.UP
```

Set `observation_type="gridstate"` to receive a symbolic `GridState` instead of
an RGBA image observation.

## Core Concepts

`State` stores component dictionaries keyed by integer entity IDs. Systems
mutate `State` and a per-step `StepContext`, keeping the reverse position index
in sync through `set_position_component` and `remove_position_component`.

`step()` clones by default. Use `step(..., in_place=True)` only when the caller
owns the input state and wants to avoid clone allocation.

The step pipeline is:

1. Snapshot positions and statuses.
2. Move autonomous `Moving` entities.
3. Move pathfinding entities.
4. Apply the requested action.
5. For each movement substep: push, move, trail, portal, damage, tile reward, win/lose.
6. Tick status timers, apply tile cost, increment turn, clean expired/removed entities.

## Built-ins

Actions: `UP`, `DOWN`, `LEFT`, `RIGHT`, `USE_KEY`, `PICK_UP`, `WAIT`.

Movements in `MOVEMENT_REGISTRY`: `cardinal`, `wrap-around`, `mirror`,
`slippery`, `windy`, `gravity`.

Objectives in `OBJECTIVE_REGISTRY`: `exit`, `collect`, `collect_exit`,
`unlock`, `push`.

Texture maps in `IMAGE_MAP_REGISTRY`: `imagen1`, `kenney`, `futurama`.

## Project Layout

```text
grid_universe/
  actions.py                  # action enum
  state.py, runtime.py        # ECS state and per-step context
  step.py                     # ordered simulation pipeline
  movements.py, objectives.py # configurable registries
  env.py                      # Gymnasium environment
  components/                 # properties and effects
  systems/                    # simulation systems
  grid/                       # grid-centric representation and factories
  renderer/                   # image renderer
  utils/                      # shared ECS, grid, status, image, maze helpers
  examples/                   # procedural and hand-built level suites
```

## Development

```bash
ruff format .
ruff check . --fix
mypy
pytest
mkdocs serve
```

Docs are built with MkDocs Material and mkdocstrings. The API reference is under
`docs/api`.

## License

MIT. See [LICENSE](LICENSE).
