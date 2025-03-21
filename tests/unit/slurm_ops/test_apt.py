#!/usr/bin/env python3
# Copyright 2024-2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for `apt` operations manager."""

import stat
import subprocess
from pathlib import Path
from unittest.mock import patch

import hpc_libs._apt as apt
from hpc_libs.slurm_ops import (
    SackdManager,
    SlurmctldManager,
    SlurmdbdManager,
    SlurmdManager,
    SlurmOpsError,
    SlurmrestdManager,
)
from constants import APT_SLURM_INFO, ULIMIT_CONFIG
from pyfakefs.fake_filesystem_unittest import TestCase


@patch(
    "hpc_libs.slurm_ops.subprocess.run",
    return_value=subprocess.CompletedProcess([], returncode=0),
)
class TestAptPackageManager(TestCase):
    """Test the `_AptManager` Slurm operations manager."""

    def setUp(self) -> None:
        self.setUpPyfakefs()
        self.sackd = SackdManager(snap=False)
        self.slurmctld = SlurmctldManager(snap=False)
        self.slurmd = SlurmdManager(snap=False)
        self.slurmdbd = SlurmdbdManager(snap=False)
        self.slurmrestd = SlurmrestdManager(snap=False)

        self.fs.create_dir("/etc/default")
        self.fs.create_dir("/etc/security/limits.d")
        self.fs.create_dir("/etc/systemd/service/slurmctld.service.d")
        self.fs.create_dir("/etc/systemd/service/slurmd.service.d")
        self.fs.create_dir("/usr/lib/systemd/system")
        self.fs.create_dir("/var/lib/slurm")

    def test_version(self, subcmd) -> None:
        """Test that `version` gets the correct package version number."""
        subcmd.side_effect = [
            subprocess.CompletedProcess([], returncode=0, stdout="amd64"),
            subprocess.CompletedProcess([], returncode=0, stdout=APT_SLURM_INFO),
        ]
        version = self.slurmctld.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(version, "23.11.7-2ubuntu1")
        self.assertListEqual(args, ["dpkg", "-l", "slurmctld"])

    def test_version_not_installed(self, subcmd) -> None:
        """Test that `version` throws an error if Slurm service is not installed."""
        subcmd.side_effect = [
            subprocess.CompletedProcess([], returncode=0, stdout="amd64"),
            subprocess.CompletedProcess([], returncode=1),
        ]
        with self.assertRaises(SlurmOpsError):
            self.slurmctld.version()

    @patch("hpc_libs._apt.DebianRepository._get_keyid_by_gpg_key")
    @patch("hpc_libs._apt.DebianRepository._dearmor_gpg_key")
    @patch("hpc_libs._apt.DebianRepository._write_apt_gpg_keyfile")
    @patch("hpc_libs._apt.RepositoryMapping.add")
    @patch("distro.codename")
    def test_init_ubuntu_hpc_ppa(self, *_) -> None:
        """Test that Ubuntu HPC repositories are initialized correctly."""
        self.slurmctld._ops_manager._init_ubuntu_hpc_ppa()

    @patch("hpc_libs._apt.DebianRepository._get_keyid_by_gpg_key")
    @patch("hpc_libs._apt.DebianRepository._dearmor_gpg_key")
    @patch("hpc_libs._apt.DebianRepository._write_apt_gpg_keyfile")
    @patch("hpc_libs._apt.RepositoryMapping.add")
    @patch("distro.codename")
    @patch(
        "hpc_libs._apt.update",
        side_effect=subprocess.CalledProcessError(1, ["apt-get", "update", "--error-any"]),
    )
    def test_init_ubuntu_hpc_ppa_fail(self, *_) -> None:
        """Test that error is correctly bubbled up if `apt update` fails."""
        with self.assertRaises(SlurmOpsError):
            self.slurmctld._ops_manager._init_ubuntu_hpc_ppa()

    def test_set_ulimit(self, *_) -> None:
        """Test that the correct slurmctld and slurmd ulimit rules are applied."""
        self.slurmctld._ops_manager._set_ulimit()

        target = Path("/etc/security/limits.d/20-charmed-hpc-openfile.conf")
        self.assertEqual(ULIMIT_CONFIG, target.read_text())
        f_info = target.stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "-rw-r--r--")

    @patch("hpc_libs._apt.add_package")
    def test_install_service(self, add_package, *_) -> None:
        """Test that `_install_service` installs the correct packages for each service."""
        self.sackd._ops_manager._install_service()
        self.assertListEqual(
            add_package.call_args[0][0],
            [
                "sackd",
                "munge",
                "mungectl",
                "slurm-client",
            ],
        )

        self.slurmctld._ops_manager._install_service()
        self.assertListEqual(
            add_package.call_args[0][0],
            [
                "slurmctld",
                "munge",
                "mungectl",
                "libpmix-dev",
                "mailutils",
                "prometheus-slurm-exporter",
            ],
        )

        self.slurmd._ops_manager._install_service()
        self.assertListEqual(
            add_package.call_args[0][0],
            [
                "slurmd",
                "munge",
                "mungectl",
                "slurm-client",
                "libpmix-dev",
                "openmpi-bin",
            ],
        )

        self.slurmdbd._ops_manager._install_service()
        self.assertListEqual(
            add_package.call_args[0][0],
            ["slurmdbd", "munge", "mungectl"],
        )

        self.slurmrestd._ops_manager._install_service()
        self.assertListEqual(
            add_package.call_args[0][0],
            [
                "slurmrestd",
                "munge",
                "mungectl",
                "slurm-wlm-basic-plugins",
            ],
        )

        add_package.side_effect = apt.PackageError("failed to install packages!")
        with self.assertRaises(SlurmOpsError):
            self.slurmctld._ops_manager._install_service()

    def test_apply_overrides(self, subcmd) -> None:
        """Test that the correct overrides are applied based on the Slurm service installed."""
        # Test overrides for slurmrestd first since it's easier to work with `call_args_list`
        self.slurmrestd._ops_manager._apply_overrides()
        groupadd = subcmd.call_args_list[0][0][0]
        adduser = subcmd.call_args_list[1][0][0]
        systemctl = subcmd.call_args_list[2][0][0]
        self.assertListEqual(groupadd, ["groupadd", "--gid", "64031", "slurmrestd"])
        self.assertListEqual(
            adduser,
            [
                "adduser",
                "--system",
                "--group",
                "--uid",
                "64031",
                "--no-create-home",
                "--home",
                "/nonexistent",
                "slurmrestd",
            ],
        )
        self.assertListEqual(systemctl, ["systemctl", "daemon-reload"])

        self.slurmctld._ops_manager._apply_overrides()
        args = subcmd.call_args[0][0]
        self.assertListEqual(args, ["systemctl", "daemon-reload"])

        self.slurmd._ops_manager._apply_overrides()
        self.assertListEqual(args, ["systemctl", "daemon-reload"])

        self.slurmdbd._ops_manager._apply_overrides()
        self.assertListEqual(args, ["systemctl", "daemon-reload"])

    @patch("hpc_libs.slurm_ops._AptManager._init_ubuntu_hpc_ppa")
    @patch("hpc_libs.slurm_ops._AptManager._install_service")
    @patch("hpc_libs.slurm_ops._AptManager._apply_overrides")
    @patch("shutil.chown")
    def test_install(self, *_) -> None:
        """Test public `install` method that encapsulates service install logic."""
        self.slurmctld.install()
        f_info = Path("/var/lib/slurm").stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "drwxr-xr-x")
        f_info = Path("/var/lib/slurm/checkpoint").stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "drwxr-xr-x")
