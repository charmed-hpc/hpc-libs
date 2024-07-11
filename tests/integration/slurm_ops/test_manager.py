#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import base64

import pytest

import lib.charms.hpc_libs.v0.slurm_ops as slurm
from lib.charms.hpc_libs.v0.slurm_ops import ServiceType, SlurmManagerBase


@pytest.fixture
def slurmctld() -> SlurmManagerBase:
    return SlurmManagerBase(ServiceType.SLURMCTLD)


@pytest.mark.order(1)
def test_install(slurmctld: SlurmManagerBase) -> None:
    """Install Slurm using the manager."""
    slurm.install()
    slurmctld.munge.generate_key()

    with open("/var/snap/slurm/common/etc/munge/munge.key", "rb") as f:
        key: str = base64.b64encode(f.read()).decode()

    assert key == slurmctld.munge.get_key()


@pytest.mark.order(2)
def test_rotate_key(slurmctld: SlurmManagerBase) -> None:
    """Test that the munge key can be rotated."""
    old_key = slurmctld.munge.get_key()
    slurmctld.munge.generate_key()
    new_key = slurmctld.munge.get_key()
    assert old_key != new_key


@pytest.mark.order(3)
def test_slurm_config(slurmctld: SlurmManagerBase) -> None:
    """Test that the slurm config can be changed."""
    slurmctld.config.set({"slurmctld-host": "test-slurm-ops", "cluster-name": "test-cluster"})
    value = slurmctld.config.get("cluster-name")
    assert value == "test-cluster"

    with open("/var/snap/slurm/common/etc/slurm/slurm.conf", "r") as f:
        output = f.read()

    for line in output.splitlines():
        entry = line.split("=")
        if len(entry) != 2:
            continue
        key, value = entry
        if key == "ClusterName":
            assert value == "test-cluster"


@pytest.mark.order(4)
def test_enable_service(slurmctld: SlurmManagerBase) -> None:
    """Test that the slurmctl daemon can be enabled."""
    slurmctld.enable()
    assert slurmctld.active()


@pytest.mark.order(5)
def test_version() -> None:
    """Test that the Slurm manager can report its version."""
    version = slurm.version()

    # We are interested in knowing that this does not return a falsy value (`None`, `''`, `[]`, etc.)
    assert version
