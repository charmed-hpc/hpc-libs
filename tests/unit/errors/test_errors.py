# Copyright 2026 Canonical Ltd.
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

"""Unit tests for HPC charm error classes."""

import pytest

from charmed_hpc_libs.errors import (
    IngressAddressNotFoundError,
    SnapError,
    SystemdError,
    UnknownVirtualizationStateError,
)


def test_ingress_address_not_found_error() -> None:
    """Test the `IngressAddressNotFoundError` exception."""
    with pytest.raises(IngressAddressNotFoundError) as exec_info:
        raise IngressAddressNotFoundError("address not found")

    assert exec_info.value.message == "address not found"


def test_snap_error() -> None:
    """Test the `SnapError` exception."""
    with pytest.raises(SnapError) as exec_info:
        raise SnapError("snap install failed")

    assert exec_info.value.message == "snap install failed"


def test_systemd_error() -> None:
    """Test the `SystemdError` exception."""
    with pytest.raises(SystemdError) as exec_info:
        raise SystemdError("service start failed")

    assert exec_info.value.message == "service start failed"


def test_unknown_virtualization_state_error() -> None:
    """Test the `UnknownVirtualizationStateError` exception."""
    with pytest.raises(UnknownVirtualizationStateError) as exec_info:
        raise UnknownVirtualizationStateError("unknown state")

    assert exec_info.value.message == "unknown state"
