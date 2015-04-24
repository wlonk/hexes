from collections import (
    Iterable,
    namedtuple,
)

__all__ = (
    'Point',
    'flatten',
)

Point = namedtuple('Point', 'x y')

stringlike = (str, bytes)


def flatten(container):
    for i in container:
        if isinstance(i, Iterable) and not isinstance(i, stringlike):
            for j in flatten(i):
                yield j
        else:
            yield i
