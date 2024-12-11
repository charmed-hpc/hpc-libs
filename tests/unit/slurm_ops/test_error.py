#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for custom errors."""

import subprocess
from unittest import TestCase
from unittest.mock import patch

from charms.hpc_libs.v0.slurm_ops import SlurmOpsError


@patch(
    "charms.hpc_libs.v0.slurm_ops.subprocess.run",
    return_value=subprocess.CompletedProcess([], returncode=0),
)
class TestSlurmOpsError(TestCase):
    def test_error_message(self, *_) -> None:
        """Test that `SlurmOpsError` stores the correct message."""
        message = "error message!"
        self.assertEqual(SlurmOpsError(message).message, message)
