"""
Azzera la rosa nello storage (Render Key Value).

Uso (in locale con REDIS_URL impostata sull'EXTERNAL connection string del
Key Value, oppure eseguito dove REDIS_URL punta allo storage):
    python3 -m bot.rosa_reset

In alternativa puoi semplicemente scrivere al bot: "resetta la rosa".
"""
from . import rosa_store as store


def main():
    prima = store.stato_rosa()
    print(f"Rosa attuale: {prima['num_giocatori']} giocatori, "
          f"{prima['crediti_spesi']} crediti spesi.")
    store.reset()
    print("OK: rosa azzerata (budget di nuovo pieno, 0 acquisti).")


if __name__ == "__main__":
    main()
