# HomiSmart for Home Assistant

![GitHub release](https://img.shields.io/github/v/release/krafman/ha-homismart)
![Validate](https://github.com/krafman/ha-homismart/actions/workflows/validate.yml/badge.svg)

> ⚠️ **Disclaimer**: This is an unofficial, community-driven integration. It is not affiliated with, authorized, or endorsed by Homismart or its parent company. Use at your own risk — changes to Homismart's API may break functionality without notice.

Control HomiSmart lights, switches, sockets, curtains and shutters from Home Assistant. Built on the [homismart-client](https://github.com/Krafman/homismart-client) library.

## Features

- **Lights** (HomiSmart wall light switches): on/off.
- **Switches** (sockets, water heater switches, and each gang of a two-gang switch): on/off.
- **Covers** (curtains and shutters): open, close, stop and set position.
- **Live updates**: changes made in the HomiSmart app or on the wall show up immediately.
- **Devices that match the hardware**: everything sits under your HomiSmart hub, and the two gangs of a two-gang switch are grouped under one physical switch (each gang can still have its own area).
- **Self-healing connection**: if the connection drops, devices show as unavailable and come back automatically when it reconnects.
- **Password changes**: if HomiSmart stops accepting the saved password, Home Assistant asks you to re-enter it.
- Devices removed from your HomiSmart account are removed from Home Assistant.
- **Diagnostics**: download them from the integration page when reporting a problem (your email and password are redacted).

Requires **Home Assistant 2026.11** or newer.

## Installation

### Marketplace (recommended)

1. Go to **Settings → Marketplace**, open the menu (⋮) and choose **Add from link**.
2. Enter `Krafman/ha-homismart` and choose **Integration**.
3. Install **HomiSmart**. You land straight in its setup.

If you used HACS before Home Assistant 2026.11, there's nothing to do: Home Assistant moved your HACS installs into the Marketplace, and updates keep coming.

### Manual

Copy `custom_components/homismart` into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration** and search for **HomiSmart**.
2. Enter the email and password you use in the HomiSmart app.

Your devices are discovered automatically.

## Notes

- **Cover positions** follow Home Assistant's convention: 0% is closed and 100% is open. (The HomiSmart app counts the other way; the integration converts.) Before version 1.2.0 positions were reversed, so check automations that set a position.
- **Two-gang switches** show as switches. To treat a gang as a light, use **Show as → Light** in the entity's settings.
- This is a cloud integration: it needs internet access to HomiSmart's servers.

## Development

Tests run the real client library against a fake HomiSmart server inside a real Home Assistant, using Home Assistant's own [pytest-homeassistant](https://github.com/home-assistant/core/tree/dev/packages/pytest-homeassistant) package (Python 3.14):

```bash
pip install -r requirements_test.txt
pytest
```

CI also runs the HACS and hassfest checks.

## License

MIT. See [LICENSE](LICENSE).
