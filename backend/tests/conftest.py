import pytest

from sentinel.generator.bangkit import DataTiruan, bangkitkan


@pytest.fixture(scope="session")
def utama() -> DataTiruan:
    return bangkitkan("utama")


@pytest.fixture(scope="session")
def hidden() -> DataTiruan:
    return bangkitkan("hidden")


@pytest.fixture(scope="session", params=["utama", "hidden"])
def dataset(request, utama, hidden) -> DataTiruan:
    return {"utama": utama, "hidden": hidden}[request.param]
