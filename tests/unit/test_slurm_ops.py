#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test slurm_ops library."""

import base64
import subprocess
import textwrap
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import charms.hpc_libs.v0.slurm_ops as slurm
import dotenv
from charms.hpc_libs.v0.slurm_ops import (
    SlurmctldManager,
    SlurmdbdManager,
    SlurmdManager,
    SlurmOpsError,
    _ServiceType,
    _SlurmManagerBase,
    _SnapManager,
)
from pyfakefs.fake_filesystem_unittest import TestCase as FsTestCase

MUNGEKEY = b"1234567890"
MUNGEKEY_BASE64 = base64.b64encode(MUNGEKEY)
JWT_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAt3PLWkwUOeckDwyMpHgGqmOZhitC8KfOQY/zPWfo+up5RQXz
gVWqsTIt1RWynxIwCGeKYfVlhoKNDEDL1ZjYPcrrGBgMEC8ifqxkN4RC8bwwaGrJ
9Zf0kknPHI5AJ9Fkv6EjgAZW1lwV0uEE5kf0wmlgfThXfzwwGVHVwemE1EgUzdI/
rVxFP5Oe+mRM7kWdtXQrfizGhfmr8laCs+dgExpPa37mk7u/3LZfNXXSWYiaNtie
vax5BxmI4bnTIXxdTT4VP9rMxG8nSspVj5NSWcplKUANlIkMKiO7k/CCD/YzRzM0
0yZttiTvECG+rKy+KJd97dbtj6wSvbJ7cjfq2wIDAQABAoIBACNTfPkqZUqxI9Ry
CjMxmbb97vZTJlTJO4KMgb51X/vRYwDToIxrPq9YhlLeFsNi8TTtG0y5wI8iXJ7b
a2T6RcnAZX0CRHBpYy8Za0L1iR6bqoaw6asNU99Hr0ZEbj48qDXuhbOFhPtKSDmP
cy4U9SDqwdXbH540rN5zT8JDgXyPAVJpwgsShk7rhgOFGIPIZqQoxEjPV3jr1sbk
k7c39fJR6Kxywppn7flSmNX3v1LDu4NDIp0Llt1NlcKlbdy5XWEW9IbiIYi3JTpB
kMpkFQFIuUyledeFyVFPsP8O7Da2rZS6Fb1dYNWzh3WkDRiAwYgTspiYiSf4AAi4
TgrOmiECgYEA312O5bXqXOapU+S2yAFRTa8wkZ1iRR2E66NypZKVsv/vfe0bO+WQ
kI6MRmTluvOKsKe3JulJZpjbl167gge45CHnFPZxEODAJN6OYp+Z4aOvTYBWQPpO
A75AGSheL66PWe4d+ZGvxYCZB5vf4THAs8BsGlFK04RKL1vHADkUjHUCgYEA0kFh
2ei/NP8ODrwygjrpjYSc2OSH9tBUoB7y5zIfLsXshb3Fn4pViF9vl01YkJJ57kki
KQm7rgqCsFnKS4oUFbjDDFbo351m1e3XRbPAATIiqtJmtLoLoSWuhXpsCbneM5bB
xLhFmm8RcFC6ORPBE2WMTGYzTEKydhImvUo+8A8CgYEAssWpyjaoRgSjP68Nj9Rm
Izv1LoZ9kX3H1eUyrEw/Hk3ze6EbK/xXkStWID0/FTs5JJyHXVBX3BK5plQ+1Rqj
I4vy7Hc2FWEcyCWMZmkA+3RLqUbvQgBUEnDh0oDZqWYX+802FnpA6V08nbdnH1D3
v6Zhn0qzDcmSqobVJluJE8UCgYB93FO1/QSQtel1WqUlnhx28Z5um4bkcVtnKn+f
dDqEZkiq2qn1UfrXksGbIdrVWEmTIcZIKKJnkbUf2fAl/fb99ccUmOX4DiIkB6co
+2wBi0CDX0XKA+C4S3VIQ7tuqwvfd+xwVRqdUsVupXSEfFXExbIRfdBRY0+vLDhy
cYJxcwKBgQCK+dW+F0UJTQq1rDxfI0rt6yuRnhtSdAq2+HbXNx/0nwdLQg7SubWe
1QnLcdjnBNxg0m3a7S15nyO2xehvB3rhGeWSfOrHYKJNX7IUqluVLJ+lIwgE2eAz
94qOCvkFCP3pnm/MKN6/rezyOzrVJn7GbyDhcjElu+DD+WRLjfxiSw==
-----END RSA PRIVATE KEY-----
"""
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


@patch(
    "charms.hpc_libs.v0.slurm_ops.subprocess.run",
    return_value=subprocess.CompletedProcess([], returncode=0),
)
class TestSlurmOps(TestCase):
    def test_error_message(self, *_) -> None:
        """Test that `SlurmOpsError` stores the correct message."""
        message = "error message!"
        self.assertEqual(SlurmOpsError(message).message, message)


@patch(
    "charms.hpc_libs.v0.slurm_ops.subprocess.run",
    return_value=subprocess.CompletedProcess([], returncode=0),
)
class TestSnapPackageManager(FsTestCase):
    def setUp(self):
        self.manager = _SnapManager()
        self.setUpPyfakefs()
        self.fs.create_file("/var/snap/slurm/common/.env")

    def test_install(self, subcmd) -> None:
        """Test that `slurm_ops` calls the correct install command."""
        self.manager.install()
        args = subcmd.call_args_list[0][0][0]
        self.assertEqual(args[:3], ["snap", "install", "slurm"])
        self.assertIn("--classic", args[3:])

    def test_version(self, subcmd) -> None:
        """Test that `slurm_ops` gets the correct version using the correct command."""
        subcmd.return_value = subprocess.CompletedProcess([], returncode=0, stdout=SLURM_INFO)
        version = self.manager.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])
        self.assertEqual(version, "23.11.7")

    def test_version_not_installed(self, subcmd) -> None:
        """Test that `slurm_ops` throws when getting the installed version if the slurm snap is not installed."""
        subcmd.return_value = subprocess.CompletedProcess(
            [], returncode=0, stdout=SLURM_INFO_NOT_INSTALLED
        )
        with self.assertRaises(slurm.SlurmOpsError):
            self.manager.version()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])

    def test_call_error(self, subcmd) -> None:
        """Test that `slurm_ops` propagates errors when a command fails."""
        subcmd.return_value = subprocess.CompletedProcess([], returncode=-1, stderr="error")
        with self.assertRaises(slurm.SlurmOpsError):
            self.manager.install()


@patch(
    "charms.hpc_libs.v0.slurm_ops.subprocess.run",
    return_value=subprocess.CompletedProcess([], returncode=0),
)
class SlurmOpsBase:
    """Test the Slurm service operations managers."""

    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_file("/var/snap/slurm/common/.env")
        self.fs.create_file("/var/snap/slurm/common/var/lib/slurm/slurm.state/jwt_hs256.key")
        self.manager.jwt._keyfile = Path(
            "/var/snap/slurm/common/var/lib/slurm/slurm.state/jwt_hs256.key"
        )
        self.manager.jwt._keyfile.write_text(JWT_KEY)

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
        subcmd.return_value = subprocess.CompletedProcess([], returncode=0, stdout=SLURM_INFO)
        self.assertTrue(self.manager.service.active())

    def test_active_not_installed(self, subcmd, *_) -> None:
        """Test that the manager throws an error when calling `active` if the snap is not installed."""
        subcmd.return_value = subprocess.CompletedProcess(
            [], returncode=0, stdout=SLURM_INFO_NOT_INSTALLED
        )
        with self.assertRaises(slurm.SlurmOpsError):
            self.manager.service.active()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["snap", "info", "slurm"])

    def test_generate_munge_key(self, subcmd, *_) -> None:
        """Test that the manager calls the correct `mungectl` command."""
        self.manager.munge.key.generate()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["mungectl", "key", "generate"])

    def test_set_munge_key(self, subcmd, *_) -> None:
        """Test that the manager sets the munge key with the correct command."""
        self.manager.munge.key.set(MUNGEKEY_BASE64)
        args = subcmd.call_args[0][0]
        # MUNGEKEY_BASE64 is piped to `stdin` to avoid exposure.
        self.assertEqual(args, ["mungectl", "key", "set"])

    def test_get_munge_key(self, subcmd, *_) -> None:
        """Test that the manager gets the munge key with the correct command."""
        subcmd.return_value = subprocess.CompletedProcess([], returncode=0, stdout=MUNGEKEY_BASE64)
        key = self.manager.munge.key.get()
        args = subcmd.call_args[0][0]
        self.assertEqual(args, ["mungectl", "key", "get"])
        self.assertEqual(key, MUNGEKEY_BASE64)

    def test_configure_munge(self, *_) -> None:
        """Test that manager is able to correctly configure munge."""
        self.manager.munge.max_thread_count = 24
        self.assertEqual(self.manager.munge.max_thread_count, 24)

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

    @patch("charms.hpc_libs.v0.slurm_ops.socket.gethostname")
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
        (SlurmOpsBase, FsTestCase),
        {
            "manager": manager,
            "config_name": config_name,
        },
    )


@patch("charms.hpc_libs.v0.slurm_ops.subprocess.run")
class TestSlurmctldConfig(FsTestCase):
    """Test the Slurmctld service config manager."""

    EXAMPLE_SLURM_CONF = textwrap.dedent(
        """
        #
        # `slurm.conf` file generated at 2024-01-30 17:18:36.171652 by slurmutils.
        #
        SlurmctldHost=juju-c9fc6f-0(10.152.28.20)
        SlurmctldHost=juju-c9fc6f-1(10.152.28.100)

        ClusterName=charmed-hpc
        AuthType=auth/munge
        Epilog=/usr/local/slurm/epilog
        Prolog=/usr/local/slurm/prolog
        FirstJobId=65536
        InactiveLimit=120
        JobCompType=jobcomp/filetxt
        JobCompLoc=/var/log/slurm/jobcomp
        KillWait=30
        MaxJobCount=10000
        MinJobAge=3600
        PluginDir=/usr/local/lib:/usr/local/slurm/lib
        ReturnToService=0
        SchedulerType=sched/backfill
        SlurmctldLogFile=/var/log/slurm/slurmctld.log
        SlurmdLogFile=/var/log/slurm/slurmd.log
        SlurmctldPort=7002
        SlurmdPort=7003
        SlurmdSpoolDir=/var/spool/slurmd.spool
        StateSaveLocation=/var/spool/slurm.state
        SwitchType=switch/none
        TmpFS=/tmp
        WaitTime=30

        #
        # Node configurations
        #
        NodeName=juju-c9fc6f-2 NodeAddr=10.152.28.48 CPUs=1 RealMemory=1000 TmpDisk=10000
        NodeName=juju-c9fc6f-3 NodeAddr=10.152.28.49 CPUs=1 RealMemory=1000 TmpDisk=10000
        NodeName=juju-c9fc6f-4 NodeAddr=10.152.28.50 CPUs=1 RealMemory=1000 TmpDisk=10000
        NodeName=juju-c9fc6f-5 NodeAddr=10.152.28.51 CPUs=1 RealMemory=1000 TmpDisk=10000

        #
        # Down node configurations
        #
        DownNodes=juju-c9fc6f-5 State=DOWN Reason="Maintenance Mode"

        #
        # Partition configurations
        #
        PartitionName=DEFAULT MaxTime=30 MaxNodes=10 State=UP
        PartitionName=batch Nodes=juju-c9fc6f-2,juju-c9fc6f-3,juju-c9fc6f-4,juju-c9fc6f-5 MinNodes=4 MaxTime=120 AllowGroups=admin
        """
    ).strip()

    def setUp(self):
        self.manager = SlurmctldManager(snap=True)
        self.config_name = "slurm"
        self.setUpPyfakefs()
        self.fs.create_file("/var/snap/slurm/common/.env")
        self.fs.create_file(
            "/var/snap/slurm/common/etc/slurm/slurm.conf", contents=self.EXAMPLE_SLURM_CONF
        )

    def test_config(self, *_) -> None:
        """Test that the manager can manipulate the configuration file."""
        with self.manager.config.edit() as config:
            self.assertEqual(config.slurmd_log_file, "/var/log/slurm/slurmd.log")
            self.assertEqual(config.nodes["juju-c9fc6f-2"]["NodeAddr"], "10.152.28.48")
            self.assertEqual(config.down_nodes[0]["State"], "DOWN")

            config.slurmctld_port = "8081"
            config.nodes["juju-c9fc6f-2"]["CPUs"] = "10"
            config.nodes["juju-c9fc6f-20"] = {"CPUs": 1}
            config.down_nodes.append(
                {"DownNodes": ["juju-c9fc6f-3"], "State": "DOWN", "Reason": "New nodes"}
            )
            del config.return_to_service

        # Exit the context to save changes to the file
        config = self.manager.config.load()
        self.assertEqual(config.slurmctld_port, "8081")
        self.assertNotEqual(config.return_to_service, "0")

        config_content = str(config).splitlines()
        self.assertIn(
            "NodeName=juju-c9fc6f-2 NodeAddr=10.152.28.48 CPUs=10 RealMemory=1000 TmpDisk=10000",
            config_content,
        )
        self.assertIn("NodeName=juju-c9fc6f-20 CPUs=1", config_content)
        self.assertIn('DownNodes=juju-c9fc6f-3 State=DOWN Reason="New nodes"', config_content)


@patch("charms.hpc_libs.v0.slurm_ops.subprocess.run")
class TestCgroupConfig(FsTestCase):
    """Test the Slurmctld service cgroup config manager."""

    EXAMPLE_CGROUP_CONF = textwrap.dedent(
        """
        #
        # `cgroup.conf` file generated at 2024-09-18 15:10:44.652017 by slurmutils.
        #
        ConstrainCores=yes
        ConstrainDevices=yes
        ConstrainRAMSpace=yes
        ConstrainSwapSpace=yes
        """
    ).strip()

    def setUp(self) -> None:
        self.manager = SlurmctldManager(snap=True)
        self.config_name = "slurmctld"
        self.setUpPyfakefs()
        self.fs.create_file("/var/snap/slurm/common/.env")
        self.fs.create_file(
            "/var/snap/slurm/common/etc/slurm/cgroup.conf", contents=self.EXAMPLE_CGROUP_CONF
        )

    def test_config(self, *_) -> None:
        """Test that manager can manipulate cgroup.conf configuration file."""
        with self.manager.cgroup.edit() as config:
            self.assertEqual(config.constrain_cores, "yes")
            self.assertEqual(config.constrain_devices, "yes")

            config.constrain_cores = "no"
            config.constrain_devices = "no"
            config.constrain_ram_space = "no"
            config.constrain_swap_space = "no"

        # Exit the context to save changes to the file
        config = self.manager.cgroup.load()
        self.assertEqual(config.constrain_cores, "no")
        self.assertEqual(config.constrain_devices, "no")
        self.assertEqual(config.constrain_ram_space, "no")
        self.assertEqual(config.constrain_swap_space, "no")


@patch("charms.hpc_libs.v0.slurm_ops.subprocess.run")
class TestSlurmdbdConfig(FsTestCase):
    """Test the Slurmdbd service config manager."""

    EXAMPLE_SLURMDBD_CONF = textwrap.dedent(
        """
        #
        # `slurmdbd.conf` file generated at 2024-01-30 17:18:36.171652 by slurmutils.
        #
        ArchiveEvents=yes
        ArchiveJobs=yes
        ArchiveResvs=yes
        ArchiveSteps=no
        ArchiveTXN=no
        ArchiveUsage=no
        ArchiveScript=/usr/sbin/slurm.dbd.archive
        AuthInfo=/var/run/munge/munge.socket.2
        AuthType=auth/munge
        AuthAltTypes=auth/jwt
        AuthAltParameters=jwt_key=16549684561684@
        DbdHost=slurmdbd-0
        DbdBackupHost=slurmdbd-1
        DebugLevel=info
        PluginDir=/all/these/cool/plugins
        PurgeEventAfter=1month
        PurgeJobAfter=12month
        PurgeResvAfter=1month
        PurgeStepAfter=1month
        PurgeSuspendAfter=1month
        PurgeTXNAfter=12month
        PurgeUsageAfter=24month
        LogFile=/var/log/slurmdbd.log
        PidFile=/var/run/slurmdbd.pid
        SlurmUser=slurm
        StoragePass=supersecretpasswd
        StorageType=accounting_storage/mysql
        StorageUser=slurm
        StorageHost=127.0.0.1
        StoragePort=3306
        StorageLoc=slurm_acct_db
        """
    ).strip()

    def setUp(self):
        self.manager = SlurmdbdManager(snap=True)
        self.config_name = "slurmdbd"
        self.setUpPyfakefs()
        self.fs.create_file("/var/snap/slurm/common/.env")
        self.fs.create_file(
            "/var/snap/slurm/common/etc/slurm/slurmdbd.conf", contents=self.EXAMPLE_SLURMDBD_CONF
        )

    def test_config(self, *_) -> None:
        """Test that the manager can manipulate the configuration file."""
        with self.manager.config.edit() as config:
            self.assertEqual(config.auth_type, "auth/munge")
            self.assertEqual(config.debug_level, "info")

            config.storage_pass = "newpass"
            config.log_file = "/var/snap/slurm/common/var/log/slurmdbd.log"
            del config.slurm_user

        # Exit the context to save changes to the file
        config = self.manager.config.load()
        self.assertEqual(config.storage_pass, "newpass")
        self.assertEqual(config.log_file, "/var/snap/slurm/common/var/log/slurmdbd.log")
        self.assertNotEqual(config.slurm_user, "slurm")


@patch("charms.hpc_libs.v0.slurm_ops.subprocess.run")
class TestSlurmdConfig(FsTestCase):
    """Test the Slurmd service config manager."""

    def setUp(self):
        self.manager = SlurmdManager(snap=True)
        self.setUpPyfakefs()
        self.fs.create_file("/var/snap/slurm/common/.env")

    def test_config(self, *_) -> None:
        """Test config operations for the slurmd manager."""
        self.manager.config_server = "localhost"
        self.assertEqual(self.manager.config_server, "localhost")
        self.assertEqual(
            dotenv.get_key("/var/snap/slurm/common/.env", "SLURMD_CONFIG_SERVER"), "localhost"
        )

        del self.manager.config_server
        self.assertIsNone(self.manager.config_server)
