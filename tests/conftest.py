"""Shared fixtures: a fake HomiSmart server spoken to by the real client library."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
import copy
import hashlib
import json
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.homismart.const import DOMAIN

USERNAME = "user@example.com"
PASSWORD = "correct-password"
HUB_ID = "007CC709F6D6B8"
UNIT_ID = "07518733000047"

# Shaped like a real account (IDs and fields as the server sends them).
HUB = {"id": HUB_ID, "pid": HUB_ID, "type": 0, "name": "Main Unit", "onLine": True, "version": 9}
DEVICES = [
    {"id": "01516628000092", "pid": HUB_ID, "type": 1, "name": "Mamad Socket", "onLine": True, "power": True},
    {"id": "02518744000032", "pid": HUB_ID, "type": 2, "name": "Stairway light", "onLine": True, "power": False},
    {"id": "04518788000212", "pid": HUB_ID, "type": 4, "name": "Office Blinds", "onLine": True, "curtainState": "100"},
    {"id": "06519917000173", "pid": HUB_ID, "type": 6, "name": "WATER HEATER", "onLine": True, "power": False},
    {"id": f"{UNIT_ID}-1", "pid": HUB_ID, "type": 7, "relayNumber": 1, "deviceId": 12001,
     "name": "Master bdr 1", "onLine": True, "power": True},
    {"id": f"{UNIT_ID}-2", "pid": HUB_ID, "type": 7, "relayNumber": 2, "deviceId": 12001,
     "name": "Master bdr 2", "onLine": True, "power": False},
]

_CLOSED = object()


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


class FakeConnection:
    """One WebSocket connection to the fake server."""

    def __init__(self, server: FakeServer) -> None:
        self._server = server
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self.closed = False

    def push(self, prefix: str, payload: Any) -> None:
        self._queue.put_nowait(prefix + json.dumps(payload))

    async def send(self, message: str) -> None:
        prefix, payload = message[:4], json.loads(message[4:] or "{}")
        self._server.received.append((prefix, payload))
        self._server.handle(self, prefix, payload)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        if not self.closed:
            self.closed = True
            self._queue.put_nowait(_CLOSED)

    def __aiter__(self) -> FakeConnection:
        return self

    async def __anext__(self) -> str:
        item = await self._queue.get()
        if item is _CLOSED:
            raise StopAsyncIteration
        return item


class FakeServer:
    """Answers the HomiSmart protocol like the real cloud does."""

    def __init__(self) -> None:
        self.password_hash = _md5(PASSWORD)
        self.hubs = [copy.deepcopy(HUB)]
        self.devices = {d["id"]: copy.deepcopy(d) for d in DEVICES}
        self.connections: list[FakeConnection] = []
        self.received: list[tuple[str, Any]] = []
        self.reachable = True

    @property
    def current(self) -> FakeConnection:
        return self.connections[-1]

    async def connect(self, url: str, open_timeout: float | None = None) -> FakeConnection:
        if not self.reachable:
            raise OSError("HomiSmart unreachable")
        connection = FakeConnection(self)
        self.connections.append(connection)
        return connection

    def handle(self, conn: FakeConnection, prefix: str, payload: dict[str, Any]) -> None:
        if prefix == "0002":  # login
            if payload["password"] == self.password_hash:
                conn.push("0003", {"result": True, "shouldConfirmTerms": 0})
            else:
                conn.push("9999", {"code": 2})  # what the real server sends
        elif prefix == "0004":  # device list
            conn.push("0005", self.hubs + list(self.devices.values()))
        elif prefix == "0006":  # control a device: the server pushes the new state
            device = self.devices[payload["id"]]
            for key in ("power", "curtainState"):
                if key in payload:
                    device[key] = payload[key]
            conn.push("0009", device)

    def commands(self, prefix: str = "0006") -> list[dict[str, Any]]:
        return [payload for p, payload in self.received if p == prefix]

    async def drop(self) -> None:
        """The cloud closes the connection."""
        await self.current.close()


@pytest.fixture
def server() -> FakeServer:
    """A fake HomiSmart cloud the real client connects to."""
    fake = FakeServer()
    with (
        patch("homismart_client.client.websockets.connect", fake.connect),
        patch("homismart_client.client.RECONNECT_BASE_DELAY", 0),
    ):
        yield fake


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """A config entry for the test account."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=USERNAME,
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    entry.add_to_hass(hass)
    return entry


async def wait_for(condition: Callable[[], Any], timeout: float = 2.0) -> None:
    """Let the client's background tasks run until *condition* holds."""
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> AsyncGenerator[MockConfigEntry]:
    """Set up the integration and wait until every device has an entity."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await wait_for(lambda: hass.states.get("cover.office_blinds") is not None
                   and hass.states.get("switch.master_bdr_2") is not None)
    await hass.async_block_till_done()
    yield config_entry
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
