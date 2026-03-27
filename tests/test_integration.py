"""Unit tests for the ha-homismart integration.

All tests mock the homismart-client library and Home Assistant internals.
No real server or HA instance needed.
"""
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# Ensure project root is on sys.path so we can import custom_components.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ---------------------------------------------------------------------------
# HA module stubs — must be set up BEFORE importing custom_components.
# Each HA submodule gets its own MagicMock to avoid metaclass conflicts.
# ---------------------------------------------------------------------------

class ConfigEntryNotReady(Exception):
    pass

class FakeEntity:
    pass

class FakeDeviceInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class FakeColorMode:
    ONOFF = "onoff"

class FakeLightEntity(FakeEntity):
    pass

class FakeCoverEntity(FakeEntity):
    pass

class FakeSwitchEntity(FakeEntity):
    pass

# Build individual module mocks.
import types

def _make_module(name, attrs=None):
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

_callback = lambda f: f  # noqa: E731 — @callback is a no-op in tests

_make_module("homeassistant")
_make_module("homeassistant.const", {"CONF_USERNAME": "username", "CONF_PASSWORD": "password"})
_make_module("homeassistant.core", {"HomeAssistant": MagicMock, "callback": _callback})
class _FakeConfigFlow:
    def __init_subclass__(cls, **kwargs):
        pass  # Accept domain= keyword argument
_make_module("homeassistant.config_entries", {"ConfigEntry": MagicMock, "ConfigFlow": _FakeConfigFlow})
_make_module("homeassistant.data_entry_flow", {"FlowResult": MagicMock})
_make_module("homeassistant.exceptions", {"ConfigEntryNotReady": ConfigEntryNotReady, "HomeAssistantError": Exception})
_make_module("homeassistant.helpers")
_make_module("homeassistant.helpers.entity", {"Entity": FakeEntity, "DeviceInfo": FakeDeviceInfo})
_make_module("homeassistant.helpers.entity_platform", {"AddEntitiesCallback": MagicMock})

dispatcher_mock = MagicMock()
_make_module("homeassistant.helpers.dispatcher", {
    "async_dispatcher_send": dispatcher_mock.async_dispatcher_send,
    "async_dispatcher_connect": dispatcher_mock.async_dispatcher_connect,
})

dev_reg_mock = MagicMock()
_make_module("homeassistant.helpers.device_registry", {
    "async_get": dev_reg_mock.async_get,
})

_make_module("homeassistant.components")
_make_module("homeassistant.components.light", {
    "LightEntity": FakeLightEntity,
    "ColorMode": FakeColorMode,
})
_make_module("homeassistant.components.cover", {
    "CoverEntity": FakeCoverEntity,
    "CoverEntityFeature": MagicMock(),
    "CoverDeviceClass": MagicMock(),
    "ATTR_POSITION": "position",
})
_make_module("homeassistant.components.switch", {
    "SwitchEntity": FakeSwitchEntity,
    "SwitchDeviceClass": MagicMock(),
})

vol_mock = MagicMock()
vol_mock.Schema = MagicMock(return_value=MagicMock())
vol_mock.Required = MagicMock(side_effect=lambda x: x)
sys.modules["voluptuous"] = vol_mock

# Now we can import our modules.
from custom_components.homismart.const import (
    DOMAIN,
    SIGNAL_NEW_LIGHT,
    SIGNAL_NEW_SWITCH,
    SIGNAL_NEW_COVER,
    SIGNAL_UPDATE_DEVICE,
)
from custom_components.homismart.coordinator import HomiSmartCoordinator
from custom_components.homismart.entity import HomiSmartEntity
from custom_components.homismart.light import HomiSmartLight


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_coordinator():
    """Create a coordinator with mocked HA and client."""
    hass = MagicMock()
    hass.loop = asyncio.get_event_loop()
    entry = MagicMock()
    entry.data = {"username": "test@test.com", "password": "pass"}
    entry.entry_id = "test_entry_id"

    with patch("custom_components.homismart.coordinator.HomismartClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_client.is_connected = True
        mock_client.session = MagicMock()
        coordinator = HomiSmartCoordinator(hass, entry)
        # Replace the real client with our mock.
        coordinator.client = mock_client

    return coordinator, hass, entry


def _make_device(device_id="dev1", name="Test Device", is_online=True,
                 device_type_enum=None, device_type_code=2, pid="hub1",
                 version=1, is_on=True):
    """Create a mock HomismartDevice."""
    device = MagicMock()
    device.id = device_id
    device.name = name
    device.is_online = is_online
    device.device_type_enum = device_type_enum
    device.device_type_code = device_type_code
    device.pid = pid
    device.version = version
    device.is_on = is_on
    device.raw = {"id": device_id, "name": name}
    device.turn_on = AsyncMock()
    device.turn_off = AsyncMock()
    device.toggle = AsyncMock()
    return device


# ---------------------------------------------------------------------------
# Fix 2: Light color mode
# ---------------------------------------------------------------------------

def test_light_color_mode():
    """HomiSmartLight must declare supported_color_modes."""
    assert hasattr(HomiSmartLight, "_attr_supported_color_modes")
    assert HomiSmartLight._attr_supported_color_modes == {FakeColorMode.ONOFF}
    assert HomiSmartLight._attr_color_mode == FakeColorMode.ONOFF


# ---------------------------------------------------------------------------
# Fix 3: coordinator.connect() uses new API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coordinator_connect():
    """connect() should await client.connect(timeout=30) directly."""
    coordinator, hass, entry = _make_coordinator()
    await coordinator.connect()
    coordinator.client.connect.assert_awaited_once_with(timeout=30)


# ---------------------------------------------------------------------------
# Fix 4: ConfigEntryNotReady
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_setup_entry_connection_failure():
    """async_setup_entry should raise ConfigEntryNotReady on connect failure."""
    from custom_components.homismart import async_setup_entry

    hass = MagicMock()
    hass.loop = asyncio.get_event_loop()
    hass.data = {}
    entry = MagicMock()
    entry.data = {"username": "test@test.com", "password": "pass"}
    entry.entry_id = "test_entry"

    with patch("custom_components.homismart.coordinator.HomismartClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.connect = AsyncMock(side_effect=asyncio.TimeoutError("timeout"))
        mock_client.disconnect = AsyncMock()
        mock_client.session = MagicMock()

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


# ---------------------------------------------------------------------------
# Fix 5: disconnect simplified
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_disconnect():
    """disconnect() should call client.disconnect()."""
    coordinator, _, _ = _make_coordinator()
    await coordinator.disconnect()
    coordinator.client.disconnect.assert_awaited_once()


# ---------------------------------------------------------------------------
# Fix 6: Hub registration
# ---------------------------------------------------------------------------

def test_hub_registration():
    """Hub discovery should register in device_registry and HA device registry."""
    coordinator, hass, entry = _make_coordinator()

    mock_ha_dev_reg = MagicMock()

    hub = MagicMock()
    hub.id = "007CC709F6D6B8"
    hub.name = "Main Unit"
    hub.is_online = True

    with patch("custom_components.homismart.coordinator.dr.async_get", return_value=mock_ha_dev_reg):
        coordinator._handle_hub_update(hub)

    assert coordinator.device_registry["007CC709F6D6B8"] is hub
    mock_ha_dev_reg.async_get_or_create.assert_called_once_with(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "007CC709F6D6B8")},
        name="Main Unit",
        manufacturer="HomiSmart",
        model="Hub",
    )


# ---------------------------------------------------------------------------
# Fix 7: Entity availability
# ---------------------------------------------------------------------------

def test_entity_availability_connected_and_online():
    """Entity available when client connected and device online."""
    coordinator, _, _ = _make_coordinator()
    device = _make_device(is_online=True)
    type(coordinator.client).is_connected = PropertyMock(return_value=True)

    entity = HomiSmartEntity(coordinator, device)
    assert entity.available is True


def test_entity_availability_disconnected():
    """Entity unavailable when client disconnected."""
    coordinator, _, _ = _make_coordinator()
    device = _make_device(is_online=True)
    type(coordinator.client).is_connected = PropertyMock(return_value=False)

    entity = HomiSmartEntity(coordinator, device)
    assert entity.available is False


def test_entity_availability_device_offline():
    """Entity unavailable when device offline."""
    coordinator, _, _ = _make_coordinator()
    device = _make_device(is_online=False)
    type(coordinator.client).is_connected = PropertyMock(return_value=True)

    entity = HomiSmartEntity(coordinator, device)
    assert entity.available is False


# ---------------------------------------------------------------------------
# Fix 7 continued: device_info via_device
# ---------------------------------------------------------------------------

def test_entity_device_info_via_device():
    """device_info should set via_device when device.pid exists."""
    coordinator, _, _ = _make_coordinator()
    device = _make_device(pid="hub1")

    entity = HomiSmartEntity(coordinator, device)
    info = entity.device_info
    assert info.via_device == (DOMAIN, "hub1")


def test_entity_device_info_no_via_device():
    """device_info should not set via_device when device.pid is None."""
    coordinator, _, _ = _make_coordinator()
    device = _make_device(pid=None)

    entity = HomiSmartEntity(coordinator, device)
    info = entity.device_info
    assert info.via_device is None


# ---------------------------------------------------------------------------
# Fix 9: _handle_new_device dispatching + error handling
# ---------------------------------------------------------------------------

def test_handle_new_device_light():
    """DeviceType.SWITCH should dispatch SIGNAL_NEW_LIGHT."""
    from homismart_client.enums import DeviceType

    coordinator, hass, _ = _make_coordinator()
    device = _make_device(device_type_enum=DeviceType.SWITCH)

    coordinator._handle_new_device(device)

    dispatcher_mock.async_dispatcher_send.assert_called_with(
        hass, SIGNAL_NEW_LIGHT, device
    )


def test_handle_new_device_switch():
    """DeviceType.SOCKET should dispatch SIGNAL_NEW_SWITCH."""
    from homismart_client.enums import DeviceType

    coordinator, hass, _ = _make_coordinator()
    device = _make_device(device_type_enum=DeviceType.SOCKET)

    coordinator._handle_new_device(device)

    dispatcher_mock.async_dispatcher_send.assert_called_with(
        hass, SIGNAL_NEW_SWITCH, device
    )


def test_handle_new_device_cover():
    """DeviceType.CURTAIN should dispatch SIGNAL_NEW_COVER."""
    from homismart_client.enums import DeviceType

    coordinator, hass, _ = _make_coordinator()
    device = _make_device(device_type_enum=DeviceType.CURTAIN)

    coordinator._handle_new_device(device)

    dispatcher_mock.async_dispatcher_send.assert_called_with(
        hass, SIGNAL_NEW_COVER, device
    )


def test_handle_new_device_error():
    """Malformed device should not crash the handler."""
    coordinator, hass, _ = _make_coordinator()

    # Device that raises on attribute access.
    bad_device = MagicMock()
    bad_device.id = "bad1"
    type(bad_device).device_type_enum = PropertyMock(side_effect=RuntimeError("boom"))

    # Should not raise.
    coordinator._handle_new_device(bad_device)
    assert "bad1" in coordinator.device_registry


# ---------------------------------------------------------------------------
# Fix 8: config_flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_config_flow_connect_success():
    """validate_input should succeed when client.connect() succeeds."""
    from custom_components.homismart.config_flow import validate_input

    hass = MagicMock()

    with patch("custom_components.homismart.config_flow.HomismartClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        # Should not raise.
        await validate_input(hass, {"username": "test@test.com", "password": "pass"})
        mock_client.connect.assert_awaited_once_with(timeout=30)
        mock_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_config_flow_connect_timeout():
    """validate_input should raise ConnectionError on timeout."""
    from custom_components.homismart.config_flow import validate_input

    hass = MagicMock()

    with patch("custom_components.homismart.config_flow.HomismartClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.connect = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_client.disconnect = AsyncMock()

        with pytest.raises(ConnectionError, match="Timeout"):
            await validate_input(hass, {"username": "test@test.com", "password": "pass"})

        # disconnect should still be called in finally.
        mock_client.disconnect.assert_awaited_once()


# ---------------------------------------------------------------------------
# Light turn on/off
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_light_turn_on():
    """async_turn_on should call device.turn_on()."""
    coordinator, _, _ = _make_coordinator()
    device = _make_device()

    light = HomiSmartLight(coordinator, device)
    await light.async_turn_on()
    device.turn_on.assert_awaited_once()


@pytest.mark.asyncio
async def test_light_turn_off():
    """async_turn_off should call device.turn_off()."""
    coordinator, _, _ = _make_coordinator()
    device = _make_device()

    light = HomiSmartLight(coordinator, device)
    await light.async_turn_off()
    device.turn_off.assert_awaited_once()
