# Grid Universe

Grid Universe is a turn-based, grid-based game engine and Gym-compatible environment. It provides two complementary state representations: an ECS `State` for simulation and a `GridState` for authoring/editing. The engine includes built-in systems for movement, push, portals, damage, status, rewards/costs, flexible observations (image or GridState), and an image-based renderer.

`step()` returns an updated state. By default, it works on a clone of the input state. Use `step(..., in_place=True)` to update the input state directly for performance-sensitive loops.

It’s designed for:

- building puzzle/gridworld games with various built-in components.
- RL / AI agent experiments via a Gymnasium wrapper
- teaching and prototyping

## Installation 

Grid Universe depends on Python 3.11+.

```bash
pip install -e .
```
