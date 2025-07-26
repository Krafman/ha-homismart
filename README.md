Home Assistant HomiSmart Integration
This is a Home Assistant integration for HomiSmart devices. It allows you to control your HomiSmart lights, switches, and covers directly from Home Assistant.

Features
Lights: Control on/off state of your HomiSmart lights.

Switches: Control on/off state of your HomiSmart switches and sockets.

Covers: Control your HomiSmart curtains and shutters, including setting the position.

Real-time updates: The integration uses a persistent connection to your HomiSmart account to receive real-time updates from your devices.

Installation
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

Supported Devices
This integration supports the following device types:

Lights

Covers (Curtains and Shutters)

Switches (Sockets and Multi-gang switches)

License
This project is licensed under the MIT License. See the LICENSE file for details.

Disclaimer
This is an unofficial integration and is not affiliated with HomiSmart in any way. Use at your own risk.