#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test `is_container` library."""

from unittest import TestCase
from unittest.mock import patch

from charms.hpc_libs.v0.is_container import UnknownVirtStateError, is_container


@patch("charms.hpc_libs.v0.is_container.shutil.which", return_value="/usr/bin/systemd-detect-virt")
@patch("charms.hpc_libs.v0.is_container.subprocess.run")
class TestIsContainer(TestCase):

    def test_inside_container(self, run, _) -> None:
        """Test that `is_container` returns True when inside a container."""
        run.return_value.returncode = 0
        self.assertTrue(is_container())

    def test_inside_virtual_machine(self, run, _) -> None:
        """Test that `is_container` returns False when inside a virtual machine."""
        run.return_value.returncode = 1
        self.assertFalse(is_container())

    def test_detect_virt_not_found(self, _, which) -> None:
        """Test that correct error is thrown if `systemd-detect-virt` is not found."""
        which.return_value = None

        try:
            is_container()
        except UnknownVirtStateError as e:
            self.assertEqual(
                e.message,
                (
                    "executable `systemd-detect-virt` not found. "
                    + "cannot determine if machine is a container instance"
                ),
            )
