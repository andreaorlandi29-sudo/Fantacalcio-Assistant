"""
Connessione Redis condivisa (Render Key Value) per tutti i moduli di storage
del bot (rosa, pareri creator, ecc.).

Variabile d'ambiente REDIS_URL. Per i test locali senza Render: ROSA_FAKE=1
usa un client redis fittizio (fakeredis); in alternativa si puo' iniettare
un client con set_client() (usato dai test).
"""
import os

_client = None


def set_client(client):
    """Inietta un client redis (per i test). In produzione non si usa."""
    global _client
    _client = client


def get_client():
    global _client
    if _client is not None:
        return _client
    if os.environ.get("ROSA_FAKE"):          # solo per test locali
        import fakeredis
        _client = fakeredis.FakeStrictRedis(decode_responses=True)
        return _client
    url = os.environ.get("REDIS_URL")
    if not url:
        raise RuntimeError(
            "Storage non configurato: manca la variabile d'ambiente REDIS_URL. "
            "Collega un Render Key Value (vedi docs/STORAGE_ROSA.md).")
    import redis  # import lazy: il bot parte anche senza redis installato/config
    _client = redis.from_url(url, decode_responses=True)
    return _client
