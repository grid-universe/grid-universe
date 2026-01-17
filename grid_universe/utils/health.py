"""Health and damage helpers."""

from pyrsistent import PMap

from grid_universe.components import Health, Dead
from grid_universe.types import EntityID


def apply_damage_and_check_death(
    health_dict: PMap[EntityID, Health],
    dead_dict: PMap[EntityID, Dead],
    eid: EntityID,
    damage: int,
    lethal: bool,
) -> tuple[PMap[EntityID, Health], PMap[EntityID, Dead]]:
    """Apply damage to entity and mark dead if lethal or HP reaches zero."""
    if eid in health_dict:
        hp = health_dict[eid]
        new_hp = max(0, hp.health - damage)
        health_dict = health_dict.set(
            eid, Health(health=new_hp, max_health=hp.max_health)
        )
        if new_hp == 0 or lethal:
            dead_dict = dead_dict.set(eid, Dead())
            health_dict = health_dict.set(
                eid, Health(health=0, max_health=hp.max_health)
            )
    else:
        if lethal:
            dead_dict = dead_dict.set(eid, Dead())
    return health_dict, dead_dict
