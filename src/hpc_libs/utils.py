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

"""Utilities for streamlining common operations within HPC-related Juju charms."""

__all__ = ["leader"]

from collections.abc import Callable
from functools import wraps
from typing import Any

import ops


def leader(func: Callable[..., Any]) -> Callable[..., Any]:
    """Only run method if the unit is the application leader, otherwise skip."""

    @wraps(func)
    def wrapper(charm: ops.CharmBase, *args: Any, **kwargs: Any) -> Any:
        if not charm.unit.is_leader():
            return None

        return func(charm, *args, **kwargs)

    return wrapper
