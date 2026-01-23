from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Final, cast

from grid_universe.entity import new_entity_id
from grid_universe.types import EntityID
from grid_universe.components.properties import (
    Agent,
    Appearance,
    Blocking,
    Collectible,
    Collidable,
    Cost,
    Damage,
    Exit,
    Health,
    Inventory,
    Key,
    LethalDamage,
    Locked,
    Moving,
    Pathfinding,
    PathfindingType,
    Portal,
    Pushable,
    Requirable,
    Rewardable,
    Status,
)
from grid_universe.components.effects import (
    Immunity,
    Phasing,
    Speed,
    TimeLimit,
    UsageLimit,
)

# ---- Registries ----

ComponentType = type[Any]
FieldName = str

FIELD_TO_COMPONENT: Final[Mapping[FieldName, ComponentType]] = {
    # Properties
    "agent": Agent,
    "appearance": Appearance,
    "blocking": Blocking,
    "collectible": Collectible,
    "collidable": Collidable,
    "cost": Cost,
    "damage": Damage,
    "exit": Exit,
    "health": Health,
    "inventory": Inventory,
    "key": Key,
    "lethal_damage": LethalDamage,
    "locked": Locked,
    "moving": Moving,
    "pathfinding": Pathfinding,
    "portal": Portal,
    "pushable": Pushable,
    "requirable": Requirable,
    "rewardable": Rewardable,
    "status": Status,
    # Effects (these are separate entities but still components)
    "immunity": Immunity,
    "phasing": Phasing,
    "speed": Speed,
    "time_limit": TimeLimit,
    "usage_limit": UsageLimit,
}

REFERENCE_FIELD_TO_COMPONENT: Final[Mapping[FieldName, ComponentType]] = {
    "pathfind_target_ref": Pathfinding,
    "pathfinding_type": PathfindingType,
    "portal_pair_ref": Portal,
}

# Grid representation nested lists (contain BaseEntity instances); tuple avoids forward-ref type mismatch
NESTED_FIELDS: Final[tuple[FieldName, ...]] = ("inventory_list", "status_list")


def _empty_objs() -> list["BaseEntity"]:
    return []


# ---- Base classes ----


@dataclass
class BaseEntity:
    """
    Minimal base for mutable grid state entities.
    """

    entity_id: EntityID = field(default_factory=new_entity_id)

    def __post_init__(self) -> None:
        assert self.entity_id is not None, "Entity must have a valid entity_id"
        validate_entity(self)

    def iter_components(self) -> Iterator[tuple[FieldName, Any]]:
        """Yield (store_name, component) for non-None ECS/effect components present on this object."""
        for name in FIELD_TO_COMPONENT.keys():
            if hasattr(self, name):
                value = getattr(self, name)
                if value is not None:
                    yield name, value

    def iter_nested_objects(self) -> Iterator[tuple[FieldName, list["BaseEntity"]]]:
        """Yield (store_name, list[BaseEntity]) for non-empty nested lists."""
        for name in NESTED_FIELDS:
            if hasattr(self, name):
                lst_any = getattr(self, name, [])
                if lst_any:
                    # Cast for type checker; runtime checks are done in validate_entity
                    lst = cast(list[BaseEntity], lst_any)
                    yield name, list(lst)

    def iter_reference_fields(self) -> Iterator[tuple[FieldName, Any]]:
        """Yield (store_name, ref) for non-None cross-entity references."""
        for name in REFERENCE_FIELD_TO_COMPONENT.keys():
            if hasattr(self, name):
                ref = getattr(self, name)
                if ref is not None:
                    yield name, ref

    def __repr__(self) -> str:
        parts: list[str] = []
        for k, v in self.iter_components():
            parts.append(f"{k}={v!r}")
        for k, v in self.iter_nested_objects():
            parts.append(f"{k}=[{', '.join(type(x).__name__ for x in v)}]")
        for k, v in self.iter_reference_fields():
            parts.append(f"{k}={v!r}")
        return f"{type(self).__name__}({', '.join(parts)})"


@dataclass(repr=False)
class Entity(BaseEntity):
    """
    Generic mutable entity with optional components, nested objects, and references.

    Games may subclass BaseEntity directly for tighter types, while this generic Entity
    remains a flexible builder-friendly shape.
    """

    # Components (optional)
    agent: Agent | None = None
    appearance: Appearance | None = None
    blocking: Blocking | None = None
    collectible: Collectible | None = None
    collidable: Collidable | None = None
    cost: Cost | None = None
    damage: Damage | None = None
    exit: Exit | None = None
    health: Health | None = None
    inventory: Inventory | None = None
    key: Key | None = None
    lethal_damage: LethalDamage | None = None
    locked: Locked | None = None
    moving: Moving | None = None
    pathfinding: Pathfinding | None = None
    portal: Portal | None = None
    pushable: Pushable | None = None
    requirable: Requirable | None = None
    rewardable: Rewardable | None = None
    status: Status | None = None

    # Effects (optional)
    immunity: Immunity | None = None
    phasing: Phasing | None = None
    speed: Speed | None = None
    time_limit: TimeLimit | None = None
    usage_limit: UsageLimit | None = None

    # Grid representation nested objects (not placed on the grid; materialized during conversion)
    inventory_list: list[BaseEntity] = field(default_factory=_empty_objs)
    status_list: list[BaseEntity] = field(default_factory=_empty_objs)

    # Grid representation reference fields (resolved during conversion)
    pathfind_target_ref: BaseEntity | None = None
    pathfinding_type: PathfindingType | None = None
    portal_pair_ref: BaseEntity | None = None


# ---- Validation helper ----


def validate_entity(obj: BaseEntity) -> None:
    """
    Validate component, nested-list, and reference field types.
    """
    # Components/effects
    for name, comp_type in FIELD_TO_COMPONENT.items():
        if hasattr(obj, name):
            val = getattr(obj, name)
            if val is not None and not isinstance(val, comp_type):
                raise TypeError(
                    f"Invalid type for '{name}': expected {comp_type.__name__}, got {type(val).__name__}"
                )

    # Nested lists: must be lists of BaseEntity
    for list_name in NESTED_FIELDS:
        if hasattr(obj, list_name):
            lst_any: Any = getattr(obj, list_name, [])
            if not isinstance(lst_any, list):
                raise TypeError(
                    f"Invalid type for '{list_name}': expected list, got {type(lst_any).__name__}"
                )
            for item in lst_any:
                if not isinstance(item, BaseEntity):
                    raise TypeError(
                        f"Invalid nested item in '{list_name}': expected BaseEntity, got {type(item).__name__}"
                    )

    # References: BaseEntity refs and PathfindingType enum
    if hasattr(obj, "pathfinding_type"):
        pft = getattr(obj, "pathfinding_type")
        if pft is not None and not isinstance(pft, PathfindingType):
            raise TypeError(
                f"Invalid type for 'pathfinding_type': expected PathfindingType, got {type(pft).__name__}"
            )
    for ref_name in ("pathfind_target_ref", "portal_pair_ref"):
        if hasattr(obj, ref_name):
            ref = getattr(obj, ref_name)
            if ref is not None and not isinstance(ref, BaseEntity):
                raise TypeError(
                    f"Invalid type for '{ref_name}': expected BaseEntity, got {type(ref).__name__}"
                )


# ---- Copy utility ----


def copy_entity_components(
    src: BaseEntity,
    dst: BaseEntity,
    include_nested: bool = True,
    include_refs: bool = True,
    preserve_entity_id: bool = False,
) -> BaseEntity:
    """
    Copy present fields from src to dst:

      - Components/effects: all keys in FIELD_TO_COMPONENT are copied when present on both src and dst.
      - Nested lists: fields in NESTED_FIELDS (shallow copies) when include_nested=True and present.
      - References: fields in REFERENCE_FIELD_TO_COMPONENT when include_refs=True and present.

    Args:
      src: Source entity.
      dst: Destination entity.
      include_nested: Whether to copy nested lists.
      include_refs: Whether to copy reference fields.
      preserve_entity_id: Whether to copy the entity_id from src to dst.

    Returns:
      dst (for chaining).
    """
    # Entity ID
    if preserve_entity_id:
        dst.entity_id = src.entity_id

    # Components/effects
    for name in FIELD_TO_COMPONENT.keys():
        if hasattr(src, name) and hasattr(dst, name):
            val = getattr(src, name)
            if val is not None:
                setattr(dst, name, val)

    # Nested lists
    if include_nested:
        for list_name in NESTED_FIELDS:
            if hasattr(src, list_name) and hasattr(dst, list_name):
                lst_any = getattr(src, list_name, [])
                if lst_any:
                    lst = cast(list[BaseEntity], lst_any)
                    setattr(dst, list_name, list(lst))

    # References
    if include_refs:
        for ref_name in REFERENCE_FIELD_TO_COMPONENT.keys():
            if hasattr(src, ref_name) and hasattr(dst, ref_name):
                setattr(dst, ref_name, getattr(src, ref_name, None))

    return dst
