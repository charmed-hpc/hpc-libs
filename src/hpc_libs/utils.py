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

__all__ = ["StopCharm", "get_ingress_address", "leader", "plog", "reconfigure", "refresh"]

import logging
import pprint
from collections.abc import Callable
from functools import wraps
from typing import Any

import ops

from hpc_libs.errors import IngressAddressNotFoundError

_logger = logging.getLogger(__name__)


class StopCharm(Exception):  # noqa N818
    """Exception raised to set high-priority status message."""

    @property
    def status(self) -> ops.StatusBase:
        """Get charm status passed as the first argument to this exception."""
        return self.args[0]


def plog(o: object) -> str:
    """Prettify built-in Python objects for log output."""
    return pprint.pformat(o, indent=4, sort_dicts=False)


def get_ingress_address(charm: ops.CharmBase, /, integration_name: str) -> str:
    """Get the ingress address of an integration endpoint.

    Args:
        charm: Charm integration endpoint is associated with.
        integration_name: Name of integration to look up network binding for.

    Raises:
        IngressAddressNotFoundError:
            Raised if the integration does not have a network binding.
        ops.RelationNotFoundError:
            Raised if the integration does not exist.
    """
    _logger.debug(
        "looking up network binding for integration '%s' in model `%s`",
        integration_name,
        charm.model.name,
    )

    if (binding := charm.model.get_binding(integration_name)) is not None:
        ingress_address = f"{binding.network.ingress_address}"
        _logger.debug(
            "ingress address for integration '%s' determined to be '%s'",
            integration_name,
            ingress_address,
        )
        return ingress_address

    _logger.error(
        "networking binding for integration '%s' in model `%s` does not exist",
        integration_name,
        charm.model.name,
    )
    raise IngressAddressNotFoundError(
        f"ingress address for integration '{integration_name}' was not found"
    )


def leader(func: Callable[..., Any]) -> Callable[..., Any]:
    """Only run method if the unit is the application leader, otherwise skip."""

    @wraps(func)
    def wrapper(charm: ops.CharmBase, *args: Any, **kwargs: Any) -> Any:
        if not charm.unit.is_leader():
            _logger.debug(
                (
                    "unit '%s' is not the leader of the '%s' application, ",
                    "skipping run of method `%s.%s`",
                ),
                charm.unit.name,
                charm.app.name,
                charm.__class__.__name__,
                func.__name__,
            )
            return None

        _logger.debug(
            "unit '%s' is the leader of the '%s' application, running method `%s.%s`",
            charm.unit.name,
            charm.app.name,
            charm.__class__.__name__,
            func.__name__,
        )
        return func(charm, *args, **kwargs)

    return wrapper


def reconfigure[T: ops.CharmBase](hook: Callable[[T], None] | None = None) -> Callable:
    """Reconfigure a service after running an event handler.

    Args:
        hook: Reconfiguration hook to call after event handler completes.
    """

    def decorator(func: Callable[..., None]) -> Callable:
        @wraps(func)
        def wrapper(charm: T, *args: ops.EventBase, **kwargs: Any) -> None:
            event, *_ = args

            try:
                func(charm, *args, **kwargs)
                if hook is not None:
                    hook(charm)
            except StopCharm as e:
                _logger.debug(
                    (
                        "`StopCharm` exception raised while running `%s` event handler `%s.%s` ",
                        "on unit '%s'. aborting service reconfiguration `%s`",
                    ),
                    event.__class__.__name__,
                    charm.__class__.__name__,
                    func.__name__,
                    charm.unit.name,  # type: ignore
                    e.status,
                )
                raise

        return wrapper

    return decorator


def refresh[T: ops.CharmBase](hook: Callable[[T], ops.StatusBase] | None = None) -> Callable:
    """Refresh a charm's status after running an event handler.

    Args:
        hook: State check hook to call after event handler completes.
    """

    def decorator(func: Callable[..., None]) -> Callable:
        @wraps(func)
        def wrapper(charm: T, *args: ops.EventBase, **kwargs: Any) -> None:
            event, *_ = args

            try:
                func(charm, *args, **kwargs)
            except StopCharm as e:
                _logger.debug(
                    (
                        "`StopCharm` exception raised while running `%s` event handler `%s.%s` ",
                        "on unit '%s'. setting status to `%s`",
                    ),
                    event.__class__.__name__,
                    charm.__class__.__name__,
                    func.__name__,
                    charm.unit.name,  # type: ignore
                    e.status,
                )
                charm.unit.status = e.status
                return

            if hook is not None:
                _logger.debug(
                    "running status check function `%s` to determine new status for unit '%s'",
                    hook.__name__,
                    charm.unit.name,  # type: ignore
                )
                status = hook(charm)
                _logger.debug(
                    "new status for unit '%s' determined to be `%s`",
                    charm.unit.name,  # type: ignore
                    status,
                )
                charm.unit.status = status

        return wrapper

    return decorator
