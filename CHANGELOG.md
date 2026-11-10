# Changelog

## 1.2.0 — 2026-11-10

Requires Home Assistant 2026.11 and homismart-client 0.3.1.

### Fixed
- **New installs can connect again.** The integration now uses homismart-client
  0.3.1; older client versions pointed at a HomiSmart server that no longer exists.
- No more "blocking call" warning at startup: the connection uses Home
  Assistant's shared TLS context.
- **Cover positions use Home Assistant's direction** (0% closed, 100% open). They
  were reversed before, so check automations that set a position.
- A wrong password now shows "Wrong email or password" immediately, instead of
  "cannot connect" after 30 seconds.
- Devices show as unavailable while the connection to HomiSmart is down, and
  recover by themselves when it comes back.
- Entities left behind by older versions (for example lights created for
  shutters) are removed.

### Added
- **Re-authentication**: when HomiSmart stops accepting the saved password,
  Home Assistant asks for the new one.
- **Two-gang switches** are grouped as one physical switch with a child device
  per gang (Home Assistant's new child devices). Existing gang devices are
  converted in place, so their IDs, areas and automations are kept.
- Devices deleted from the HomiSmart account are removed from Home Assistant.
- Diagnostics download, with credentials redacted.
- Brand icon (the HomiSmart logo), a Marketplace category
  (`hubs_protocols.smart_home_hubs`), and translated setup messages.
- Clearer device models (Light switch, Socket, Shutter, Two-gang switch,
  Water heater switch).

### Changed
- Built for Home Assistant 2026.11: devices hang off the hub through
  `via_device_id`, data lives in `entry.runtime_data`, setup and unload return
  `None`, and entities support in-place entity ID changes.
- Tests run in a real Home Assistant with the official `pytest-homeassistant`
  package, and in CI on every push.
