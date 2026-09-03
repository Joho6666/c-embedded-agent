import pytest

from app.net import PublicURLError, assert_public_http_url


def test_reject_localhost():
    with pytest.raises(PublicURLError):
        assert_public_http_url("http://localhost:8000")
    with pytest.raises(PublicURLError):
        assert_public_http_url("http://127.0.0.1/v1")


def test_reject_private():
    with pytest.raises(PublicURLError):
        assert_public_http_url("http://192.168.1.1")
    with pytest.raises(PublicURLError):
        assert_public_http_url("http://10.0.0.2")


def test_reject_non_http():
    with pytest.raises(PublicURLError):
        assert_public_http_url("ftp://example.com")
