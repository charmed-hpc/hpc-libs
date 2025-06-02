#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
import time
from pathlib import Path

import pytest

from hpc_libs.slurm_ops import SlurmctldManager


@pytest.fixture
def slurmctld(snap: bool) -> SlurmctldManager:
    return SlurmctldManager(snap=snap)


@pytest.mark.order(1)
def test_install(slurmctld: SlurmctldManager, etc_path: Path) -> None:
    """Install Slurm using the manager."""
    slurmctld.install()
    slurmctld.key.generate()

    key: bytes = (etc_path / "slurm" / "slurm.key").read_bytes()
    key: str = base64.b64encode(key).decode()

    assert key == slurmctld.key.get()


@pytest.mark.order(2)
def test_rotate_key(slurmctld: SlurmctldManager) -> None:
    """Test that the slurm key can be rotated."""
    old_key = slurmctld.key.get()
    slurmctld.key.generate()
    new_key = slurmctld.key.get()
    assert old_key != new_key


@pytest.mark.order(3)
def test_slurm_config(slurmctld: SlurmctldManager) -> None:
    """Test that the slurm config can be changed."""
    with slurmctld.config.edit() as config:
        config.slurmctld_host = [slurmctld.hostname]
        config.state_save_location = str(slurmctld._ops_manager.var_lib_path / "checkpoint")
        config.cluster_name = "test-cluster"
        config.auth_type = "auth/slurm"
        config.cred_type = "cred/slurm"
        config.slurm_user = "slurm"

    for line in str(slurmctld.config.load()).splitlines():
        entry = line.split("=")
        if len(entry) != 2:
            continue
        key, value = entry
        if key == "clustername":
            assert value == "test-cluster"
        if key == "slurmctldhost":
            assert value == slurmctld.hostname
        if key == "authtype":
            assert value == "auth/slurm"
        if key == "credtype":
            assert value == "cred/slurm"
        if key == "slurmuser":
            assert value == "slurm"


@pytest.mark.order(4)
def test_enable_service(slurmctld: SlurmctldManager) -> None:
    """Test that the slurmctld daemon can be started."""
    slurmctld.service.start()

    # The service is always active immediately after start, so wait a couple of seconds
    # to catch any delayed errors.
    time.sleep(5)

    assert slurmctld.service.active()


@pytest.mark.order(5)
def test_version(slurmctld: SlurmctldManager) -> None:
    """Test that the Slurm manager can report its version."""
    version = slurmctld.version()

    # We are interested in knowing that this does not return a falsy value (`None`, `''`, `[]`, etc.)
    assert version
