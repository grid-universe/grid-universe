from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from grid_universe.components import Position
from grid_universe.components.properties.status import Status
from grid_universe.types import EntityID
from grid_universe.utils.ecs import PositionIndex

if TYPE_CHECKING:
    from grid_universe.state import State


@dataclass
class StepContext:
    """Contextual data for the current step.

    Attributes:
        prev_position: Snapshot of positions before movement this step.
        prev_status: Snapshot of statuses at the beginning of the step.
        trail: Mapping of positions to entities that have occupied them.
        damage_hits: Set of damage events this turn (target, damager, turn).
        position_index: Per-step reverse index from position to entity IDs.
        removed_entity_ids: Entity IDs to delete from component stores at step end.
    """

    position_index: PositionIndex
    prev_position: dict[EntityID, Position] = field(default_factory=dict)
    prev_status: dict[EntityID, Status] = field(default_factory=dict)
    trail: dict[Position, set[EntityID]] = field(default_factory=dict)
    damage_hits: set[tuple[EntityID, EntityID, int]] = field(default_factory=set)
    removed_entity_ids: set[EntityID] = field(default_factory=set)


def make_step_context(state: "State") -> StepContext:
    """Create the runtime context shared by systems during one step."""
    return StepContext(
        prev_status=dict(state.status),
        position_index=state._position_index,
    )


def snapshot_positions(ctx: StepContext, state: "State") -> None:
    """Capture current positions for movement interaction checks."""
    ctx.prev_position = dict(state.position)
