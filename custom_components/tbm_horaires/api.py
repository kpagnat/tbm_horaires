# api.py
import httpx
import unicodedata
from typing import Any, Dict, List, Tuple

import logging
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level="DEBUG")

def to_int(value, default: int = -1) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default

def get_value(v: Any) -> str:
    """Retourne le texte depuis un champ SIRI qui peut être list/dict/str."""
    if isinstance(v, list):
        if not v:
            return ""
        x = v[0]
        if isinstance(x, dict):
            return x.get("value") or x.get("Value") or ""
        if isinstance(x, str):
            return x
        return ""
    if isinstance(v, dict):
        return v.get("value") or v.get("Value") or ""
    if isinstance(v, str):
        return v
    return ""

class SiriLiteClient:
    def __init__(self, session: httpx.AsyncClient, api_base: str, api_key: str):
        self._s = session
        self._base = api_base
        self._key = api_key

    async def get_lines(self) -> Dict[str, Dict[str, str]]:
        url = f"{self._base}/lines-discovery.json"
        r = await self._s.get(url, params={"AccountKey": self._key}, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        items = (data.get("Siri", {})
                .get("LinesDelivery", {})
                .get("AnnotatedLineRef", []))
        found_lines: Dict[str, Dict[str, str]] = {}
        for it in items or []:
            line_ref = get_value(it.get("LineRef"))
            line_name = get_value(it.get("LineName"))

            if line_ref:
                line_code = get_value(it.get("LineCode"))
                destinations = it.get("Destinations")
                for d in (destinations or []):
                    direction_ref = to_int(get_value(d.get("DirectionRef")))
                    place_name = get_value(d.get("PlaceName"))
                    key = f"{line_ref}-{direction_ref}"

                    found_lines[key] = {"LineRef": line_ref, "LineName": line_name, "LineCode": line_code, "Direction": place_name, "DirectionRef": direction_ref}

        # Tri sur LineName
        found_lines_sorted = dict(sorted(found_lines.items(), key=lambda kv: (kv[1].get("LineName") or "")))
        return found_lines_sorted

    async def stoppoints_search(self, target_line_ref: str, direction_ref:int, bbox: Tuple[float,float,float,float]) -> List[Dict[str, Any]]:
        W, N, E, S = bbox
        url = f"{self._base}/stoppoints-discovery.json"
        params = {
            "AccountKey": self._key,
            "BoundingBox.UpperLeft.longitude": W,
            "BoundingBox.UpperLeft.latitude":  N,
            "BoundingBox.LowerRight.longitude": E,
            "BoundingBox.LowerRight.latitude":  S
        }
        r = await self._s.get(url, params=params, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        items = (data.get("Siri", {})
                   .get("StopPointsDelivery", {})
                   .get("AnnotatedStopPointRef", []))

        results = []

        for it in items:
            stop_name = get_value(it.get("StopName"))
            stop_point_ref = get_value(it.get("StopPointRef"))
            stop_area_ref = get_value(it.get("StopAreaRef"))
            lines = it.get("Lines")

            for l in (lines or []):
                line_ref = get_value(l)
                # Ligne trouvée ! Il faut regarder si on est dans la bonne direction grâce au StopPointRef
                if target_line_ref == line_ref:
                    stop_monitor = await self.stop_monitoring(stop_point_ref, target_line_ref, direction_ref, max_visits=1)
                    if len(stop_monitor) > 0:
                        results.append({"StopName": stop_name, "StopPointRef": stop_point_ref, "StopAreaRef": stop_area_ref, "DirectionRef": direction_ref})
                    break

        # Tri sur StopName
        results.sort(key=lambda x: (x.get("StopName") or "").casefold())
        return results
    
    async def stop_monitoring(
        self,
        stop_point_ref: str,
        line_ref: str | None = None,
        direction_ref: int = -1,
        preview: str = "PT40M",
        max_visits: int = 4
    ) -> List[Dict[str, Any]]:
        url = f"{self._base}/stop-monitoring.json"
        params: Dict[str, Any] = {
            "AccountKey": self._key,
            "MonitoringRef": stop_point_ref,
            "PreviewInterval": preview,
            "MaximumStopVisits": max_visits
        }
        if line_ref:
            params["LineRef"] = line_ref
        if direction_ref != -1:
            params["DirectionRef"] = direction_ref

        r = await self._s.get(url, params=params, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()

        deliveries = (data.get("Siri", {})
                        .get("ServiceDelivery", {})
                        .get("StopMonitoringDelivery", []))

        visits: List[Dict[str, Any]] = []
        for d in deliveries:
            for v in (d.get("MonitoredStopVisit") or []):
                
                stop_point_ref = get_value(v.get("MonitoringRef"))
                mvj = v.get("MonitoredVehicleJourney") or {}

                # Récupération brute
                line_ref_val = get_value(mvj.get("LineRef"))
                direction_ref = to_int(get_value(mvj.get("DirectionRef")))
                call = mvj.get("MonitoredCall") or {}
                destination = (get_value(mvj.get("DestinationName")) or get_value(mvj.get("DirectionName")))

                aimed = call.get("AimedDepartureTime") or call.get("AimedArrivalTime")
                expected = call.get("ExpectedDepartureTime") or call.get("ExpectedArrivalTime")
                realtime = bool(expected and aimed and expected != aimed)

                visits.append({
                    "StopPointRef": stop_point_ref,
                    "DirectionRef": direction_ref,
                    "LineRef": line_ref_val or "",
                    "destination": destination or "",      # <- lower
                    "aimed": aimed,                        # <- lower
                    "expected": expected,                  # <- lower
                    "realtime": realtime                   # <- lower
                })

        visits.sort(key=lambda x: x["expected"] or x["aimed"] or "")
        return visits