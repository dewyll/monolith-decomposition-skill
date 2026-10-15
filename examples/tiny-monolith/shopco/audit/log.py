import json
from datetime import datetime

TRAIL = []


def record(event, payload):
    TRAIL.append({"at": datetime.utcnow().isoformat(), "event": event, "payload": json.dumps(payload)})
