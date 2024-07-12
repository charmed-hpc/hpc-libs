#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test slurm_ops library."""

import base64
import subprocess
from unittest import TestCase
from unittest.mock import patch

import charms.hpc_libs.v0.slurm_ops as slurm
from charms.hpc_libs.v0.slurm_ops import ServiceType, SlurmManagerBase, SlurmOpsError

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
    slurm.logrotate:                 oneshot, enabled, inactive
    slurm.munged:                    simple, enabled, active
    slurm.slurm-prometheus-exporter: simple, disabled, inactive
    slurm.slurmctld:                 simple, disabled, active
    slurm.slurmd:                    simple, enabled, active
    slurm.slurmdbd:                  simple, disabled, active
    slurm.slurmrestd:                simple, disabled, active
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
installed:          23.11.7             (x1) 114MB classic
"""
SLURM_INFO_NOT_INSTALLED = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
"""


@patch("charms.hpc_libs.v0.slurm_ops.subprocess.check_output")
class TestSlurmOps(TestCase):

    def test_format_key(self, _) -> None:
        """Test that `kebabize` properly formats slurm keys."""
        self.assertEqual(slurm.format_key("CPUs"), "cpus")
        self.assertEqual(slurm.format_key("AccountingStorageHost"), "accounting-storage-host")

    def test_install(self, subcmd) -> None:
        """Test that `slurm_ops` calls the correct install command."""
        slurm.install()
        args = subcmd.call_args[0][0]
        self.assertEqual(args[:3], ["snap", "install", "slurm"])
        self.assertIn("--classic", args[3:])  # codespell:ignore

    def test_version(self, subcmd) -> None:
        """Test that `slurm_ops` gets the correct version using the correct command."""
        subcmd.return_value = SLURM_INFO.encode()
        version = slurm.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])
        self.assertEqual(version, "23.11.7")

    def test_version_not_installed(self, subcmd) -> None:
        """Test that `slurm_ops` throws when getting the installed version if the slurm snap is not installed."""
        subcmd.return_value = SLURM_INFO_NOT_INSTALLED.encode()
        with self.assertRaises(slurm.SlurmOpsError):
            slurm.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])

    def test_call_error(self, subcmd) -> None:
        """Test that `slurm_ops` propagates errors when a command fails."""
        subcmd.side_effect = subprocess.CalledProcessError(-1, cmd=[""], stderr=b"error")
        with self.assertRaises(slurm.SlurmOpsError):
            slurm.install()

    def test_error_message(self, *_) -> None:
        """Test that `SlurmOpsError` stores the correct message."""
        message = "error message!"
        self.assertEqual(SlurmOpsError(message).message, message)


@patch("charms.hpc_libs.v0.slurm_ops.subprocess.check_output")
class SlurmOpsBase:
    """Test the Slurm service operations managers."""

    def test_config_name(self, *_) -> None:
        """Test that the config name is correctly set."""
        self.assertEqual(self.manager._service.config_name, self.config_name)

    def test_enable(self, subcmd, *_) -> None:
        """Test that the manager calls the correct enable command."""
        self.manager.enable()

        args = subcmd.call_args[0][0]
        self.assertEqual(
            args, ["snap", "start", "--enable", f"slurm.{self.manager._service.value}"]
        )

    def test_disable(self, subcmd, *_) -> None:
        """Test that the manager calls the correct disable command."""
        self.manager.disable()

        args = subcmd.call_args[0][0]
        self.assertEqual(
            args, ["snap", "stop", "--disable", f"slurm.{self.manager._service.value}"]
        )

    def test_restart(self, subcmd, *_) -> None:
        """Test that the manager calls the correct restart command."""
        self.manager.restart()

        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "restart", f"slurm.{self.manager._service.value}"])

    def test_active(self, subcmd, *_) -> None:
        """Test that the manager can detect that a service is active."""
        subcmd.return_value = SLURM_INFO.encode()
        self.assertTrue(self.manager.active())

    def test_active_not_installed(self, subcmd, *_) -> None:
        """Test that the manager throws an error when calling `active` if the snap is not installed."""
        subcmd.return_value = SLURM_INFO_NOT_INSTALLED.encode()
        with self.assertRaises(slurm.SlurmOpsError):
            self.manager.active()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])

    def test_get_options(self, subcmd) -> None:
        """Test that the manager correctly collects all requested configuration options."""
        subcmd.return_value = '{"%(name)s.key1": "value1", "%(name)s.key2": "value2"}' % {
            "name": self.config_name
        }
        value = self.manager.config.get_options("key1", "key2")
        calls = [args[0][0] for args in subcmd.call_args_list]
        self.assertEqual(calls[0], ["snap", "get", "-d", "slurm", f"{self.config_name}.key1"])
        self.assertEqual(calls[1], ["snap", "get", "-d", "slurm", f"{self.config_name}.key2"])
        self.assertEqual(value, {"key1": "value1", "key2": "value2"})

    def test_get_config(self, subcmd, *_) -> None:
        """Test that the manager calls the correct `snap get ...` command."""
        subcmd.return_value = '{"%s.key": "value"}' % self.config_name
        value = self.manager.config.get("key")
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "get", "-d", "slurm", f"{self.config_name}.key"])
        self.assertEqual(value, "value")

    def test_get_config_all(self, subcmd) -> None:
        """Test that manager calls the correct `snap get ...` with no arguments given."""
        subcmd.return_value = '{"%s": "value"}' % self.config_name
        value = self.manager.config.get()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "get", "-d", "slurm", self.config_name])
        self.assertEqual(value, "value")

    def test_set_config(self, subcmd, *_) -> None:
        """Test that the manager calls the correct `snap set ...` command."""
        self.manager.config.set({"key": "value"})
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "set", "slurm", f'{self.config_name}.key="value"'])

    def test_unset_config(self, subcmd) -> None:
        """Test that the manager calls the correct `snap unset ...` command."""
        self.manager.config.unset("key")
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "unset", "slurm", f"{self.config_name}.key"])

    def test_unset_config_all(self, subcmd) -> None:
        """Test the manager calls the correct `snap unset ...` with no arguments given."""
        self.manager.config.unset()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "unset", "slurm", self.config_name])

    def test_generate_munge_key(self, subcmd, *_) -> None:
        """Test that the manager calls the correct `mungectl` command."""
        self.manager.munge.generate_key()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["slurm.mungectl", "key", "generate"])

    def test_set_munge_key(self, subcmd, *_) -> None:
        """Test that the manager sets the munge key with the correct command."""
        self.manager.munge.set_key(MUNGEKEY_BASE64)
        args = subcmd.call_args[0][0]
        # MUNGEKEY_BASE64 is piped to `stdin` to avoid exposure.
        self.assertEqual(args, ["slurm.mungectl", "key", "set"])

    def test_get_munge_key(self, subcmd, *_) -> None:
        """Test that the manager gets the munge key with the correct command."""
        subcmd.return_value = MUNGEKEY_BASE64
        key = self.manager.munge.get_key()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["slurm.mungectl", "key", "get"])
        self.assertEqual(key, MUNGEKEY_BASE64)

    def test_configure_munge(self, subcmd) -> None:
        """Test that manager is able to correctly configure munge."""
        self.manager.munge.config.set({"max-thread-count": 24})
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "set", "slurm", "munge.max-thread-count=24"])

    @patch("charms.hpc_libs.v0.slurm_ops.socket.gethostname")
    def test_hostname(self, gethostname, *_) -> None:
        """Test that manager is able to correctly get the host name."""
        gethostname.return_value = "machine"
        self.assertEqual(self.manager.hostname, "machine")
        gethostname.return_value = "machine.domain.com"
        self.assertEqual(self.manager.hostname, "machine")


parameters = [
    (SlurmManagerBase(ServiceType.SLURMCTLD), "slurm"),
    (SlurmManagerBase(ServiceType.SLURMD), "slurmd"),
    (SlurmManagerBase(ServiceType.SLURMDBD), "slurmdbd"),
    (SlurmManagerBase(ServiceType.SLURMRESTD), "slurmrestd"),
]

for manager, config_name in parameters:
    cls_name = f"Test{manager._service.value.capitalize()}Ops"
    globals()[cls_name] = type(
        cls_name,
        (SlurmOpsBase, TestCase),
        {
            "manager": manager,
            "config_name": config_name,
        },
    )
