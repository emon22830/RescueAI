"""How CORS_ORIGINS is read.

A malformed value fails invisibly — the browser reports a bare network error and every
screen in the deployed app reads as "the backend is down" — so the parsing is forgiving
about how the value was typed into a hosting dashboard.
"""

from app.config import Settings


def test_trailing_slash_is_not_a_different_origin():
    """A browser sends `https://app.example` as its Origin, never with the slash."""
    settings = Settings(cors_origins="https://app.example/")
    assert settings.allowed_origins == ["https://app.example"]


def test_quotes_pasted_around_the_value_are_dropped():
    settings = Settings(cors_origins='"https://app.example"')
    assert settings.allowed_origins == ["https://app.example"]


def test_a_comma_list_keeps_every_origin_and_ignores_spacing():
    settings = Settings(cors_origins=" https://app.example , http://localhost:5173 ")
    assert settings.allowed_origins == ["https://app.example", "http://localhost:5173"]


def test_blank_entries_never_become_an_empty_origin():
    settings = Settings(cors_origins="https://a.example,,")
    assert settings.allowed_origins == ["https://a.example"]


def test_app_url_is_the_first_origin_normalized():
    """It is pasted into a Google OAuth redirect; a trailing slash there makes `//app`."""
    settings = Settings(cors_origins="https://app.example/,http://localhost:5173")
    assert settings.app_url == "https://app.example"


def test_app_url_falls_back_when_no_origin_is_configured():
    assert Settings(cors_origins="").app_url == "http://localhost:5173"


def test_unhandled_error_still_answers_with_cors_headers(client):
    """A crash must look like a crash, not like a backend that is down.

    Starlette answers an unhandled exception outside the CORS middleware, so the 500
    goes back with no access-control-allow-origin, the browser refuses to show it and
    the UI reports the whole backend as unreachable. main.py catches it inside the CORS
    layer instead.
    """
    from app.main import app

    @app.get("/_test_boom")
    def boom():
        raise RuntimeError("nothing handles this")

    try:
        response = client.get("/_test_boom", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 500
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "unexpected error" in response.json()["detail"]
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/_test_boom"]
