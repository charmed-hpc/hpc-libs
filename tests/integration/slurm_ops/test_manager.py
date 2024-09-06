#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
from pathlib import Path

import pytest

from lib.charms.hpc_libs.v0.slurm_ops import SlurmctldManager


@pytest.fixture
def slurmctld() -> SlurmctldManager:
    return SlurmctldManager(snap=True)


@pytest.mark.order(1)
def test_install(slurmctld: SlurmctldManager) -> None:
    """Install Slurm using the manager."""
    slurmctld.install()
    slurmctld.munge.key.generate()

    with open("/var/snap/slurm/common/etc/munge/munge.key", "rb") as f:
        key: str = base64.b64encode(f.read()).decode()

    assert key == slurmctld.munge.key.get()


@pytest.mark.order(2)
def test_rotate_key(slurmctld: SlurmctldManager) -> None:
    """Test that the munge key can be rotated."""
    old_key = slurmctld.munge.key.get()
    slurmctld.munge.key.generate()
    new_key = slurmctld.munge.key.get()
    assert old_key != new_key


@pytest.mark.order(3)
def test_slurm_config(slurmctld: SlurmctldManager) -> None:
    """Test that the slurm config can be changed."""
    with slurmctld.config() as config:
        config.slurmctld_host = ["test-slurm-ops"]
        config.cluster_name = "test-cluster"

    print(Path("/var/snap/slurm/common/etc/slurm/slurm.conf").read_text())

    for line in Path("/var/snap/slurm/common/etc/slurm/slurm.conf").read_text().splitlines():
        entry = line.split("=")
        if len(entry) != 2:
            continue
        key, value = entry
        if key == "ClusterName":
            assert value == "test-cluster"
        if key == "SlurmctldHost":
            assert value == "test-slurm-ops"


@pytest.mark.order(4)
def test_enable_service(slurmctld: SlurmctldManager) -> None:
    """Test that the slurmctl daemon can be enabled."""
    slurmctld.service.enable()
    assert slurmctld.service.active()


@pytest.mark.order(5)
def test_version(slurmctld: SlurmctldManager) -> None:
    """Test that the Slurm manager can report its version."""
    version = slurmctld.version()

    # We are interested in knowing that this does not return a falsy value (`None`, `''`, `[]`, etc.)
    assert version
