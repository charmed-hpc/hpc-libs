#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Slurm service operations managers."""

import base64
import subprocess
from pathlib import Path
from unittest.mock import patch

from constants import (
    FAKE_GROUP_NAME,
    FAKE_USER_NAME,
    JWT_KEY,
    SLURM_KEY_BASE64,
    SNAP_SLURM_INFO,
    SNAP_SLURM_INFO_NOT_INSTALLED,
)
from pyfakefs.fake_filesystem_unittest import TestCase

from hpc_libs.slurm_ops import (
    SlurmOpsError,
    _ServiceType,
    _SlurmManagerBase,
)


@patch(
    "hpc_libs.slurm_ops.subprocess.run",
    return_value=subprocess.CompletedProcess([], returncode=0),
)
class SlurmOpsBase:
    """Test the Slurm service operations managers."""

    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_file("/var/snap/slurm/common/.env")
        self.fs.create_file("/var/snap/slurm/common/var/lib/slurm/slurm.state/jwt_hs256.key")
        self.fs.create_file("/var/snap/slurm/common/etc/slurm/slurm.key")

        # pyfakefs inconsistently mocks JWTKeyManager so fake instead.
        self.manager.jwt._keyfile = Path(
            "/var/snap/slurm/common/var/lib/slurm/slurm.state/jwt_hs256.key"
        )
        self.manager.jwt._user = FAKE_USER_NAME
        self.manager.jwt._group = FAKE_GROUP_NAME
        self.manager.jwt._keyfile.write_text(JWT_KEY)

        self.manager.key._keyfile = Path("/var/snap/slurm/common/etc/slurm/slurm.key")
        self.manager.key._user = FAKE_USER_NAME
        self.manager.key._group = FAKE_GROUP_NAME
        self.manager.key._keyfile.write_bytes(base64.b64decode(SLURM_KEY_BASE64.encode()))

    def test_config_name(self, *_) -> None:
        """Test that the config name is correctly set."""
        self.assertEqual(self.manager.service.type.config_name, self.config_name)

    def test_enable(self, subcmd, *_) -> None:
        """Test that the manager calls the correct enable command."""
        self.manager.service.enable()

        args = subcmd.call_args[0][0]
        self.assertEqual(
            args, ["snap", "start", "--enable", f"slurm.{self.manager.service.type.value}"]
        )

    def test_disable(self, subcmd, *_) -> None:
        """Test that the manager calls the correct disable command."""
        self.manager.service.disable()

        args = subcmd.call_args[0][0]
        self.assertEqual(
            args, ["snap", "stop", "--disable", f"slurm.{self.manager.service.type.value}"]
        )

    def test_restart(self, subcmd, *_) -> None:
        """Test that the manager calls the correct restart command."""
        self.manager.service.restart()

        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "restart", f"slurm.{self.manager.service.type.value}"])

    def test_active(self, subcmd) -> None:
        """Test that the manager can detect that a service is active."""
        subcmd.return_value = subprocess.CompletedProcess([], returncode=0, stdout=SNAP_SLURM_INFO)
        self.assertTrue(self.manager.service.active())

    def test_active_not_installed(self, subcmd, *_) -> None:
        """Test that the manager throws an error when calling `active` if the snap is not installed."""
        subcmd.return_value = subprocess.CompletedProcess(
            [], returncode=0, stdout=SNAP_SLURM_INFO_NOT_INSTALLED
        )
        with self.assertRaises(SlurmOpsError):
            self.manager.service.active()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])

    def test_slurm_key(self, *_) -> None:
        """Test that the manager correctly manages the slurm key."""
        key = self.manager.key.get()
        self.assertEqual(key, SLURM_KEY_BASE64)

        self.manager.key.generate()
        key = base64.b64encode(self.manager.key.path.read_bytes()).decode()
        self.assertEqual(self.manager.key.get(), key)

        self.manager.key.set(SLURM_KEY_BASE64)
        self.assertEqual(self.manager.key.get(), SLURM_KEY_BASE64)

    def test_get_jwt_key(self, *_) -> None:
        """Test that the jwt key is properly retrieved."""
        self.assertEqual(self.manager.jwt.get(), JWT_KEY)

    def test_set_jwt_key(self, *_) -> None:
        """Test that the jwt key is set correctly."""
        self.manager.jwt.set(JWT_KEY)
        self.assertEqual(self.manager.jwt.get(), JWT_KEY)

    def test_generate_jwt_key(self, *_) -> None:
        """Test that the jwt key is properly generated."""
        self.manager.jwt.generate()
        self.assertNotEqual(self.manager.jwt.get(), JWT_KEY)

    @patch("hpc_libs.slurm_ops.socket.gethostname")
    def test_hostname(self, gethostname, *_) -> None:
        """Test that manager is able to correctly get the host name."""
        gethostname.return_value = "machine"
        self.assertEqual(self.manager.hostname, "machine")
        gethostname.return_value = "machine.domain.com"
        self.assertEqual(self.manager.hostname, "machine")

    def test_scontrol(self, subcmd) -> None:
        """Test that manager correctly calls scontrol."""
        self.manager.scontrol("reconfigure")
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["scontrol", "reconfigure"])


parameters = [
    (_SlurmManagerBase(_ServiceType.SLURMCTLD, snap=True), "slurm"),
    (_SlurmManagerBase(_ServiceType.SLURMD, snap=True), "slurmd"),
    (_SlurmManagerBase(_ServiceType.SLURMDBD, snap=True), "slurmdbd"),
    (_SlurmManagerBase(_ServiceType.SLURMRESTD, snap=True), "slurmrestd"),
]

for manager, config_name in parameters:
    cls_name = f"Test{manager.service.type.value.capitalize()}Ops"
    globals()[cls_name] = type(
        cls_name,
        (SlurmOpsBase, TestCase),
        {
            "manager": manager,
            "config_name": config_name,
        },
    )
