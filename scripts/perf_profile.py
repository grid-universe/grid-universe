#!/usr/bin/env python3

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import random
from typing import Iterator

from grid_universe.actions import Action
from grid_universe.examples.maze import generate
from grid_universe.step import step
from grid_universe.renderer.image import ImageRenderer


def _action_stream(rng: random.Random) -> Iterator[Action]:
    actions = list(Action)
    while True:
        yield rng.choice(actions)


def _run_episode(
    *,
    width: int,
    height: int,
    steps: int,
    seed: int | None,
    action_seed: int | None,
    render_every: int,
    renderer: ImageRenderer | None,
) -> int:
    state = generate(width=width, height=height, seed=seed)
    rng = random.Random(action_seed if action_seed is not None else (seed or 0))
    actions = _action_stream(rng)

    step_count = 0
    for _ in range(steps):
        action = next(actions)
        state = step(state, action)
        step_count += 1
        if render_every > 0 and (step_count % render_every == 0):
            if renderer is not None:
                _ = renderer.render(state)
        if state.win or state.lose:
            break
    return step_count


def perf_profile(
    *,
    width: int,
    height: int,
    steps: int,
    seed: int | None,
    action_seed: int | None,
    episodes: int,
    render_every: int,
    render_resolution: int,
    sort_by: str,
    top: int,
    out: str,
) -> str:
    profiler = cProfile.Profile()
    profiler.enable()
    renderer = ImageRenderer(resolution=render_resolution) if render_every > 0 else None
    total_steps = 0
    for i in range(episodes):
        total_steps += _run_episode(
            width=width,
            height=height,
            steps=steps,
            seed=None if seed is None else seed + i,
            action_seed=action_seed,
            render_every=render_every,
            renderer=renderer,
        )
    profiler.disable()

    profiler.dump_stats(out)

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats(sort_by)
    stats.print_stats(top)

    summary = (
        f"Episodes: {episodes}\nTotal steps: {total_steps}\nProfile saved to: {out}\n\n"
    )
    return summary + stream.getvalue()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile Grid Universe step() to identify bottlenecks."
    )
    parser.add_argument("--width", type=int, default=15)
    parser.add_argument("--height", type=int, default=15)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--action-seed", type=int, default=0)
    parser.add_argument(
        "--render-every",
        type=int,
        default=5,
        help="Render every N steps (0 disables rendering).",
    )
    parser.add_argument(
        "--render-resolution",
        type=int,
        default=256,
        help="Image render resolution when rendering is enabled.",
    )
    parser.add_argument(
        "--sort",
        dest="sort_by",
        default="cumtime",
        choices=["cumtime", "tottime", "ncalls"],
    )
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--out", type=str, default="profile.pstats")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = perf_profile(
        width=args.width,
        height=args.height,
        steps=args.steps,
        seed=args.seed,
        action_seed=args.action_seed,
        episodes=args.episodes,
        render_every=args.render_every,
        render_resolution=args.render_resolution,
        sort_by=args.sort_by,
        top=args.top,
        out=args.out,
    )
    print(report)


if __name__ == "__main__":
    main()
