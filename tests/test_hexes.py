# -*- coding: utf-8 -*-
import pytest
from hexes import Application


@pytest.mark.xfail(reason="Curses again.", run=False)
def test_setup_and_teardown():
    with pytest.raises(RuntimeError):
        with Application():
            raise RuntimeError


def test_placeholder():
    assert True
