#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from hpc_libs.is_container import is_container


def test_is_container() -> None:
    """Test that `is_container` properly detects the system container."""
    assert is_container() is True
