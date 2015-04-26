from hexes.utils import flatten


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
