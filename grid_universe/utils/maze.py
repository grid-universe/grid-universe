"""Maze generation and analysis helpers.

Utility routines for producing and querying grid mazes used in sample levels
or procedural content generation. The algorithms favor clarity and
deterministic reproducibility via an injected ``random.Random`` instance.

Functions
---------
generate_perfect_maze:
    Depth-first backtracking perfect maze generator (no cycles, single path
    between any two open cells) with optional edge opening to guarantee exit
    accessibility on borders.

bfs_path:
    Breadth-first search shortest path (unweighted) between two open cells.

all_required_path_positions:
    Computes the union of waypoints' shortest paths ensuring all required
    positions are visited in sequence.

adjust_maze_wall_percentage:
    Post-processes a perfect maze to tune overall wall density by randomly
    opening a proportion of remaining walls, enabling difficulty scaling or
    aesthetic variation.
"""

import random
from collections import deque

# Type aliases for clarity
Coord = tuple[int, int]
MazeGrid = dict[Coord, bool]  # True = open/floor; False = wall

DIRECTIONS: list[tuple[int, int]] = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def generate_perfect_maze(
    width: int, height: int, rng: random.Random, open_edge: bool = True
) -> MazeGrid:
    """
    Generates a perfect maze using recursive backtracking.
    Returns a dict mapping (x, y) -> bool (True is open/floor, False is wall).
    """
    maze: MazeGrid = {(x, y): False for x in range(width) for y in range(height)}

    def in_bounds(x: int, y: int) -> bool:
        return 0 <= x < width and 0 <= y < height

    def carve(x: int, y: int) -> None:
        maze[(x, y)] = True
        dirs = DIRECTIONS[:]
        rng.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x + dx * 2, y + dy * 2
            bx, by = x + dx, y + dy
            if in_bounds(nx, ny) and not maze[(nx, ny)]:
                maze[(bx, by)] = True
                carve(nx, ny)

    carve(0, 0)

    if open_edge:
        # Ensure right edge is open if cell before is open
        for y in range(height):
            if maze.get((width - 2, y), False):
                maze[(width - 1, y)] = True

        # Ensure bottom edge is open if cell above is open
        for x in range(width):
            if maze.get((x, height - 2), False):
                maze[(x, height - 1)] = True

    return maze


def bfs_path(maze: MazeGrid, start: Coord, goal: Coord) -> list[Coord]:
    """
    Finds the shortest path from start to goal using BFS.
    Only traverses open/floor cells.
    Returns the path as a list of coordinates (including both start and goal), or [] if unreachable.
    """
    if start == goal:
        return [start]
    queue: deque[Coord] = deque([start])
    prev: dict[Coord, Coord] = {}
    visited: set[Coord] = {start}

    while queue:
        pos = queue.popleft()
        for dx, dy in DIRECTIONS:
            np = (pos[0] + dx, pos[1] + dy)
            if maze.get(np, False) and np not in visited:
                prev[np] = pos
                queue.append(np)
                visited.add(np)
                if np == goal:
                    # Early exit
                    queue.clear()
                    break

    # Reconstruct path
    path: list[Coord] = []
    if goal in visited:
        p = goal
        while p != start:
            path.append(p)
            p = prev[p]
        path.append(start)
        path.reverse()
    return path


def all_required_path_positions(
    maze: MazeGrid, start: Coord, required_positions: list[Coord], goal: Coord
) -> set[Coord]:
    """
    Returns all positions along the shortest paths
    from start -> required_position1 -> required_position2 -> ... -> goal.
    """
    essential: set[Coord] = set()
    waypoints = [start] + required_positions + [goal]
    for i in range(len(waypoints) - 1):
        path = bfs_path(maze, waypoints[i], waypoints[i + 1])
        essential.update(path)
    return essential


def adjust_maze_wall_percentage(
    maze: MazeGrid, wall_percentage: float, rng: random.Random
) -> MazeGrid:
    """
    Returns a new MazeGrid with wall percentage controlled.
    wall_percentage=0.0: fully open grid; 1.0: perfect maze (original).
    """
    # All tiles that are not open after maze generation (walls)
    wall_positions: list[Coord] = [pos for pos, is_open in maze.items() if not is_open]
    num_total_walls: int = len(wall_positions)
    num_keep: int = int(num_total_walls * wall_percentage)
    # Shuffle and keep only the desired percentage
    shuffled: list[Coord] = wall_positions[:]
    rng.shuffle(shuffled)
    keep_set: set[Coord] = set(shuffled[:num_keep])
    # Compose new maze grid
    adjusted_maze: MazeGrid = {}
    for pos, is_open in maze.items():
        adjusted_maze[pos] = is_open or (pos not in keep_set)
    return adjusted_maze
