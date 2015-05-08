# -*- coding: utf-8 -*-
import pytest
from hexes import (
    Box,
    Style,
)


@pytest.fixture
def tree():
    box = Box(
        title="Root",
        children=(
            Box(
                title="A",
                children=(
                    Box(
                        title="AA",
                    ),
                    Box(
                        title="AB",
                    ),
                ),
            ),
            Box(
                title="B",
            ),
        ),
    )
    box.available_height = 100
    box.available_width = 100
    return box


def test_traverse_pre_order(tree):
    actual = [box.title for box in tree.traverse_pre_order]
    expected = ["Root", "A", "AA", "AB", "B"]
    assert actual == expected


def test_root(tree):
    node = tree.children[0].children[1]  # "AB"
    assert node.root == tree


def test_available_height(tree):
    # 49 is the 100 of the root, minus 2 of borders, divide by 2 for the number
    # of children.
    assert tree.children[0].available_height == 49
    assert tree.children[1].available_height == 49
    # 23 is the 49 of the parent, minus 2 of borders, divide by 2 (round down)
    # for the number of children
    assert tree.children[0].children[0].available_height == 23
    assert tree.children[0].children[1].available_height == 23


def test_available_width(tree):
    # 98 is full width minus 2 for borders.
    assert tree.children[0].available_width == 98
    assert tree.children[1].available_width == 98
    # 96 is full width minus 2 for parent's borders and 2 for grandparent's
    # borders
    assert tree.children[0].children[0].available_width == 96
    assert tree.children[0].children[1].available_width == 96


def test_available_width_with_horizontal_layout(tree):
    tree.children[0].style.layout = Style.Layout.Horizontal

    # 98 is full width minus 2 for borders.
    assert tree.children[0].available_width == 98
    assert tree.children[1].available_width == 98
    # 96 (parent inner width) / 2 for siblings - 2 for borders
    assert tree.children[0].children[0].available_width == 48
    assert tree.children[0].children[1].available_width == 48


def test_ancestors(tree):
    expected = [tree.children[0], tree]
    assert tree.children[0].children[0].ancestors == expected


def test_older_siblings(tree):
    assert tree.children[0].older_siblings == []
    assert tree.children[1].older_siblings == [tree.children[0]]


def test_younger_siblings(tree):
    assert tree.children[0].younger_siblings == [tree.children[1]]
    assert tree.children[1].younger_siblings == []


def test_upper_left(tree):
    assert tree.upper_left == (0, 0)
    assert tree.children[0].upper_left == (1, 1)
    assert tree.children[1].upper_left == (1, 50)

    assert tree.children[0].children[0].upper_left == (2, 2)
    assert tree.children[0].children[1].upper_left == (2, 25)


def test_upper_left_with_horizontal_layout(tree):
    tree.children[0].style.layout = Style.Layout.Horizontal

    assert tree.upper_left == (0, 0)
    assert tree.children[0].upper_left == (1, 1)
    assert tree.children[1].upper_left == (1, 50)

    assert tree.children[0].children[0].upper_left == (2, 2)
    assert tree.children[0].children[1].upper_left == (50, 2)


def test_lower_right(tree):
    assert tree.lower_right == (100, 100)


def test_add_child(tree):
    box = Box()
    tree.add_child(box)
    assert box.parent == tree


def test_add_children(tree):
    box1 = Box()
    box2 = Box()
    tree.add_children(box1, box2)
    assert box1.parent == tree
    assert box2.parent == tree
