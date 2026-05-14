from grid_universe.components import Blocking
from grid_universe.examples.gameplay_levels import build_level_basic_movement
from grid_universe.renderer.image import ImageRenderer, get_eid_properties_map


def test_image_renderer_renders_state() -> None:
    state = build_level_basic_movement()

    image = ImageRenderer(resolution=64).render(state)

    assert image.mode == "RGBA"
    assert image.size == (64, 45)


def test_eid_properties_map_reflects_state_updates() -> None:
    state = build_level_basic_movement()
    agent_id = next(iter(state.agent))

    assert "blocking" not in get_eid_properties_map(state)[agent_id]

    state.blocking[agent_id] = Blocking()

    assert "blocking" in get_eid_properties_map(state)[agent_id]
