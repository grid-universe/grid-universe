from dataclasses import dataclass


@dataclass(frozen=True)
class Requirable:
    """
    Marker component for requirable entities.
    """

    pass
