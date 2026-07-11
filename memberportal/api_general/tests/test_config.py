import builtins

import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db

CONFIG_URL = "/api/config/"


def test_config_returns_200_with_version_and_features(api_client):
    """The site config endpoint must serve the version and feature flags.

    This is the payload the frontend relies on at boot (getSiteConfig); if it
    500s, features stays empty and gated UI such as Stripe billing silently
    disappears.
    """
    response = api_client.get(CONFIG_URL)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    # Version comes from package.json and must resolve to a real value.
    assert body["version"]
    assert body["version"] != "unknown"

    # Features must be populated so the frontend's enableStripe gate works.
    assert isinstance(body["features"], dict)
    assert "enableStripe" in body["features"]


def test_config_survives_missing_package_json(api_client):
    """A missing/unreadable package.json must not 500 the whole config endpoint.

    Regression test for the Docker deployment bug: the version was read from a
    path that only exists in a source checkout (src-frontend/package.json), so
    the file was absent in the image and /api/config/ returned 500 -- taking
    Stripe, theme, and every other feature flag down with it. The version read
    is now guarded and falls back to "unknown".
    """
    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if str(file).endswith("package.json"):
            raise FileNotFoundError(2, "No such file or directory", str(file))
        return real_open(file, *args, **kwargs)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(builtins, "open", fake_open)
        response = api_client.get(CONFIG_URL)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["version"] == "unknown"
    # The rest of the config must still be served.
    assert "enableStripe" in body["features"]
