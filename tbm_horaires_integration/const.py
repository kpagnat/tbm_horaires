DOMAIN = "tbm_horaires"
API_BASE = "https://bdx.mecatran.com/utw/ws/siri/2.0/bordeaux"
API_KEY  = "opendata-bordeaux-metropole-flux-gtfs-rt"  # clé publique doc officielle
# Bounding box large autour de Bordeaux (W, N, E, S):
BBOX = (-0.81, 45.10, -0.35, 44.70)
DEFAULT_PREVIEW = "PT90M"  # fenêtre pour prochains passages
DEFAULT_INTERVAL_SEC = 60