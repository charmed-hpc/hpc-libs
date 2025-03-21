#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE for licensing details.

"""Unit tests for `snap` operations manager."""

import subprocess
from unittest.mock import patch

from hpc_libs.slurm_ops import SlurmOpsError, _SnapManager
from constants import SNAP_SLURM_INFO, SNAP_SLURM_INFO_NOT_INSTALLED
from pyfakefs.fake_filesystem_unittest import TestCase


@patch(
    "hpc_libs.slurm_ops.subprocess.run",
    return_value=subprocess.CompletedProcess([], returncode=0),
)
class TestSnapPackageManager(TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.manager = _SnapManager()
        self.fs.create_file("/var/snap/slurm/common/.env")

    def test_install(self, subcmd) -> None:
        """Test that `slurm_ops` calls the correct install command."""
        self.manager.install()
        args = subcmd.call_args_list[0][0][0]
        self.assertEqual(args[:3], ["snap", "install", "slurm"])
        self.assertIn("--classic", args[3:])

    def test_version(self, subcmd) -> None:
        """Test that `slurm_ops` gets the correct version using the correct command."""
        subcmd.return_value = subprocess.CompletedProcess([], returncode=0, stdout=SNAP_SLURM_INFO)
        version = self.manager.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])
        self.assertEqual(version, "23.11.7")

    def test_version_not_installed(self, subcmd) -> None:
        """Test that `slurm_ops` throws when getting the installed version if the slurm snap is not installed."""
        subcmd.return_value = subprocess.CompletedProcess(
            [], returncode=0, stdout=SNAP_SLURM_INFO_NOT_INSTALLED
        )
        with self.assertRaises(SlurmOpsError):
            self.manager.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])

    def test_call_error(self, subcmd) -> None:
        """Test that `slurm_ops` propagates errors when a command fails."""
        subcmd.return_value = subprocess.CompletedProcess([], returncode=-1, stderr="error")
        with self.assertRaises(SlurmOpsError):
            self.manager.install()
