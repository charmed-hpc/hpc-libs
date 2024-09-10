from pathlib import Path

from pytest import Parser, fixture


def pytest_addoption(parser: Parser):
    parser.addoption("--snap", action="store_true")


@fixture(scope="session")
def snap(pytestconfig) -> bool:
    return pytestconfig.getoption("snap")


@fixture(scope="session")
def etc_path(snap: bool) -> Path:
    return Path("/var/snap/slurm/common/etc") if snap else Path("/etc")
