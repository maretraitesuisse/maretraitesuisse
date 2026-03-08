import time
from collections import defaultdict, deque

RATE_LIMIT_STORAGE = defaultdict(deque)

def is_rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    q = RATE_LIMIT_STORAGE[key]

    # supprimer les requêtes trop anciennes
    while q and q[0] <= now - window_seconds:
        q.popleft()

    # trop de requêtes
    if len(q) >= limit:
        return True

    # ajouter la requête actuelle
    q.append(now)
    return False