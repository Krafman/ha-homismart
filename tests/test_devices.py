"""How HomiSmart devices map onto Home Assistant devices and entities."""
from __future__ import annotations

from pytest_homeassistant.common import MockConfigEntry, mock_device_registry

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.homismart.const import DOMAIN
from custom_components.homismart.coordinator import split_gang_names

from .conftest import HUB_ID, UNIT_ID, FakeServer, wait_for


def _device(hass: HomeAssistant, entry: MockConfigEntry, device_id: str) -> dr.DeviceEntry:
    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, device_id), entry.entry_id)
    assert device is not None, device_id
    return device


async def test_platforms_per_device_type(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Sockets and relays are switches, wall switches lights, shutters covers."""
    ent_reg = er.async_get(hass)
    expected = {
        "01516628000092": "switch.mamad_socket",
        "02518744000032": "light.stairway_light",
        "04518788000212": "cover.office_blinds",
        "06519917000173": "switch.water_heater",
        f"{UNIT_ID}-1": "switch.master_bdr_1",
        f"{UNIT_ID}-2": "switch.master_bdr_2",
    }
    for unique_id, entity_id in expected.items():
        domain = entity_id.split(".")[0]
        assert ent_reg.async_get_entity_id(domain, DOMAIN, unique_id) == entity_id

    assert hass.states.get("switch.mamad_socket").attributes["device_class"] == "outlet"
    assert hass.states.get("switch.water_heater").attributes["device_class"] == "switch"


async def test_device_tree(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    """Devices hang off the hub; the two gangs are children of one physical switch."""
    entry = setup_integration
    dev_reg = dr.async_get(hass)
    hub = _device(hass, entry, HUB_ID)
    assert (hub.name, hub.model) == ("Main Unit", "Hub")

    socket = _device(hass, entry, "01516628000092")
    assert socket.via_device_id == hub.id
    assert (socket.model, socket.model_id) == ("Socket", "1")

    unit = _device(hass, entry, UNIT_ID)
    assert (unit.name, unit.model, unit.via_device_id) == ("Master bdr", "Two-gang switch", hub.id)
    for relay in (1, 2):
        gang = dev_reg.async_get_child_device_by_identifier(
            (DOMAIN, f"{UNIT_ID}-{relay}"), entry.entry_id
        )
        assert gang is not None
        assert gang.parent_device_id == unit.id
        assert gang.name == str(relay)  # Shown as "Master bdr 1": parent + child.


async def test_existing_gang_devices_become_children_in_place(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> None:
    """Upgrading keeps each gang's device ID (and so its automations and area)."""
    # The device an older version created, as loaded from storage at startup.
    old = dr.DeviceEntry(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, f"{UNIT_ID}-2")},
        name="Master bdr 2",
        area_id="bedroom",
    )
    dev_reg = mock_device_registry(hass, {old.id: old})
    er.async_get(hass).async_get_or_create(
        Platform.SWITCH, DOMAIN, f"{UNIT_ID}-2", config_entry=config_entry,
        device_id=old.id, suggested_object_id="master_bdr_2",
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await wait_for(lambda: hass.states.get("switch.master_bdr_2") is not None)
    await hass.async_block_till_done()

    gang = dev_reg.async_get_child_device_by_identifier((DOMAIN, f"{UNIT_ID}-2"), config_entry.entry_id)
    assert gang is not None and gang.id == old.id
    assert gang.area_id == "bedroom"
    assert er.async_get(hass).async_get("switch.master_bdr_2").device_id == old.id
    await hass.config_entries.async_unload(config_entry.entry_id)


async def test_stale_entities_from_older_versions_are_removed(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> None:
    """Old versions created lights for shutters; those entries get cleaned up."""
    ent_reg = er.async_get(hass)
    stale = ent_reg.async_get_or_create(
        Platform.LIGHT, DOMAIN, "04518788000212", config_entry=config_entry,
        suggested_object_id="office_blinds",
    )

    await hass.config_entries.async_setup(config_entry.entry_id)
    await wait_for(lambda: hass.states.get("cover.office_blinds") is not None)
    await hass.async_block_till_done()

    assert ent_reg.async_get(stale.entity_id) is None
    assert ent_reg.async_get_entity_id(Platform.COVER, DOMAIN, "04518788000212")
    await hass.config_entries.async_unload(config_entry.entry_id)


async def test_device_removed_from_account(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """A device deleted in the HomiSmart app disappears from Home Assistant."""
    entry = setup_integration
    del server.devices["01516628000092"]
    server.current.push("0005", server.hubs + list(server.devices.values()))
    await wait_for(lambda: hass.states.get("switch.mamad_socket") is None)

    assert dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "01516628000092"), entry.entry_id
    ) is None
    assert er.async_get(hass).async_get("switch.mamad_socket") is None


async def test_unit_removed_with_its_last_gang(
    hass: HomeAssistant, server: FakeServer, setup_integration: MockConfigEntry
) -> None:
    """The physical two-gang device goes once neither gang exists any more."""
    entry = setup_integration
    for relay in (1, 2):
        del server.devices[f"{UNIT_ID}-{relay}"]
    server.current.push("0005", server.hubs + list(server.devices.values()))
    await wait_for(lambda: hass.states.get("switch.master_bdr_1") is None)
    await hass.async_block_till_done()

    assert dr.async_get(hass).async_get_device_by_identifier((DOMAIN, UNIT_ID), entry.entry_id) is None


def test_split_gang_names() -> None:
    """Shared leading words name the unit; the rest names each gang."""
    assert split_gang_names(["Master bdr 1", "Master bdr 2"]) == ("Master bdr", ["1", "2"])
    assert split_gang_names(["Upstairs Switch 1", "Upstairs Hallway Light"]) == (
        "Upstairs", ["Switch 1", "Hallway Light"]
    )
    # Nothing in common, identical names, or a lone gang: keep the full names.
    for names in (["Dining room light", "Living room Light"], ["Garden", "Garden"], ["Porch 1"]):
        assert split_gang_names(names) == ("Two-gang switch", names)
