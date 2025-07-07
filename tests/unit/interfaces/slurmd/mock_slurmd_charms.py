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

"""Mock charms for the `slurmd` interface unit tests."""

import ops
from slurmutils import Partition

from hpc_libs.interfaces import (
    ComputeData,
    ControllerData,
    SlurmctldConnectedEvent,
    SlurmctldReadyEvent,
    SlurmdDisconnectedEvent,
    SlurmdProvider,
    SlurmdReadyEvent,
    SlurmdRequirer,
    controller_not_ready,
    partition_not_ready,
    wait_when,
)
from hpc_libs.utils import refresh

SLURMD_INTEGRATION_NAME = "slurmd"
EXAMPLE_AUTH_KEY = "xyz123=="
EXAMPLE_CONTROLLERS = ["127.0.0.1", "127.0.1.1"]
EXAMPLE_PARTITION_CONFIG = Partition(partitionname="polaris")


class MockSlurmdProviderCharm(ops.CharmBase):
    """Mock `slurmd` provider charm."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self.slurmctld = SlurmdProvider(self, SLURMD_INTEGRATION_NAME)

        framework.observe(
            self.on.config_changed,
            self._on_config_changed,
        )
        framework.observe(
            self.slurmctld.on.slurmctld_connected,
            self._on_slurmctld_connected,
        )
        framework.observe(
            self.slurmctld.on.slurmctld_ready,
            self._on_slurmctld_ready,
        )

    def _on_config_changed(self, event: ops.ConfigChangedEvent) -> None:
        custom = self.config.get("partition-config", "")
        if custom and self.slurmctld.joined() and self.unit.is_leader():
            partition = Partition.from_str(custom)
            partition.partition_name = "polaris"
            self.slurmctld.set_compute_data(ComputeData(partitionconfig=partition))

    def _on_slurmctld_connected(self, event: SlurmctldConnectedEvent) -> None:
        self.slurmctld.set_compute_data(
            ComputeData(partitionconfig=EXAMPLE_PARTITION_CONFIG),
            integration_id=event.relation.id,
        )

    @refresh(check=None)
    @wait_when(controller_not_ready)
    def _on_slurmctld_ready(self, event: SlurmctldReadyEvent) -> None:
        data = self.slurmctld.get_controller_data(integration_id=event.relation.id)
        # Assume `remote_app_data` contains and `auth_key` and `controllers` list.
        assert data.auth_key == EXAMPLE_AUTH_KEY
        assert data.controllers == EXAMPLE_CONTROLLERS


class MockSlurmdRequirerCharm(ops.CharmBase):
    """Mock `slurmd` requirer charm."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self.slurmd = SlurmdRequirer(self, SLURMD_INTEGRATION_NAME)

        framework.observe(
            self.slurmd.on.slurmd_ready,
            self._on_slurmd_ready,
        )
        framework.observe(
            self.slurmd.on.slurmd_disconnected,
            self._on_slurmd_disconnected,
        )

    @refresh(check=None)
    @wait_when(partition_not_ready)
    def _on_slurmd_ready(self, event: SlurmdReadyEvent) -> None:
        data = self.slurmd.get_compute_data(integration_id=event.relation.id)
        # Assume `remote_app_data` contains partition configuration data.
        assert data.partitionconfig.dict() == EXAMPLE_PARTITION_CONFIG.dict()

        self.slurmd.set_controller_data(
            ControllerData(
                auth_key=EXAMPLE_AUTH_KEY,
                controllers=EXAMPLE_CONTROLLERS,
            )
        )

    def _on_slurmd_disconnected(self, event: SlurmdDisconnectedEvent) -> None: ...
