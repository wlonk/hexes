from hexes.utils import (
    flatten,
    wrap_by_paragraph,
)


def test_flatten():
    nested_lists = [
        1,
        2,
        [
            3,
        ],
        [
            4,
            [
                5,
                6,
            ],
            7,
        ],
        8
    ]

    assert list(flatten(nested_lists)) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_wrap_by_paragraph():
    s = """
1234567890
1234567890

1234567890
1234567890
    """.strip()
    expected = """
1234567
890 123
4567890

1234567
890 123
4567890
    """.strip()
    actual = wrap_by_paragraph(s, width=7)
    assert actual == expected
