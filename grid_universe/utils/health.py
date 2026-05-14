"""Health and damage helpers."""

from grid_universe.components import Health, Dead
from grid_universe.types import EntityID


def apply_damage_and_check_death(
    health_dict: dict[EntityID, Health],
    dead_dict: dict[EntityID, Dead],
    eid: EntityID,
    damage: int,
    lethal: bool,
) -> None:
    """Apply damage to entity and mark dead if lethal or HP reaches zero."""
    if eid in health_dict:
        hp = health_dict[eid]
        new_hp = max(0, hp.current_health - damage)
        health_dict[eid] = Health(current_health=new_hp, max_health=hp.max_health)
        if new_hp == 0 or lethal:
            dead_dict[eid] = Dead()
            health_dict[eid] = Health(current_health=0, max_health=hp.max_health)
    else:
        if lethal:
            dead_dict[eid] = Dead()
