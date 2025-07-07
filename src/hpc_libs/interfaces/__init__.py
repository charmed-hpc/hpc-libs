# Copyright 2025 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration interfaces for HPC-related Juju charms."""

__all__ = [
    # From `base.py`
    "Condition",
    "ConditionEvaluation",
    "integration_exists",
    "integration_not_exists",
    "block_when",
    "wait_when",
    # From `slurm/common.py`
    "ControllerData",
    "SlurmctldConnectedEvent",
    "SlurmctldDisconnectedEvent",
    "SlurmctldReadyEvent",
    "controller_not_ready",
    # From `slurm/oci_runtime.py`
    "OCIRuntimeData",
    "OCIRuntimeDisconnectedEvent",
    "OCIRuntimeReadyEvent",
    "OCIRuntimeProvider",
    "OCIRuntimeRequirer",
    # From `slurm/slurmd.py`
    "ComputeData",
    "SlurmdReadyEvent",
    "SlurmdDisconnectedEvent",
    "SlurmdProvider",
    "SlurmdRequirer",
    "partition_not_ready",
]

from .base import (
    Condition,
    ConditionEvaluation,
    block_when,
    integration_exists,
    integration_not_exists,
    wait_when,
)
from .slurm.common import (
    ControllerData,
    SlurmctldConnectedEvent,
    SlurmctldDisconnectedEvent,
    SlurmctldReadyEvent,
    controller_not_ready,
)
from .slurm.oci_runtime import (
    OCIRuntimeData,
    OCIRuntimeDisconnectedEvent,
    OCIRuntimeProvider,
    OCIRuntimeReadyEvent,
    OCIRuntimeRequirer,
)
from .slurm.slurmd import (
    ComputeData,
    SlurmdDisconnectedEvent,
    SlurmdProvider,
    SlurmdReadyEvent,
    SlurmdRequirer,
    partition_not_ready,
)
