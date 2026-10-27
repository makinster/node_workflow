"""UI discovery must never reach the owner's local inference server in tests."""
import pytest


@pytest.fixture(autouse=True)
def isolated_model_picker_discovery(monkeypatch):
    async def unavailable(*args, **kwargs):
        raise ConnectionError('No fake discovery server configured')
    monkeypatch.setattr('frontend.widgets.local_model_picker.list_models', unavailable)
