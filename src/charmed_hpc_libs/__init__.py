# Copyright 2025-2026 Canonical Ltd.
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

"""Libraries for authoring HPC charms."""

__all__ = [
    # From `errors` module
    "Error",
    "IngressAddressNotFoundError",
    "SnapError",
    "SystemdError",
    "UnknownVirtualizationStateError",
    # From `interfaces` module
    "Interface",
    # From `ops` module
    "Condition",
    "ConditionEvaluation",
    "EnvManager",
    "ServiceManager",
    "SnapServiceManager",
    "StopCharm",
    "SystemctlServiceManager",
    "block_unless",
    "call",
    "get_ingress_address",
    "integration_exists",
    "integration_not_exists",
    "is_container",
    "leader",
    "load_secret",
    "refresh",
    "snap",
    "systemctl",
    "update_secret",
    "wait_unless",
]

from .errors import (
    Error,
    IngressAddressNotFoundError,
    SnapError,
    SystemdError,
    UnknownVirtualizationStateError,
)
from .interfaces import Interface
from .ops import (
    Condition,
    ConditionEvaluation,
    EnvManager,
    ServiceManager,
    SnapServiceManager,
    StopCharm,
    SystemctlServiceManager,
    block_unless,
    call,
    get_ingress_address,
    integration_exists,
    integration_not_exists,
    is_container,
    leader,
    load_secret,
    refresh,
    snap,
    systemctl,
    update_secret,
    wait_unless,
)
