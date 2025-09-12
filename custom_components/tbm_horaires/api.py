# api.py
import httpx
import unicodedata
from typing import Any, Dict, List, Tuple

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").casefold()

def _text(v):
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

def _get_ref(obj: Any) -> str:
    if isinstance(obj, dict):
        v = obj.get("value")
        return v if isinstance(v, str) else ""
    return obj if isinstance(obj, str) else ""

def _get_name(sn: Any) -> str:
    # "StopName": [{"value":"...","lang":"fr"}] ou dict {"value":"..."} ou string
    if isinstance(sn, list) and sn:
        x = sn[0]
        if isinstance(x, dict):
            return x.get("value") or ""
        if isinstance(x, str):
            return x
    if isinstance(sn, dict):
        return sn.get("value") or ""
    if isinstance(sn, str):
        return sn
    return ""

class SiriLiteClient:
    def __init__(self, session: httpx.AsyncClient, api_base: str, api_key: str):
        self._s = session
        self._base = api_base
        self._key = api_key

    async def lines_map(self) -> Dict[str, Dict[str, str]]:
        """
        Mappe LineRef -> {"published": "...", "name": "...", "mode": "..."} via lines-discovery.
        On stocke aussi la clé 'last' (dernier token après ':') pour faciliter le matching.
        """
        url = f"{self._base}/lines-discovery.json"
        r = await self._s.get(url, params={"AccountKey": self._key}, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        items = (data.get("Siri", {})
                .get("LinesDelivery", {})
                .get("AnnotatedLineRef", []))
        m: Dict[str, Dict[str, str]] = {}
        for it in items or []:
            ref = _text(it.get("LineRef"))
            pub = _text(it.get("PublishedLineName")) or _text(it.get("LineName"))
            mode = _text(it.get("TransportMode")) or _text(it.get("ProductCategoryRef"))
            name = _text(it.get("LineName")) or pub
            if ref:
                m[ref] = {"published": pub, "name": name, "mode": mode, "last": ref.split(":")[-1]}
        # index supplémentaires par dernier token pour rattraper certains refs
        for ref, v in list(m.items()):
            last = v["last"]
            if last and last not in m:
                m[last] = v
            alias = f"line:{last}"
            if alias not in m:
                m[alias] = v
        return m

    async def stoppoints_search(self, query: str, bbox: Tuple[float,float,float,float]) -> List[Dict[str, Any]]:
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

        qn = _norm(query)
        results = []
        for it in items:
            name = _get_name(it.get("StopName"))
            ref = _get_ref(it.get("StopPointRef"))
            if name and ref and qn in _norm(name):
                results.append({"name": name, "ref": ref})
        return results
    
    async def stop_monitoring(
        self,
        monitoring_ref: str,
        line_ref: str | None = None,
        destination_ref: str | None = None,
        preview: str = "PT40M",
        max_visits: int = 8
    ) -> List[Dict[str, Any]]:
        url = f"{self._base}/stop-monitoring.json"
        params: Dict[str, Any] = {
            "AccountKey": self._key,
            "MonitoringRef": monitoring_ref,
            "PreviewInterval": preview,
            "MaximumStopVisits": max_visits
        }
        if line_ref:
            params["LineRef"] = line_ref
        if destination_ref:
            params["DestinationRef"] = destination_ref

        r = await self._s.get(url, params=params, headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()

        deliveries = (data.get("Siri", {})
                        .get("ServiceDelivery", {})
                        .get("StopMonitoringDelivery", []))

        visits: List[Dict[str, Any]] = []
        for d in deliveries:
            for v in (d.get("MonitoredStopVisit") or []):
                mvj = v.get("MonitoredVehicleJourney") or {}

                # Récupération brute
                line_ref_val = _text(mvj.get("LineRef"))
                line_name = _text(mvj.get("PublishedLineName")) or _text(mvj.get("LineName"))
                call = mvj.get("MonitoredCall") or {}
                destination = (_text(mvj.get("DestinationName")) or
                            _text(call.get("DestinationDisplay")) or
                            _text(mvj.get("DirectionName")) or
                            _text(mvj.get("DestinationRef")))

                aimed = call.get("AimedDepartureTime") or call.get("AimedArrivalTime")
                expected = call.get("ExpectedDepartureTime") or call.get("ExpectedArrivalTime")
                realtime = bool(expected and aimed and expected != aimed)

                visits.append({
                    "line_name": line_name or "",        # peut être vide → on compensera avec lines_map côté flow
                    "line_ref": line_ref_val or "",
                    "destination": destination or "",
                    "aimed": aimed,
                    "expected": expected,
                    "realtime": realtime
                })

        visits.sort(key=lambda x: x["expected"] or x["aimed"] or "")
        return visits