#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test slurm_ops library."""

import base64
import subprocess
from unittest.mock import patch

from charms.hpc_libs.v0.slurm_ops import Service, SlurmManager
from pyfakefs.fake_filesystem_unittest import TestCase

MUNGEKEY = b"1234567890"
MUNGEKEY_BASE64 = base64.b64encode(MUNGEKEY)
SLURM_INFO = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
commands:
    - slurm.command1
    - slurm.command2
services:
    slurm.munged:                    simple, enabled, active
    slurm.slurmctld:                 simple, disabled, active
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
installed:          23.11.7             (x1) 114MB classic
"""


@patch("charms.hpc_libs.v0.slurm_ops.subprocess.check_output")
class SlurmOpsBase:
    """Test slurm_ops library."""

    def setUp(self) -> None:
        self.setUpPyfakefs()
        self.manager = SlurmManager(self.service)

    def test_config_name(self, *_) -> None:
        """Test that the config name is correctly set."""
        self.assertEqual(self.manager._service.config_name, self.config_name)

    def test_install(self, subcmd, *_) -> None:
        """Test that the manager calls the correct install command."""
        self.manager.install()
        args = subcmd.call_args[0][0]
        self.assertEqual(args[:3], ["snap", "install", "slurm"])
        self.assertIn("--classic", args[3:])  # codespell:ignore

    def test_enable(self, subcmd, *_) -> None:
        """Test that the manager calls the correct enable command."""
        self.manager.enable()
        calls = [args[0][0] for args in subcmd.call_args_list]

        self.assertEqual(calls[0], ["snap", "start", "--enable", "slurm.munged"])
        self.assertEqual(calls[1], ["snap", "start", "--enable", f"slurm.{self.service.value}"])

    def test_restart(self, subcmd, *_) -> None:
        """Test that the manager calls the correct restart command."""
        self.manager.restart()

        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "restart", f"slurm.{self.service.value}"])

    def test_restart_munged(self, subcmd, *_) -> None:
        """Test that the manager calls the correct enable command for munged."""
        self.manager.restart_munged()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "restart", "slurm.munged"])

    def test_disable(self, subcmd, *_) -> None:
        """Test that the manager calls the correct disable command."""
        self.manager.disable()
        calls = [args[0][0] for args in subcmd.call_args_list]

        self.assertEqual(calls[0], ["snap", "stop", "--disable", "slurm.munged"])
        self.assertEqual(calls[1], ["snap", "stop", "--disable", f"slurm.{self.service.value}"])

    def test_set_config(self, subcmd, *_) -> None:
        """Test that the manager calls the correct set_config command."""
        self.manager.set_config("key", "value")
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "set", "slurm", f"{self.config_name}.key=value"])

    def test_get_config(self, subcmd, *_) -> None:
        """Test that the manager calls the correct get_config command."""
        subcmd.return_value = b"value"
        value = self.manager.get_config("key")
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "get", "slurm", f"{self.config_name}.key"])
        self.assertEqual(value, "value")

    def test_generate_munge_key(self, subcmd, *_) -> None:
        """Test that the manager calls the correct mungekey command."""

        def mock_mungekey(*args, **kwargs):
            (_mk, _f, _k, path) = args[0]
            self.assertEqual(_mk, "mungekey")

            with open(path, "wb") as f:
                f.write(MUNGEKEY)

        subcmd.side_effect = mock_mungekey
        key = self.manager.generate_munge_key()
        self.assertEqual(key, MUNGEKEY)

    def test_set_munge_key(self, subcmd, *_) -> None:
        """Test that the manager sets the munge key with the correct command."""
        self.manager.set_munge_key(MUNGEKEY)
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "set", "slurm", f"munge.key={MUNGEKEY_BASE64.decode()}"])

    def test_get_munge_key(self, subcmd, *_) -> None:
        """Test that the manager gets the munge key with the correct command."""
        subcmd.return_value = MUNGEKEY_BASE64
        key = self.manager.get_munge_key()
        self.assertEqual(key, MUNGEKEY)

    def test_version(self, subcmd, *_) -> None:
        """Test that the manager gets the version key with the correct command."""
        subcmd.return_value = SLURM_INFO.encode()
        version = self.manager.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])
        self.assertEqual(version, "23.11.7")

    def test_call_error(self, subcmd, *_) -> None:
        """Test that the manager propagates errors when a command fails."""
        subcmd.side_effect = subprocess.CalledProcessError(-1, cmd=[""], stderr=b"error")
        with self.assertRaises(subprocess.CalledProcessError):
            self.manager.install()


parameters = [
    (Service.SLURMCTLD, "slurm"),
    (Service.SLURMD, "slurmd"),
    (Service.SLURMDBD, "slurmdbd"),
    (Service.SLURMRESTD, "slurmrestd"),
]

for service, config_name in parameters:
    cls_name = f"TestSlurmOps_{service.value}"
    globals()[cls_name] = type(
        cls_name,
        (SlurmOpsBase, TestCase),
        {
            "service": service,
            "config_name": config_name,
        },
    )
