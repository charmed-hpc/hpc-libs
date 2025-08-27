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
    "block_unless",
    "integration_exists",
    "integration_not_exists",
    "load_secret",
    "update_secret",
    "wait_unless",
    # From `slurm/common.py`
    "ControllerData",
    "SlurmctldConnectedEvent",
    "SlurmctldDisconnectedEvent",
    "SlurmctldReadyEvent",
    "controller_ready",
    # From `slurm/oci_runtime.py`
    "OCIRuntimeData",
    "OCIRuntimeDisconnectedEvent",
    "OCIRuntimeReadyEvent",
    "OCIRuntimeProvider",
    "OCIRuntimeRequirer",
    # From `slurm/sackd.py`
    "SackdProvider",
    "SackdRequirer",
    "SackdConnectedEvent",
    # From `slurm/slurmd.py`
    "ComputeData",
    "SlurmdConnectedEvent",
    "SlurmdReadyEvent",
    "SlurmdDisconnectedEvent",
    "SlurmdProvider",
    "SlurmdRequirer",
    "partition_ready",
    # From `slurm/slurmdbd.py`
    "DatabaseData",
    "SlurmdbdProvider",
    "SlurmdbdRequirer",
    "SlurmdbdConnectedEvent",
    "SlurmdbdReadyEvent",
    "SlurmdbdDisconnectedEvent",
    "database_ready",
    # From `slurm/slurmrestd.py`
    "SlurmrestdProvider",
    "SlurmrestdRequirer",
    "SlurmrestdConnectedEvent",
]

from .base import (
    Condition,
    ConditionEvaluation,
    block_unless,
    integration_exists,
    integration_not_exists,
    load_secret,
    update_secret,
    wait_unless,
)
from .slurm.common import (
    ControllerData,
    SlurmctldConnectedEvent,
    SlurmctldDisconnectedEvent,
    SlurmctldReadyEvent,
    controller_ready,
)
from .slurm.oci_runtime import (
    OCIRuntimeData,
    OCIRuntimeDisconnectedEvent,
    OCIRuntimeProvider,
    OCIRuntimeReadyEvent,
    OCIRuntimeRequirer,
)
from .slurm.sackd import (
    SackdConnectedEvent,
    SackdProvider,
    SackdRequirer,
)
from .slurm.slurmd import (
    ComputeData,
    SlurmdConnectedEvent,
    SlurmdDisconnectedEvent,
    SlurmdProvider,
    SlurmdReadyEvent,
    SlurmdRequirer,
    partition_ready,
)
from .slurm.slurmdbd import (
    DatabaseData,
    SlurmdbdConnectedEvent,
    SlurmdbdDisconnectedEvent,
    SlurmdbdProvider,
    SlurmdbdReadyEvent,
    SlurmdbdRequirer,
    database_ready,
)
from .slurm.slurmrestd import (
    SlurmrestdConnectedEvent,
    SlurmrestdProvider,
    SlurmrestdRequirer,
)
