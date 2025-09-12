from __future__ import annotations

from datetime import datetime, timezone
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _mins_to(iso_ts: str | None) -> int | None:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return max(0, int((dt - datetime.now(timezone.utc)).total_seconds() // 60))
    except Exception:
        return None


class TBMNextPassageSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:train"

    def __init__(self, coordinator, name: str, stop_label: str, line_label: str, dest_label: str) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._stop = stop_label
        self._line = line_label
        self._dest = dest_label
        self._attr_unique_id = f"{DOMAIN}_{name}".lower().replace(" ", "_")

    @property
    def native_value(self):
        data = self.coordinator.data or []
        if not data:
            return None
        first = data[0]
        minutes = _mins_to(first.get("expected") or first.get("aimed"))
        return f"{minutes} min" if minutes is not None else None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or []
        departures = []
        for v in data[:8]:
            minutes = _mins_to(v.get("expected") or v.get("aimed"))
            departures.append(
                {
                    "in_min": minutes,
                    "destination": v.get("destination"),
                    "line_name": v.get("line_name"),
                    "realtime": v.get("realtime"),
                    "time_expected": v.get("expected") or v.get("aimed"),
                }
            )
        return {
            "stop": self._stop,
            "line": self._line,
            "destination": self._dest,
            "departures": departures,
        }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add_entities: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]

    def _short_line(lbl: str) -> str:
        import re
        if not lbl:
            return ""
        m = re.search(r'([A-Z]{1,3}|\d{1,3})$', lbl.strip(), re.IGNORECASE)
        return m.group(1).upper() if m else lbl.strip()

    line_code = _short_line(entry.data.get("line_label") or "")
    stop = entry.data["stop_label"]
    dest = entry.data["dest_label"]
    name = f"TBM {line_code} {stop} {dest}".strip()

    add_entities(
        [
            TBMNextPassageSensor(
                coord,
                name,
                entry.data["stop_label"],
                entry.data["line_label"],
                entry.data["dest_label"],
            )
        ],
        update_before_add=True,
    )
