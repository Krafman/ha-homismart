"""Constants for the HomiSmart integration."""

# The domain of the integration.
DOMAIN = "homismart"

# The platforms to be set up.
PLATFORMS = ["light", "cover", "switch"]

# Signals for the dispatcher.
SIGNAL_NEW_LIGHT = "homismart_new_light"
SIGNAL_NEW_COVER = "homismart_new_cover"
SIGNAL_NEW_SWITCH = "homismart_new_switch"
SIGNAL_UPDATE_DEVICE = "homismart_update"
