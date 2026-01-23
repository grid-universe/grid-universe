# Grid Universe

Grid Universe is a turn-based, grid-based game engine and Gym-compatible environment. It provides two complementary state representations—immutable ECS State for simulation and mutable GridState—along with built-in systems (movement, push, portals, damage, status, rewards/costs), flexible observations (image or GridState), and an image-based renderer.

It’s designed for:

- building puzzle/gridworld games with various built-in components.
- RL / AI agent experiments via a Gymnasium wrapper
- teaching and prototyping

## Installation 

Grid Universe depends on Python 3.11+.

```bash
pip install -e .
```