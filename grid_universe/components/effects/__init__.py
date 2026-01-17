from .immunity import Immunity
from .phasing import Phasing
from .speed import Speed
from .time_limit import TimeLimit
from .usage_limit import UsageLimit

Effect = Immunity | Phasing | Speed

__all__ = [
    "Effect",
    "Immunity",
    "Phasing",
    "Speed",
    "TimeLimit",
    "UsageLimit",
]
