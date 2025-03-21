#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Slurm configuration managers and descriptors."""

import stat
from pathlib import Path

import dotenv
from constants import (
    EXAMPLE_ACCT_GATHER_CONFIG,
    EXAMPLE_CGROUP_CONFIG,
    EXAMPLE_GRES_CONFIG,
    EXAMPLE_SLURM_CONFIG,
    EXAMPLE_SLURMDBD_CONFIG,
    FAKE_GROUP_GID,
    FAKE_GROUP_NAME,
    FAKE_USER_NAME,
    FAKE_USER_UID,
)
from pyfakefs.fake_filesystem_unittest import TestCase

from hpc_libs.slurm_ops import (
    SackdManager,
    SlurmctldManager,
    SlurmdbdManager,
    SlurmdManager,
)


class TestConfigManagement(TestCase):
    """Test configuration managers provided by the Slurm service managers."""

    @classmethod
    def setUpClass(cls):
        cls.setUpClassPyfakefs()

        cls.sackd = SackdManager(snap=False)
        cls.slurmctld = SlurmctldManager(snap=False)
        cls.slurmd = SlurmdManager(snap=False)
        cls.slurmdbd = SlurmdbdManager(snap=False)

    def test_sackd_manager_config_server(self) -> None:
        """Test `SackdManager` `config_server` descriptors."""
        self.fs.create_file("/etc/default/sackd")

        self.sackd.config_server = "localhost"
        self.assertEqual(self.sackd.config_server, "localhost")
        self.assertEqual(dotenv.get_key("/etc/default/sackd", "SACKD_CONFIG_SERVER"), "localhost")
        del self.sackd.config_server
        self.assertIsNone(self.sackd.config_server)

    def test_slurmctld_manager_acct_gather_config(self) -> None:
        """Test `SlurmctldManager` acct_gather.conf configuration file editor."""
        self.fs.create_file("/etc/slurm/acct_gather.conf", contents=EXAMPLE_ACCT_GATHER_CONFIG)

        # Fake user and group that owns the `acct_gather.conf` file.
        self.slurmctld.acct_gather._user = FAKE_USER_NAME
        self.slurmctld.acct_gather._group = FAKE_GROUP_NAME

        with self.slurmctld.acct_gather.edit() as config:
            self.assertEqual(config.energy_ipmi_frequency, "1")
            self.assertEqual(config.energy_ipmi_calc_adjustment, "yes")
            self.assertListEqual(config.sysfs_interfaces, ["enp0s1"])

            config.energy_ipmi_frequency = "2"
            config.energy_ipmi_calc_adjustment = "no"
            config.sysfs_interfaces = ["enp0s2"]

        # Exit the context to save changes to the acct_gather.conf file.
        config = self.slurmctld.acct_gather.load()
        self.assertEqual(config.energy_ipmi_frequency, "2")
        self.assertEqual(config.energy_ipmi_calc_adjustment, "no")
        self.assertListEqual(config.sysfs_interfaces, ["enp0s2"])

        # Ensure that permissions on the acct_gather.conf are correct.
        f_info = Path("/etc/slurm/acct_gather.conf").stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "-rw-------")
        self.assertEqual(f_info.st_uid, FAKE_USER_UID)
        self.assertEqual(f_info.st_gid, FAKE_GROUP_GID)

    def test_slurmctld_manager_cgroup_config(self) -> None:
        """Test `SlurmctldManager` cgroup.conf configuration file editor."""
        self.fs.create_file("/etc/slurm/cgroup.conf", contents=EXAMPLE_CGROUP_CONFIG)

        # Fake user and group that owns the cgroup.conf file.
        self.slurmctld.cgroup._user = FAKE_USER_NAME
        self.slurmctld.cgroup._group = FAKE_GROUP_NAME

        with self.slurmctld.cgroup.edit() as config:
            self.assertEqual(config.constrain_cores, "yes")
            self.assertEqual(config.constrain_devices, "yes")

            config.constrain_cores = "no"
            config.constrain_devices = "no"
            config.constrain_ram_space = "no"
            config.constrain_swap_space = "no"

        # Exit the context to save changes to the cgroup.conf file.
        config = self.slurmctld.cgroup.load()
        self.assertEqual(config.constrain_cores, "no")
        self.assertEqual(config.constrain_devices, "no")
        self.assertEqual(config.constrain_ram_space, "no")
        self.assertEqual(config.constrain_swap_space, "no")

        # Ensure that permissions on the cgroup.conf file are correct.
        f_info = Path("/etc/slurm/cgroup.conf").stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "-rw-r--r--")
        self.assertEqual(f_info.st_uid, FAKE_USER_UID)
        self.assertEqual(f_info.st_gid, FAKE_GROUP_GID)

    def test_slurmctld_manager_gres_config(self) -> None:
        """Test `SlurmctldManager` gres.conf configuration file editor."""
        self.fs.create_file("/etc/slurm/gres.conf", contents=EXAMPLE_GRES_CONFIG)

        # Fake use and group that owns the gres.conf file
        self.slurmctld.gres._user = FAKE_USER_NAME
        self.slurmctld.gres._group = FAKE_GROUP_NAME

        with self.slurmctld.gres.edit() as config:
            self.assertEqual(config.auto_detect, "nvml")
            self.assertDictEqual(
                config.names.dict(),
                {
                    "gpu": [
                        {
                            "Name": "gpu",
                            "Type": "gp100",
                            "File": "/dev/nvidia0",
                            "Cores": ["0", "1"],
                        },
                        {
                            "Name": "gpu",
                            "Type": "gp100",
                            "File": "/dev/nvidia1",
                            "Cores": ["0", "1"],
                        },
                        {
                            "Name": "gpu",
                            "Type": "p6000",
                            "File": "/dev/nvidia2",
                            "Cores": ["2", "3"],
                        },
                        {
                            "Name": "gpu",
                            "Type": "p6000",
                            "File": "/dev/nvidia3",
                            "Cores": ["2", "3"],
                        },
                    ],
                    "mps": [
                        {"Name": "mps", "Count": "200", "File": "/dev/nvidia0"},
                        {"Name": "mps", "Count": "200", "File": "/dev/nvidia1"},
                        {"Name": "mps", "Count": "100", "File": "/dev/nvidia2"},
                        {"Name": "mps", "Count": "100", "File": "/dev/nvidia3"},
                    ],
                    "bandwidth": [
                        {
                            "Name": "bandwidth",
                            "Type": "lustre",
                            "Count": "4G",
                            "Flags": ["CountOnly"],
                        },
                    ],
                },
            )
            self.assertDictEqual(
                config.nodes.dict(),
                {
                    "juju-c9c6f-[1-10]": [
                        {
                            "NodeName": "juju-c9c6f-[1-10]",
                            "Name": "gpu",
                            "Type": "rtx",
                            "File": "/dev/nvidia[0-3]",
                            "Count": "8G",
                        }
                    ]
                },
            )

            del config.auto_detect

        # Exit the context to save changes to the gres.conf file.
        config = self.slurmctld.gres.load()
        self.assertIsNone(config.auto_detect)

        # Ensure that permissions on the gres.conf file are correct.
        f_info = Path("/etc/slurm/gres.conf").stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "-rw-r--r--")
        self.assertEqual(f_info.st_uid, FAKE_USER_UID)
        self.assertEqual(f_info.st_gid, FAKE_GROUP_GID)

    def test_slurmctld_manager_slurm_config(self) -> None:
        """Test `SlurmctldManager` slurm.conf configuration file editor."""
        self.fs.create_file("/etc/slurm/slurm.conf", contents=EXAMPLE_SLURM_CONFIG)

        # Fake user and group that owns the slurm.conf file.
        self.slurmctld.config._user = FAKE_USER_NAME
        self.slurmctld.config._group = FAKE_GROUP_NAME

        with self.slurmctld.config.edit() as config:
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

        # Exit the context to save changes to the slurm.conf file.
        config = self.slurmctld.config.load()
        self.assertEqual(config.slurmctld_port, "8081")
        self.assertNotEqual(config.return_to_service, "0")

        config_content = str(config).splitlines()
        self.assertIn(
            "NodeName=juju-c9fc6f-2 NodeAddr=10.152.28.48 CPUs=10 RealMemory=1000 TmpDisk=10000",
            config_content,
        )
        self.assertIn("NodeName=juju-c9fc6f-20 CPUs=1", config_content)
        self.assertIn('DownNodes=juju-c9fc6f-3 State=DOWN Reason="New nodes"', config_content)

        # Ensure that permissions on the slurm.conf file are correct.
        f_info = Path("/etc/slurm/slurm.conf").stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "-rw-r--r--")
        self.assertEqual(f_info.st_uid, FAKE_USER_UID)
        self.assertEqual(f_info.st_gid, FAKE_GROUP_GID)

    def test_slurmctld_manager_exporter_config(self) -> None:
        self.fs.create_file("/etc/default/prometheus-slurm-exporter")

        self.assertEqual(self.slurmctld.exporter.args, [])

        self.slurmctld.exporter.args = ["-slurm.cli-fallback", "-slurm.enable-diag"]

        self.assertEqual(
            self.slurmctld.exporter.args, ["-slurm.cli-fallback", "-slurm.enable-diag"]
        )
        self.assertEqual(
            dotenv.get_key("/etc/default/prometheus-slurm-exporter", "ARGS"),
            "-slurm.cli-fallback -slurm.enable-diag",
        )

        del self.slurmctld.exporter.args

        self.assertEqual(self.slurmctld.exporter.args, [])
        self.assertEqual(dotenv.get_key("/etc/default/prometheus-slurm-exporter", "ARGS"), None)

    def test_slurmd_config_server(self) -> None:
        """Test `SlurmdManager` `config_server` descriptors."""
        self.fs.create_file("/etc/default/slurmd")

        self.slurmd.config_server = "localhost"
        self.assertEqual(self.slurmd.config_server, "localhost")
        self.assertEqual(
            dotenv.get_key("/etc/default/slurmd", "SLURMD_CONFIG_SERVER"), "localhost"
        )

        del self.slurmd.config_server
        self.assertIsNone(self.slurmd.config_server)

    def test_slurmdbd_manager_slurmdbd_config(self) -> None:
        """Test `SlurmdbdManager` slurmdbd.conf configuration file editor."""
        self.fs.create_file("/etc/slurm/slurmdbd.conf", contents=EXAMPLE_SLURMDBD_CONFIG)

        # Fake user and group that owns the slurmdbd.conf file.
        self.slurmdbd.config._user = FAKE_USER_NAME
        self.slurmdbd.config._group = FAKE_GROUP_NAME

        with self.slurmdbd.config.edit() as config:
            self.assertEqual(config.auth_type, "auth/munge")
            self.assertEqual(config.debug_level, "info")

            config.storage_pass = "newpass"
            config.log_file = "/var/log/slurm/slurmdbd.log"
            del config.slurm_user

        # Exit the context to save changes to the slurmdbd.conf file.
        config = self.slurmdbd.config.load()
        self.assertEqual(config.storage_pass, "newpass")
        self.assertEqual(config.log_file, "/var/log/slurm/slurmdbd.log")
        self.assertNotEqual(config.slurm_user, "slurm")

        # Ensure that permissions on the slurmdbd.conf file are correct.
        f_info = Path("/etc/slurm/slurmdbd.conf").stat()
        self.assertEqual(stat.filemode(f_info.st_mode), "-rw-------")
        self.assertEqual(f_info.st_uid, FAKE_USER_UID)
        self.assertEqual(f_info.st_gid, FAKE_GROUP_GID)

    def test_slurmdbd_manager_mysql_unix_port(self) -> None:
        """Test `SlurmdbdManager` `mysql_unix_port` descriptors."""
        self.fs.create_file("/etc/default/slurmdbd")

        self.slurmdbd.mysql_unix_port = "/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock"
        self.assertEqual(
            self.slurmdbd.mysql_unix_port,
            "/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
        )
        self.assertEqual(
            dotenv.get_key("/etc/default/slurmdbd", "MYSQL_UNIX_PORT"),
            "/var/snap/charmed-mysql/common/run/mysqlrouter/mysql.sock",
        )

        del self.slurmdbd.mysql_unix_port
        self.assertIsNone(self.slurmdbd.mysql_unix_port)
