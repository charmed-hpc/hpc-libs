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

"""Mock charms for the `slurm_oci_runtime` interface unit tests."""

import ops
from ops import Framework
from slurmutils import OCIConfig

from hpc_libs.interfaces import (
    OCIRunTimeData,
    OCIRunTimeDisconnectedEvent,
    OCIRunTimeProvider,
    OCIRunTimeReadyEvent,
    OCIRunTimeRequirer,
    SlurmctldConnectedEvent,
)

OCI_RUNTIME_INTEGRATION_NAME = "oci-runtime"
EXAMPLE_OCI_CONFIG = OCIConfig(
    ignorefileconfigjson=False,
    envexclude="^(SLURM_CONF|SLURM_CONF_SERVER)=",
    runtimeenvexclude="^(SLURM_CONF|SLURM_CONF_SERVER)=",
    runtimerun="apptainer exec --userns %r %@",
    runtimekill="kill -s SIGTERM %p",
    runtimedelete="kill -s SIGKILL %p",
)


class MockOCIRunTimeProviderCharm(ops.CharmBase):
    """Mock OCI runtime provider charm."""

    def __init__(self, framework: Framework) -> None:
        super().__init__(framework)

        self._oci_runtime = OCIRunTimeProvider(self, OCI_RUNTIME_INTEGRATION_NAME)

        framework.observe(self._oci_runtime.on.slurmctld_connected, self._on_slurmctld_connected)

    def _on_slurmctld_connected(self, event: SlurmctldConnectedEvent) -> None:
        self._oci_runtime.set_oci_runtime_data(
            OCIRunTimeData(ociconfig=EXAMPLE_OCI_CONFIG),
            integration_id=event.relation.id,
        )


class MockOCIRunTimeRequirerCharm(ops.CharmBase):
    """Mock OCI runtime requirer charm."""

    def __init__(self, framework: Framework) -> None:
        super().__init__(framework)

        self._oci_runtime = OCIRunTimeRequirer(self, OCI_RUNTIME_INTEGRATION_NAME)

        framework.observe(
            self._oci_runtime.on.oci_runtime_ready,
            self._on_oci_runtime_ready,
        )
        framework.observe(
            self._oci_runtime.on.oci_runtime_disconnected,
            self._on_oci_runtime_disconnected,
        )

    def _on_oci_runtime_ready(self, event: OCIRunTimeReadyEvent) -> None:
        config = self._oci_runtime.get_oci_runtime_data(event.relation)
        # Assume `remote_app_data` contains `oci.conf` configuration data.
        assert config.ociconfig.dict() == EXAMPLE_OCI_CONFIG.dict()

    def _on_oci_runtime_disconnected(self, event: OCIRunTimeDisconnectedEvent) -> None: ...
