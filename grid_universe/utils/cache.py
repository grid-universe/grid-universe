"""Lightweight LRU cache helpers for identity-keyed objects."""

from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar, ParamSpec
import weakref


P = ParamSpec("P")
R = TypeVar("R")


def lru_identity_cache(
    *,
    maxsize: int = 256,
    key_fn: Callable[..., Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """LRU cache decorator using an identity-based key by default.

    Args:
        maxsize: Maximum number of cached entries.
        key_fn: Optional function to produce cache key from args/kwargs.
            Defaults to ``id(args[0])`` (identity of first argument).
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        cache: OrderedDict[
            Any,
            tuple[weakref.ref[Any] | None, tuple[Any, ...], dict[str, Any], R],
        ] = OrderedDict()

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = key_fn(*args, **kwargs) if key_fn else id(args[0])
            entry = cache.get(key)
            if entry is not None:
                cached_ref, cached_args, cached_kwargs, value = entry
                if cached_ref is not None and cached_ref() is not args[0]:
                    cache.pop(key, None)
                elif cached_args == args and cached_kwargs == kwargs:
                    cache.move_to_end(key)
                    return value
                else:
                    cache.pop(key, None)

            value = fn(*args, **kwargs)
            ref: weakref.ref[Any] | None = None
            if args:
                try:
                    ref = weakref.ref(args[0])
                except TypeError:
                    ref = None
            cache[key] = (ref, args, kwargs, value)
            cache.move_to_end(key)
            if len(cache) > maxsize:
                cache.popitem(last=False)
            return value

        return wrapper

    return decorator
