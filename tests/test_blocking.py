"""The event-loop blocking guard in conftest.py really catches blocking calls."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.grocy_pro.const import DOMAIN
from custom_components.grocy_pro.repairs import _old_card_file


async def test_guard_catches_file_io_in_loop(
    hass: HomeAssistant, no_blocking_io_in_loop
) -> None:
    """Calling an executor-only helper in the loop is reported."""
    _old_card_file(hass)
    assert no_blocking_io_in_loop
    assert "repairs.py" in no_blocking_io_in_loop[0]
    no_blocking_io_in_loop.clear()


async def test_flow_and_setup_do_not_block(
    hass: HomeAssistant, setup_integration, no_blocking_io_in_loop
) -> None:
    """Regression for 3.0.1: the user step read package metadata in the loop."""
    await setup_integration()
    await hass.config_entries.async_unload(
        hass.config_entries.async_entries(DOMAIN)[0].entry_id
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "abort"  # single instance: the entry still exists
    assert no_blocking_io_in_loop == []
