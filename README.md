# Home Assistant HomiSmart Integration
![GitHub stars](https://img.shields.io/github/stars/krafman/ha-homismart?style=social)
![GitHub last commit](https://img.shields.io/github/last-commit/krafman/ha-homismart)
[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg?logo=HomeAssistantCommunityStore&logoColor=white)](https://github.com/hacs/integration)


> ⚠️ **Disclaimer**: This is an unofficial, community-driven library. It is not affiliated with, authorized, or endorsed by Homismart or its parent company. Use at your own risk — changes to Homismart's API may break functionality without notice.
This is a Home Assistant integration for HomiSmart devices. It allows you to control your HomiSmart lights, switches, and covers directly from Home Assistant.

## Features
- Lights: Control on/off state of your HomiSmart lights.

- Switches: Control on/off state of your HomiSmart switches and sockets.

- Covers: Control your HomiSmart curtains and shutters, including setting the position.

- Real-time updates: The integration uses a persistent connection to your HomiSmart account to receive real-time updates from your devices.

## Installation
HACS (Home Assistant Community Store)
Go to HACS.

Go to "Integrations".

Click the three dots in the top right and select "Custom repositories".

Add the URL to this repository in the "Repository" field.

Select "Integration" as the category.

Click "ADD".

Find the "Home Assistant HomiSmart Integration" card and click "INSTALL".

Follow the instructions on screen to complete the installation.

Manual Installation
Copy the homismart folder from custom_components in this repository to the custom_components folder in your Home Assistant configuration directory.

Restart Home Assistant.

Configuration
Go to Settings -> Devices & Services.

Click the + ADD INTEGRATION button.

Search for "HomiSmart".

Enter your HomiSmart username and password.

Click Submit.

The integration will automatically discover your HomiSmart devices.

## Supported Devices
This integration supports the following device types:

- Lights

- Covers (Curtains and Shutters)

- Switches (Sockets and Multi-gang switches)

## License
This project is licensed under the MIT License. See the LICENSE file for details.

