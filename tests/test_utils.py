from hexes.utils import (
    flatten,
    modify,
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


def test_modify():
    original = "test"
    new = "test"
    val, modified = modify(original, new)
    assert val == "test"
    assert not modified

    original = "test"
    new = "gronk"
    val, modified = modify(original, new)
    assert val == "gronk"
    assert modified
