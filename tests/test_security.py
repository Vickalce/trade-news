from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.core.config import settings
from api.security import _REQUEST_WINDOWS, enforce_rate_limit, require_api_key



def test_require_api_key_rejects_invalid_key():
    with patch.object(settings, "api_key", "secret"):
        with pytest.raises(HTTPException) as exc:
            require_api_key(x_api_key="wrong")
        assert exc.value.status_code == 401



def test_require_api_key_accepts_valid_key():
    with patch.object(settings, "api_key", "secret"):
        assert require_api_key(x_api_key="secret") is None



def test_rate_limit_blocks_second_request():
    _REQUEST_WINDOWS.clear()
    request = SimpleNamespace(client=SimpleNamespace(host="testhost"), url=SimpleNamespace(path="/pipeline/run"))
    with patch.object(settings, "rate_limit_window_seconds", 60), patch.object(settings, "rate_limit_max_requests", 1):
        enforce_rate_limit(request)
        with pytest.raises(HTTPException) as exc:
            enforce_rate_limit(request)
        assert exc.value.status_code == 429
