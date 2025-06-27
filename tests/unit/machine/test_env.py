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

"""Unit tests for the `env` machine library."""

from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from hpc_libs.machine import EnvManager

ENV_FILE = "/etc/default/slurmd"


class TestEnvManager:
    """Test the `EnvManager` class."""

    @pytest.fixture
    def env_manager(self, fs: FakeFilesystem) -> EnvManager:
        """Create an `EnvManager` object with a fake environment file."""
        fs.create_file(ENV_FILE)
        return EnvManager(ENV_FILE)

    def test_set(self, env_manager: EnvManager) -> None:
        """Test the `set` method."""
        env_manager.set({"SLURMD_CONFIG_SERVER": "localhost:6817"})
        with open(ENV_FILE, "rt") as fin:
            assert fin.read() == "SLURMD_CONFIG_SERVER='localhost:6817'\n"

    def test_get(self, env_manager: EnvManager) -> None:
        """Test the `get` method."""
        env_manager.set({"SLURMD_CONFIG_SERVER": "localhost:6817"})
        assert env_manager.get("SLURMD_CONFIG_SERVER") == "localhost:6817"

    def test_unset(self, env_manager: EnvManager) -> None:
        """Test the `unset` method."""
        env_manager.unset("SLURMD_CONFIG_SERVER")
        with open(ENV_FILE, "rt") as fin:
            assert fin.read() == ""

    def test_path(self, env_manager: EnvManager) -> None:
        """Test the `path` property."""
        assert env_manager.path == Path(ENV_FILE)
