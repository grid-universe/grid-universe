# Grid Universe

> A modular, deterministic, fully *immutable* ECS gridworld for research, teaching, prototyping RL ideas, and building puzzle / action mechanics fast.

Grid Universe combines a pure Entity–Component–System model (functional, ordered systems) with flexible level-building and rendering tools. It ships with procedural generators, a Gymnasium wrapper, and extensible registries for movement and objectives.

Built for: rapid experimentation (movement/objective swaps), reproducible RL benchmarks, curriculum & teaching demos, and custom gameplay mechanics (portals, powerups, hazards, pushing, keys/doors, moving enemies, pathfinding chasers, etc.).

---

<p align="center">
    <a href="https://grid-universe.github.io/grid-universe/">Docs</a> •
    <a href="LICENSE">MIT License</a>
</p>

<p align="center">
    <em>Immutable ECS gridworld with procedural generation, deterministic replay, Gymnasium wrapper, and pluggable movement & objectives.</em>
</p>

<p align="center">
    <!-- Badges (replace placeholders with real CI/coverage later) -->
    <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-blue" />
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green" />
    <img alt="Type Checked" src="https://img.shields.io/badge/types-mypy_strict-informational" />
    <img alt="Lint: Ruff" src="https://img.shields.io/badge/lint-ruff-ff69b4" />
    <img alt="Docs" src="https://img.shields.io/badge/docs-mkdocs%20material-374151" />
</p>

## Why Grid Universe?

- **Immutable ECS core** – Each tick is a pure transformation (`State -> State`), simplifying debugging & reproducibility.
- **Deterministic** – All randomness is derived from `(seed, turn)`; rollouts & renders are reproducible bit‑to‑bit across machines.
- **Fast iteration** – Author a mutable `Level` → convert to immutable `State` → simulate; round‑trip for editors.
- **Rich mechanics** – Portals, keys/doors, pushables, moving entities, hazards, pathfinding chasers, powerup effects (speed, immunity, phasing) with time/usage limits.
- **RL ready** – Native Gymnasium environment: image + structured info; reward = delta score; discrete 7‑action space.
- **Procedural generation** – Maze generator with density knobs for enemies, keys, portals, hazards, rewards.
- **Extensible** – Register new movement & objective functions; add systems, components, texture mappings without invasive changes.

---

## Table of Contents (concise)

- [Hello World](#hello-world)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Seeding & Determinism](#seeding--determinism)
- [ECS Tick Order](#ecs-tick-order)
- [Features Matrix](#features-matrix)
- [Movement & Objectives Reference](#movement--objectives-reference)
- [Gym Environment](#gym-environment)
- [Extending](#extending)
- [Rendering & Assets](#rendering--assets)
- [Project Structure](#project-structure)
- [Development](#development)
- [License](#license)

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

More examples below and full docs: https://grid-universe.github.io/grid-universe/

---

## Installation

Requirements

- Python 3.11+

Base install (editable):

```bash
pip install -e .
```

Optional extras (from `pyproject.toml`):

```bash
pip install -e ".[dev]"   # tests, lint, type checking
pip install -e ".[doc]"   # mkdocs site
```

Quick verification:

```bash
python -c "import grid_universe as _; print('OK')"
```

### Dev Container

If using VS Code / Dev Containers: a pre-configured Python environment (see `.devcontainer/`).

---

## Quick Start

### Procedural (one-liner)

Generate a random maze state, take a step, and render:

```python
from grid_universe.examples.maze import generate
from grid_universe.actions import Action
from grid_universe.step import step
from grid_universe.renderer.texture import TextureRenderer

state = generate(width=7, height=7, seed=42)
state = step(state, Action.UP)
img = TextureRenderer().render(state)
img.save("frame.png")
```

### Building a Level

Build a 5×5 world manually using factories then convert to runtime `State`:

```python
from grid_universe.levels.grid import Level
from grid_universe.levels.factories import create_floor, create_agent, create_coin, create_exit
from grid_universe.levels.convert import to_state
from grid_universe.actions import Action
from grid_universe.step import step
from grid_universe.moves import default_move_fn
from grid_universe.objectives import exit_objective_fn

level = Level(width=5, height=5, move_fn=default_move_fn, objective_fn=exit_objective_fn, seed=123)
for y in range(level.height):
    for x in range(level.width):
        level.add((x, y), create_floor())
level.add((1, 1), create_agent(health=5))
level.add((2, 1), create_coin(reward=10))
level.add((3, 3), create_exit())

state = to_state(level)
agent_id = next(iter(state.agent.keys()))

for a in [Action.RIGHT, Action.PICK_UP, Action.DOWN, Action.DOWN]:
    state = step(state, a, agent_id=agent_id)
    if state.win or state.lose:
        break
```

### Gymnasium Env

```python
from grid_universe.gym_env import GridUniverseEnv
from grid_universe.examples.maze import generate as maze_generate
import numpy as np

env = GridUniverseEnv(initial_state_fn=maze_generate, render_mode="rgb_array", width=7, height=7, seed=7)
obs, info = env.reset()
done = False
while not done:
    action = int(env.action_space.sample())
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated
img = env.render()
if img: img.save("rollout_last.png")
```

---

---

## Seeding & Determinism

- Provide a seed to generators or `Level`; stored in `State.seed`.
- All stochastic choices (e.g., windy gusts, texture variant selection) derive from hashing `(seed, turn)`.
- Add custom deterministic randomness:

```python
import random
def rng_for_turn(state):
    return random.Random(hash((state.seed or 0, state.turn)))
```

Determinism note: Actions + initial seed fully define subsequent States (pure functional pipeline).

---

## ECS Tick Order

`step()` applies ordered pure systems:

1. Snapshot previous positions (`position_system`)
2. Autonomous movers (`moving_system`)
3. Pathfinding chasers (`pathfinding_system`)
4. Effect timers decrement (`status_tick_system`)
5. Trails recorded (`trail_system`)
6. Per sub-move (multi-speed): `push → movement → portal → damage → tile_reward`
7. Post: `status_gc → tile_cost → win → lose → turn++ → gc`

Batch map mutations inside a system before constructing the new `State` for performance.

See deep dive: docs/engine-dev/architecture/systems-order.md

---

## Features Matrix

| Category | Built-in | Extensible | Notes |
|----------|----------|-----------|-------|
| Movement | default, wrap, slippery, windy, gravity (examples) | ✅ via registry | Multi-step speed effects supported |
| Objectives | default, exit, collect, unlock, push | ✅ via registry | Register function name → objective fn |
| Interactions | portals, keys/doors, pushables, reward/cost tiles, hazards, enemies | Add components + systems | Damage & portal order deterministic |
| Effects | speed, immunity, phasing (time/usage limits) | Add effect + limit component | Tick + GC systems handle lifecycle |
| Rendering | texture tiles + recolor groups | Override texture map & group rules | Deterministic variant selection |
| Procedural Gen | Maze (walls, exits, items, powerups, enemies) | Write new generator returning `State` or `Level` | Use seed param for reproducibility |
| RL API | Gymnasium wrapper (image+info) | Add wrappers | Reward = delta score |
| Multi-Agent Core | Data model supports many agents | RL wrapper (single agent default) | Extend Gym env for multi-agent |

---

## Movement & Objectives Reference

Built-in movement function names (see `moves.py`):

Registry keys: `default`, `cardinal`, `wrap`, `mirror`, `slippery`, `windy`, `gravity`.

Built-in objective function names (see `objectives.py`):

Registry keys: `default`, `collect`, `exit`, `collect_exit`, `unlock`, `push`.

Registries:

```python
from grid_universe.moves import MOVE_FN_REGISTRY
from grid_universe.objectives import OBJECTIVE_FN_REGISTRY
print(MOVE_FN_REGISTRY.keys())
print(OBJECTIVE_FN_REGISTRY.keys())
```

---

## Gym Environment

Observation dict (summary):

- `image`: `(H, W, 4)` RGBA uint8
- `info.agent`: health/max, effects, inventory
- `info.status`: score, phase (`ongoing|win|lose`), turn
- `info.config`: move/objective names, seed, width, height

Action space: `Discrete(7)` → `[UP, DOWN, LEFT, RIGHT, USE_KEY, PICK_UP, WAIT]`.

Reward: `score(t) - score(t-1)`.

Minimal random episode:

```python
import numpy as np
from grid_universe.gym_env import GridUniverseEnv
from grid_universe.examples.maze import generate as maze_generate

env = GridUniverseEnv(initial_state_fn=maze_generate, width=8, height=8, seed=123, render_mode="texture")
obs, info = env.reset()
done = False
total = 0
while not done:
    action = int(env.action_space.sample())
    obs, r, term, trunc, info = env.step(action)
    total += r
    done = term or trunc
print("Episode reward:", total)
```

Full schema & details: docs/agent-dev/gym/observations.md

---

## Extending

| Domain | Steps |
|--------|-------|
| Movement | Implement `MoveFn(state, eid, action) -> Sequence[Position]` → register in `MOVE_FN_REGISTRY` |
| Objective | Implement `ObjectiveFn(state, agent_id) -> bool` → register in `OBJECTIVE_FN_REGISTRY` |
| Component | Add dataclass + store to `State` + map in the mutable `Entity` spec + adapt conversions |
| System | Pure `State -> State`; insert in `step()` ordering appropriately |
| Effect | Add effect + optional limit components; integrate in status tick + GC |
| Rendering | Extend `DEFAULT_TEXTURE_MAP`, add group rule for recoloring |
| Level Factories | Add helpers in `levels/factories.py` |

Guidelines:

- Derive RNG from `(state.seed, state.turn)` only.
- Keep updates batched; avoid mutating existing `PMap` references.
- Avoid hidden global state; prefer function arguments.

---

## Rendering & Assets

Texture selection key: `(appearance_name, tuple(sorted(properties))) → path|directory`.

If value is a directory, a deterministic file is chosen from it (seed + turn) so runs are stable.

Group recoloring: keys/doors (by key id), paired portals, etc. Add custom group rules for more categories.

More in: docs/guides/rendering/ and docs/reference/api/#rendering


---

## Architecture Overview

Ordered, pure systems (simplified) executed by `step()`:

1. `position_system` (snapshot previous positions)
2. `moving_system` (autonomous movers)
3. `pathfinding_system` (chasers)
4. `status_tick_system` (effect time limits)
5. `trail_system` (movement traces)
6. Per sub-move (for multi-speed actions): `push_system → movement_system → portal_system → damage_system → tile_reward_system`
7. Post action: `status_gc_system → tile_cost_system → win_system → lose_system → turn++ → gc`

Advantages

- Predictable ordering & testability
- Immutability eliminates hidden side-effects
- Deterministic variant selection & random movement

Entities are opaque integer IDs; component presence in a persistent map defines capabilities; systems only read/write via new `State` instances.

See: `docs/design/ecs_architecture.md` for deep dive.

---

## Observation & Action Schema

Gymnasium (`GridUniverseEnv`) observation dict:

| Key | Type | Shape / Fields |
|-----|------|----------------|
| `image` | `np.ndarray(uint8)` | `(H, W, 4)` RGBA |
| `info.agent.health` | int | current or -1 |
| `info.agent.max_health` | int | max or -1 |
| `info.agent.effects` | list | entries with id, type, limit_type, limit_amount, multiplier |
| `info.agent.inventory` | list | item/key descriptors |
| `info.status.score` | int | cumulative score |
| `info.status.phase` | str | `ongoing|win|lose` |
| `info.status.turn` | int | current turn |
| `info.config.*` | misc | move/objective names, seed, width/height |

Action space: `Discrete(7)` → `[UP, DOWN, LEFT, RIGHT, USE_KEY, PICK_UP, WAIT]`.

Reward: delta of `state.score` per step.

---

## Project Structure

```
grid_universe/
  actions.py       # Action enums
  state.py         # Immutable ECS world snapshot
  step.py          # Orchestrated reducer
  moves.py         # Movement strategies + registry
  objectives.py    # Objective strategies + registry
  gym_env.py       # Gymnasium wrapper
  components/      # properties/ & effects/ dataclasses
  systems/         # Ordered pure systems
  levels/          # Mutable Level/Entity model, factories, converters
  renderer/        # TextureRenderer + helpers
  utils/           # ECS, grid, status, inventory, gc, image, trail
  assets/          # Texture packs (kenney, futurama, ...)
tests/             # Unit + integration tests
docs/              # MkDocs site sources
```

---

## Development

### Tests

```bash
pytest
```

### Lint & Format

```bash
ruff format .
ruff check . --fix
```

### Types

```bash
mypy grid_universe
```

### Docs (local)

```bash
pip install -e ".[doc]"
mkdocs serve
```

### Contributing Workflow

1. Branch (`feat/...` or `fix/...`).
2. Add/modify code + tests.
3. Run tests, lint, type check.
4. Update docs if API surface changes.
5. Open PR with rationale & examples.

Principles: purity, determinism, small composable systems, explicit registries.

---

## License

MIT – see [LICENSE](LICENSE).