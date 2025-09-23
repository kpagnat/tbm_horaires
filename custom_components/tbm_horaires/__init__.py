from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, API_BASE, API_KEY
from .coordinator import TBMCoordinator

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["api_base"] = API_BASE
    hass.data[DOMAIN]["api_key"] = API_KEY

    coord = TBMCoordinator(
        hass,
        name=f"TBM {entry.data['stop_label']} -> {entry.data['dest_label']}",
        stop_point_ref=entry.data["stop_point_ref"],
        line_ref=entry.data["line_ref"],
        destination_ref=entry.data["destination_ref"],
        preview=entry.data["preview"]
    )
    await coord.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coord
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coord = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coord:
        await coord.async_shutdown()
    return unloaded