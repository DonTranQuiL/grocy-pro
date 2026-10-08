"""The picture proxy."""

from __future__ import annotations

from http import HTTPStatus

from homeassistant.core import HomeAssistant

from .conftest import API_URL

GOOD = "/api/grocy_pro/productpictures/Y29va2llcy5qcGc="


async def test_proxies_picture(
    hass: HomeAssistant, setup_integration, hass_client_no_auth, aioclient_mock
) -> None:
    """Pictures are fetched from Grocy with the API key and resized."""
    await setup_integration()
    aioclient_mock.get(
        f"{API_URL}/files/productpictures/Y29va2llcy5qcGc=",
        content=b"JPEGDATA",
        headers={"Content-Type": "image/jpeg", "Cache-Control": "max-age=3600"},
    )
    client = await hass_client_no_auth()
    response = await client.get(f"{GOOD}?width=99999")
    assert response.status == HTTPStatus.OK
    assert await response.read() == b"JPEGDATA"
    assert response.headers["Content-Type"] == "image/jpeg"
    _, url, _, headers = aioclient_mock.mock_calls[-1]
    assert url.query["best_fit_width"] == "2000"
    assert url.query["force_serve_as"] == "picture"
    assert headers["GROCY-API-KEY"] == "secret-key"


async def test_rejects_bad_requests(
    hass: HomeAssistant, setup_integration, hass_client_no_auth, aioclient_mock
) -> None:
    """Only the two picture folders and base64 names are allowed."""
    await setup_integration()
    client = await hass_client_no_auth()
    assert (await client.get("/api/grocy_pro/backups/Y29va2llcy5qcGc=")).status == 404
    assert (await client.get("/api/grocy_pro/productpictures/not*base64")).status == 400
    assert not aioclient_mock.mock_calls


async def test_upstream_errors(
    hass: HomeAssistant, setup_integration, hass_client_no_auth, aioclient_mock
) -> None:
    """Grocy errors are passed on as status codes."""
    from aiohttp import ClientError

    await setup_integration()
    client = await hass_client_no_auth()
    aioclient_mock.get(f"{API_URL}/files/productpictures/Y29va2llcy5qcGc=", status=404)
    assert (await client.get(GOOD)).status == 404
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{API_URL}/files/productpictures/Y29va2llcy5qcGc=", exc=ClientError()
    )
    assert (await client.get(GOOD)).status == 502


async def test_not_loaded(
    hass: HomeAssistant, setup_integration, hass_client_no_auth
) -> None:
    """Without a loaded entry the proxy answers 503."""
    entry = await setup_integration()
    await hass.config_entries.async_unload(entry.entry_id)
    client = await hass_client_no_auth()
    assert (await client.get(GOOD)).status == 503
