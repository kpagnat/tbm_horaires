from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN, API_BASE, API_KEY, BBOX, DEFAULT_PREVIEW
import httpx
from .api import SiriLiteClient

import logging
from homeassistant.helpers.selector import (
    SelectSelector, SelectSelectorConfig, SelectSelectorMode, SelectOptionDict
)

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level="DEBUG")

STEP_SELECT_LINE = "select_line_destination"
STEP_SELECT_STOP = "select_stop"
STEP_USER_VALIDATE = "user_validate"
STEP_CREATE_ENTITY = "create_entity"

class TBMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    def __init__(self) -> None:
        self._errors = {}
        
    """Point d'entrée du flow (obligatoire)."""
    async def async_step_user(self, user_input):
        _LOGGER.info("==START TBM integration==")
        return await self.async_step_select_line_destination()

    async def async_step_select_line_destination(self):
        # Affichage de la liste de choix de la ligne + destination
        try:
            async with httpx.AsyncClient(headers={
                "Accept": "application/json",
                "User-Agent": "ha-tbm-horaires/0.1"
            }) as s:
                client = SiriLiteClient(s, API_BASE, API_KEY)
                available_lines = await client.get_lines()

        except Exception as e:
            _LOGGER.exception("Lecture des lignes + destination TBM HTTP error: %s", e)
            return self.async_abort(reason="cannot_connect")

        if available_lines is None:
            return self.async_abort(reason="Aucune ligne trouvée")

        # Constructions de la liste des lignes + destinations
        self._lines_map = {}  # garde la liste complète
        options = []
        for idx, (key, value) in enumerate(available_lines.items()):
            label = f'{value["LineName"]} - {value["Direction"]}'
            options.append(SelectOptionDict(value=key, label=label))
            self._lines_map[key] = value

        # Puis on affiche le formulaire avec le dropdown des choix possibles
        return self.async_show_form(
            step_id=STEP_SELECT_STOP,
            data_schema=vol.Schema({
                vol.Required("select_line"): SelectSelector(SelectSelectorConfig(
                    options=options, mode=SelectSelectorMode.DROPDOWN
                ))
            })
        )

    async def async_step_select_stop(self, user_input):
        # Ici, on récupère le choix de l'utilisateur avec line+destination, il ne manque que l'arrêt
        idx = user_input["select_line"]
        self.user_choice = self._lines_map[idx]

        _LOGGER.info("===USER_CHOICE====")
        _LOGGER.info(self.user_choice)

        try:
            async with httpx.AsyncClient(headers={
                "Accept": "application/json",
                "User-Agent": "ha-tbm-horaires/0.1"
            }) as s:
                client = SiriLiteClient(s, API_BASE, API_KEY)
                stops = await client.stoppoints_search(
                    self.user_choice["LineRef"],
                    self.user_choice["DirectionRef"],
                    bbox=BBOX
                )

        except Exception as e:
            _LOGGER.exception("Lecture des arrêts TBM correspondant à la ligne %s, erreur: %s", self.user_choice["LineName"], e)
            return self.async_abort(reason="cannot_connect")

        # Constructions de la liste des arrêts de la ligne sélectionnée
        # Garde un mapping StopPointRef -> StopName pour l’étape suivante
        self._stops_map = {stop["StopPointRef"]: stop["StopName"] for stop in stops}

        options = [
            SelectOptionDict(value=ref, label=name) for ref, name in self._stops_map.items()
        ]

        return self.async_show_form(
            step_id=STEP_USER_VALIDATE,
            data_schema=vol.Schema({
                vol.Required("select_stop"): SelectSelector(SelectSelectorConfig(
                    options=options, mode=SelectSelectorMode.DROPDOWN
                ))
            })
        )

    async def async_step_user_validate(self, user_input):

        # Ici, on récupère le choix de l'utilisateur (arrêt)
        stop_ref = user_input["select_stop"]

        self.user_choice["StopPointRef"] = stop_ref
        self.user_choice["StopName"] = self._stops_map.get(stop_ref, stop_ref)

        stop_name = self.user_choice["StopName"]
        line_name = self.user_choice["LineName"]
        dest_name = self.user_choice["Direction"]

        self.user_choice["Title"] = f"{line_name} > {dest_name} - {stop_name}"

        return self.async_show_form(
            step_id=STEP_CREATE_ENTITY,
            data_schema=vol.Schema({
                vol.Optional("title", default=(self.user_choice["Title"])): str
            })
        )

    async def async_step_create_entity(self, user_input):

        _LOGGER.info("===USER_CHOICE====")
        _LOGGER.info(self.user_choice)

        title = user_input["title"]

        stop_point_ref = self.user_choice["StopPointRef"]
        line_ref = self.user_choice["LineRef"]
        destination_ref = self.user_choice["DirectionRef"]
        stop_name = self.user_choice["StopName"]
        line_name = self.user_choice["LineName"]
        dest_name = self.user_choice["Direction"]

        data = {
            "stop_point_ref": stop_point_ref,
            "line_ref": line_ref,
            "destination_ref": destination_ref,
            "stop_label": stop_name,
            "line_label": line_name,
            "dest_label": dest_name,
            "preview": DEFAULT_PREVIEW
        }
        await self.async_set_unique_id(f"{stop_name}-{line_name}-{dest_name}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=data)
