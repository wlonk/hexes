# -*- coding: utf-8 -*-
import pytest
from hexes import Application


def test_setup_and_teardown():
    with pytest.raises(RuntimeError):
        with Application():
            raise RuntimeError


def test_is_a_tty():
    import os
    import sys
    assert os.isatty(sys.stdout.fileno())
    assert os.isatty(sys.stderr.fileno())
    assert os.isatty(sys.stdin.fileno())
