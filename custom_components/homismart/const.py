"""Constants for the HomiSmart integration."""
from homeassistant.const import Platform

DOMAIN = "homismart"
MANUFACTURER = "HomiSmart"

PLATFORMS = [Platform.COVER, Platform.LIGHT, Platform.SWITCH]

SIGNAL_UPDATE_DEVICE = "homismart_update_{}"
SIGNAL_NEW_DEVICE = "homismart_new_{}"
