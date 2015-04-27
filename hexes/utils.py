from collections import (
    Iterable,
    namedtuple,
)
from textwrap import wrap

__all__ = (
    'Point',
    'flatten',
    'wrap_by_paragraph',
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


def wrap_by_paragraph(text, width=70, **kwargs):
    paragraphs = text.split('\n\n')
    return '\n\n'.join(
        '\n'.join(wrap(paragraph, width=width, **kwargs))
        for paragraph in paragraphs
    )
