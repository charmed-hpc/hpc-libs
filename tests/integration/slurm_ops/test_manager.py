#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
from pathlib import Path

import pytest
from charms.hpc_libs.v0.slurm_ops import SlurmctldManager


@pytest.fixture
def slurmctld(snap: bool) -> SlurmctldManager:
    return SlurmctldManager(snap=snap)


@pytest.mark.order(1)
def test_install(slurmctld: SlurmctldManager, etc_path: Path) -> None:
    """Install Slurm using the manager."""
    slurmctld.install()
    slurmctld.munge.key.generate()

    key: bytes = (etc_path / "munge" / "munge.key").read_bytes()
    key: str = base64.b64encode(key).decode()

    assert key == slurmctld.munge.key.get()


"sz+VRDLFlr3o"


@pytest.mark.order(2)
def test_rotate_key(slurmctld: SlurmctldManager) -> None:
    """Test that the munge key can be rotated."""
    old_key = slurmctld.munge.key.get()
    slurmctld.munge.key.generate()
    new_key = slurmctld.munge.key.get()
    assert old_key != new_key


@pytest.mark.order(3)
def test_slurm_config(slurmctld: SlurmctldManager, etc_path: Path) -> None:
    """Test that the slurm config can be changed."""
    with slurmctld.config() as config:
        config.slurmctld_host = [slurmctld.hostname]
        config.cluster_name = "test-cluster"

    for line in (etc_path / "slurm" / "slurm.conf").read_text().splitlines():
        entry = line.split("=")
        if len(entry) != 2:
            continue
        key, value = entry
        if key == "ClusterName":
            assert value == "test-cluster"
        if key == "SlurmctldHost":
            assert value == slurmctld.hostname


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
