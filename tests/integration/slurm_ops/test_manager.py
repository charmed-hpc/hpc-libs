#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


import pytest

from lib.charms.hpc_libs.v0.slurm_ops import Service, SlurmManager


@pytest.fixture
def slurm_manager() -> SlurmManager:
    return SlurmManager(Service.SLURMCTLD)


@pytest.mark.order(1)
def test_install(slurm_manager: SlurmManager) -> None:
    """Install Slurm using the manager."""
    slurm_manager.install()
    slurm_manager.enable()
    slurm_manager.set_munge_key(slurm_manager.generate_munge_key())

    with open("/var/snap/slurm/common/etc/munge/munge.key", "rb") as f:
        key: bytes = f.read()

    assert key == slurm_manager.get_munge_key()


@pytest.mark.order(2)
def test_rotate_key(slurm_manager: SlurmManager) -> None:
    """Test that the munge key can be rotated."""
    old_key = slurm_manager.get_munge_key()

    slurm_manager.set_munge_key(slurm_manager.generate_munge_key())

    new_key = slurm_manager.get_munge_key()

    assert old_key != new_key


@pytest.mark.order(3)
def test_slurm_config(slurm_manager: SlurmManager) -> None:
    """Test that the slurm config can be changed."""
    slurm_manager.set_config("cluster-name", "test-cluster")
    slurm_manager.set_configs({"max-tasks-per-node": "30000", "inactive-limit": "60000"})

    assert slurm_manager.get_config("cluster-name") == "test-cluster"
    assert slurm_manager.get_config("max-tasks-per-node") == "30000"
    assert slurm_manager.get_config("inactive-limit") == "60000"

    with open("/var/snap/slurm/common/etc/slurm/slurm.conf", "r") as f:
        output = f.read()

    for line in output.splitlines():
        entry = line.split("=")
        if len(entry) != 2:
            continue
        key, value = entry
        if key == "ClusterName":
            assert value == "test-cluster"
        elif key == "MaxTasksPerNode":
            assert value == "30000"
        elif key == "InactiveLimit":
            assert value == "60000"


@pytest.mark.order(4)
def test_version(slurm_manager: SlurmManager) -> None:
    """Test that the Slurm manager can report its version."""
    version = slurm_manager.version()

    # We are interested in knowing that this does not return a falsy value (`None`, `''`, `[]`, etc.)
    assert version
