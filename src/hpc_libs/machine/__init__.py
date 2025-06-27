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

"""Machine libraries for HPC-related Juju charms."""

__all__ = [
    # From vendored `apt.py`
    "apt",
    # From `core` module
    "ServiceManager",
    "call",
    # From `env.py`
    "EnvManager",
    # From `snap.py`
    "SnapServiceManager",
    "snap",
    # From `systemd.py`
    "SystemctlServiceManager",
    "systemctl",
]

import hpc_libs.machine.apt as apt
from hpc_libs.machine.core import ServiceManager, call
from hpc_libs.machine.env import EnvManager
from hpc_libs.machine.snap import SnapServiceManager, snap
from hpc_libs.machine.systemd import SystemctlServiceManager, systemctl
