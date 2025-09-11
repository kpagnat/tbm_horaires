from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN, API_BASE, API_KEY, BBOX, DEFAULT_PREVIEW
import httpx
from .api import SiriLiteClient

import logging, re
from homeassistant.helpers.selector import (
    SelectSelector, SelectSelectorConfig, SelectSelectorMode, SelectOptionDict
)
import asyncio

_LOGGER = logging.getLogger(__name__)

STEP_USER = "user"
STEP_PICK = "pick"
STEP_FILTER = "filter"

def _short_code(ref: str) -> str:
    m = re.search(r'(\d+)(?!.*\d)', ref or '')
    return m.group(1) if m else ref

def _make_label(name: str, ref: str) -> str:
    return f"{name} [{_short_code(ref)}]"

def _short_line_from_name(line_name: str) -> str:
    """'Tram B' -> 'B', 'Lianes 7'/'Principale 27' -> '7'/'27', 'Bato 3' -> '3'."""
    if not line_name:
        return ""
    m = re.search(r'([A-Z]{1,3}|\d{1,3})$', line_name.strip(), re.IGNORECASE)
    return m.group(1).upper() if m else line_name.strip()

def _best_code(line_name: str, line_ref: str, lines_map: dict) -> str:
    """Choisit le meilleur code affichable (évite 'LOC')."""
    # 1) Si le nom publié donne un code propre (B, 27, 430...), on prend
    code = _short_line_from_name(line_name)
    if code and code != line_name and code.upper() != "LOC":
        return code
    # 2) Sinon, on tente le mapping via lines-discovery
    if line_ref:
        cand = [line_ref, line_ref.split(":")[-1], f"line:{line_ref.split(':')[-1]}"]
        for k in cand:
            if k in lines_map:
                pub = lines_map[k].get("published") or lines_map[k].get("name")
                code2 = _short_line_from_name(pub or "")
                if code2 and code2.upper() != "LOC":
                    return code2
    # 3) Dernier recours : si line_name non vide mais égal 'LOC', on renvoie vide pour forcer le fallback
    return ""  # on laissera le fallback "Nom [id]"

async def _label_for_stop(client, ref: str, fallback_label: str, lines_map: dict) -> str:
    """Renvoie 'CODE - Destination' d'après le 1er passage ; sinon fallback."""
    try:
        # 1) proche temps réel
        visits = await client.stop_monitoring(ref, preview="PT10M", max_visits=2)
        if not visits:
            # 2) creux/soirée
            visits = await client.stop_monitoring(ref, preview="PT90M", max_visits=1)
        if not visits:
            # 3) nuit → on va chercher jusqu'à demain matin (~20h)
            visits = await client.stop_monitoring(ref, preview="PT20H", max_visits=1)

        if visits:
            v0 = visits[0]
            code = _best_code(v0.get("line_name") or "", v0.get("line_ref") or "", lines_map)
            dest = (v0.get("destination") or "").strip()
            if code and dest:
                return f"{code} - {dest}"
    except Exception as e:
        _LOGGER.debug("Label probe failed for %s: %s", ref, e)
    return fallback_label

class TBMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_USER,
                data_schema=vol.Schema({vol.Required("stop_query"): str})
            )

        try:
            async with httpx.AsyncClient(headers={
                "Accept": "application/json",
                "User-Agent": "ha-tbm-horaires/0.1"
            }) as s:
                client = SiriLiteClient(s, API_BASE, API_KEY)
                items = await client.stoppoints_search(user_input["stop_query"], BBOX)

                if not items:
                    return self.async_abort(reason="no_stops_found")
                
                # Mapping des lignes pour convertir LineRef -> code court (B, 27, 430...)
                try:
                    lines_map = await client.lines_map()
                except Exception as e:
                    _LOGGER.debug("lines_map failed, fallback to empty map: %s", e)
                    lines_map = {}

                # Conserver le nom d'arrêt pour le titre par défaut plus tard
                self._stop_names = {it["ref"]: it["name"] for it in items}

                # Fallbacks "Nom [id]"
                fallbacks = {it["ref"]: _make_label(it["name"], it["ref"]) for it in items}

                # En parallèle : 1 mini stop-monitoring par quai pour produire "CODE - Destination"
                tasks = [
                    _label_for_stop(client, it["ref"], fallbacks[it["ref"]], lines_map)
                    for it in items
                ]
                labels = await asyncio.gather(*tasks)

        except httpx.HTTPStatusError as e:
            _LOGGER.exception("TBM stops discovery HTTP error: %s", e)
            if e.response.status_code in (401, 403):
                return self.async_abort(reason="auth_failed")
            return self.async_abort(reason="cannot_connect")
        except Exception as e:
            _LOGGER.exception("TBM stops discovery unexpected error: %s", e)
            return self.async_abort(reason="unknown")

        # Construire les options avec les labels enrichis
        options = []
        self._stops_cache = {}
        for it, label in zip(items, labels):
            ref = it["ref"]
            options.append(SelectOptionDict(value=ref, label=label))
            self._stops_cache[ref] = label

        return self.async_show_form(
            step_id=STEP_PICK,
            data_schema=vol.Schema({
                vol.Required("monitoring_ref"): SelectSelector(SelectSelectorConfig(
                    options=options, mode=SelectSelectorMode.DROPDOWN
                ))
            })
        )

    async def async_step_pick(self, user_input):
        self._monitoring_ref = user_input["monitoring_ref"]
        try:
            async with httpx.AsyncClient(headers={
                "Accept": "application/json",
                "User-Agent": "ha-tbm-horaires/0.1"
            }) as s:
                client = SiriLiteClient(s, API_BASE, API_KEY)
                visits = await client.stop_monitoring(self._monitoring_ref, preview=DEFAULT_PREVIEW, max_visits=30)
                if not visits:
                    visits = await client.stop_monitoring(self._monitoring_ref, preview="PT12H", max_visits=30)

        except httpx.HTTPStatusError as e:
            _LOGGER.exception("TBM stop-monitoring HTTP error: %s", e)
            if e.response.status_code in (401, 403):
                return self.async_abort(reason="auth_failed")
            return self.async_abort(reason="cannot_connect")
        except Exception as e:
            _LOGGER.exception("TBM stop-monitoring unexpected error: %s", e)
            return self.async_abort(reason="unknown")


        # mapping lignes/destinations
        try:
            async with httpx.AsyncClient(headers={
                "Accept": "application/json",
                "User-Agent": "ha-tbm-horaires/0.1"
            }) as s2:
                client2 = SiriLiteClient(s2, API_BASE, API_KEY)
                lines_map = await client2.lines_map()
        except Exception as e:
            _LOGGER.debug("lines_map (pick) failed: %s", e)
            lines_map = {}

        lines = {}
        for v in visits or []:
            code = _best_code(v.get("line_name") or "", v.get("line_ref") or "", lines_map) or (v.get("line_name") or "*")
            dest = (v.get("destination") or "").strip() or "*"
            lines.setdefault(code, set()).add(dest)

        # options de ligne (affiche un code lisible)
        line_options = [SelectOptionDict(value=ln, label=ln) for ln in sorted(lines.keys()) if ln != "*"]

        # options de destination (union de toutes les dests trouvées)
        all_dests = sorted({d for ds in lines.values() for d in ds if d and d != "*"})
        default_dest = all_dests[0] if all_dests else "*"

        return self.async_show_form(
            step_id=STEP_FILTER,
            data_schema=vol.Schema({
                vol.Required("line_name"): SelectSelector(SelectSelectorConfig(
                    options=line_options if line_options else [SelectOptionDict(value="*", label="*")],
                    mode=SelectSelectorMode.DROPDOWN
                )),
                vol.Required("destination_name", default=default_dest): SelectSelector(SelectSelectorConfig(
                    options=[SelectOptionDict(value=d, label=d) for d in (all_dests or ["*"])],
                    mode=SelectSelectorMode.DROPDOWN
                )),
                vol.Optional("title", default=(getattr(self, "_stop_names", {}) or {}).get(self._monitoring_ref, "TBM") + (f" - {default_dest}" if default_dest and default_dest != "*" else "")): str
            })
        )

    async def async_step_filter(self, user_input):
        stop_name = (getattr(self, "_stop_names", {}) or {}).get(self._monitoring_ref, "TBM")
        line_name = user_input["line_name"]
        dest_name = user_input["destination_name"]

        # Titre par défaut demandé : "[Nom arrêt] - [Destination]"
        title = f"{stop_name} - {dest_name}" if dest_name and dest_name != "*" else stop_name

        data = {
            "monitoring_ref": self._monitoring_ref,
            "stop_label": stop_name,          # <-- nom d'arrêt pur (plus le label enrichi)
            "line_label": line_name,          # <-- on stocke le code/nom choisi
            "dest_label": dest_name,
            "line_ref": None,
            "destination_ref": None,
            "preview": DEFAULT_PREVIEW
        }
        await self.async_set_unique_id(f"{self._monitoring_ref}-{line_name}-{dest_name}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=data)
