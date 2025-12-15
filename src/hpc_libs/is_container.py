# Copyright 2024 Canonical Ltd.
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

"""Detect if machine is a container instance.

Even though Juju supports using LXD containers as the backing cloud for
deploying charmed operators, not all HPC applications work within system containers,
and some need additional configuration. This simple charm library provides utilities
for identifying the virtualization runtime for a charmed operator.

### Example Usage:

```python3
from hpc_libs.is_container import is_container

class ApplicationCharm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.install, self._on_install)

    def _on_install(self, _: InstallEvent) -> None:
        if is_container():
            self.unit.status = BlockedStatus("app does not support container runtime")

        # Proceed with installation.
        ...
```
"""

import shutil
import subprocess


class UnknownVirtStateError(Exception):
    """Raise error if unknown virtualization state is returned."""

    @property
    def message(self) -> str:
        """Return message passed as argument to exception."""
        return self.args[0]


def is_container() -> bool:
    """Detect if the machine is a container instance.

    Raises:
        DetectVirtNotFoundError: Raised if `systemd-detect-virt` is not found on machine.
    """
    if shutil.which("systemd-detect-virt") is None:
        raise UnknownVirtStateError(
            (
                "executable `systemd-detect-virt` not found. "
                + "cannot determine if machine is a container instance"
            )
        )

    result = subprocess.run(
        ["systemd-detect-virt", "--container"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0
