import os
import json
from collections import Counter
from typing import List, Dict, Optional
from data.pokedex import get_pokemon_data, get_roles
from core.duel_simulator import simulate_multi_turn_duel, is_valid_set
from core.metagame_analyzer import load_metagame_data

# === Constantes ===
RESULT_PATH = "data/results/final_sets/"
LOG_PATH = "data/results/set_logs/"
SYNERGY_PATH = "data/results/synergy_result.json"

os.makedirs(RESULT_PATH, exist_ok=True)
os.makedirs(LOG_PATH, exist_ok=True)

# === Moves imposés par rôle ===
ROLE_FORCED_MOVES = {
    "hazard_setter": ["stealth rock", "toxic spikes", "spikes"],
    "setup_sweeper": ["swords dance", "calm mind", "dragon dance", "nasty plot"],
    "pivot": ["u-turn", "volt switch", "flip turn"],
    "status_spreader": ["will-o-wisp", "toxic", "thunder wave"]
}

# === Fonctions ===
def get_forced_moves(roles: List[str], legal_moves: List[str]) -> List[str]:
    forced = []
    for role in roles:
        for move in ROLE_FORCED_MOVES.get(role, []):
            if move in legal_moves:
                forced.append(move)
    return list(set(forced))  # unique

def choose_best_set(name: str, threats: List[str], duel_log: dict) -> dict:
    """Choisit le set ayant le plus de wins contre les menaces."""
    sets = duel_log.get(name, {})
    counter = Counter()

    for threat in threats:
        verdict = sets.get(threat)
        if verdict == "✅ Win":
            counter[(name, threat)] += 1

    return {"win_count": sum(counter.values()), "beats": list(counter.keys())}

def adjust_moves(original_moves: List[str], forced_moves: List[str], duel_targets: List[str], move_effectiveness: Dict[str, int]) -> List[str]:
    moves = list(original_moves)
    for forced in forced_moves:
        if forced not in moves:
            # Remplacer le move le moins utile contre les cibles
            if len(moves) < 4:
                moves.append(forced)
            else:
                least_valuable = min(moves, key=lambda m: move_effectiveness.get(m, 0))
                moves.remove(least_valuable)
                moves.append(forced)
    return moves

def optimize_spread(pkmn_name: str, move_set: List[str], threats: List[str], duel_log: dict) -> dict:
    """
    Détermine la nature + EVs à affecter : vitesse, offensive, bulk.
    (Logique simplifiée ici)
    """
    log = []
    base_data = get_pokemon_data(pkmn_name)
    from data.pokedex import get_base_stats

    base_stats = base_data.get("base_stats") or get_base_stats(pkmn_name)
    if not base_stats:
        raise ValueError(f"❌ Statistiques de base introuvables pour {pkmn_name}")
    offense = "atk" if base_stats["atk"] > base_stats["spa"] else "spa"
    speed = base_stats["spe"]

    log.append(f"🧠 Profil offensif détecté : {offense.upper()}")
    log.append(f"⚡ Vitesse de base : {speed}")

    # Hypothèse : on bat les menaces par vitesse → on investit
    wins_by_speed = 0
    for target, verdict in duel_log.get(pkmn_name, {}).items():
        if verdict == "✅ Win":
            wins_by_speed += 1  # simplification

    evs = {"hp": 0, "atk": 0, "spa": 0, "def": 0, "spd": 0, "spe": 0}
    evs[offense] = 252
    evs["spe"] = 252
    evs["hp"] = 4
    nature = "Jolly" if offense == "atk" else "Timid"

    log.append(f"🎯 Attribution de nature : {nature}")
    log.append(f"📊 Répartition des EVs : {evs}")

    return {
        "evs": evs,
        "ivs": {stat: 31 for stat in evs},
        "nature": nature,
        "log": log
    }

def build_set(pkmn_name: str, threats: List[str], duel_log: dict, roles: List[str]) -> Dict:
    data = get_pokemon_data(pkmn_name)
    legal_moves = data.get("moves", [])
    forced = get_forced_moves(roles, legal_moves)

    best_set_data = choose_best_set(pkmn_name, threats, duel_log)
    set_moves = legal_moves[:4]  # fallback
    move_effectiveness = Counter()

    for threat in threats:
        if verdict := duel_log.get(pkmn_name, {}).get(threat):
            for move in legal_moves:
                if move.lower() in threat.lower():
                    move_effectiveness[move] += 1

    moves = adjust_moves(set_moves, forced, threats, move_effectiveness)
    spread_info = optimize_spread(pkmn_name, moves, threats, duel_log)

    return {
        "name": pkmn_name,
        "moves": moves,
        "ability": data.get("ability1", "???"),
        "item": "Booster Energy",  # logique future
        "tera_type": "???",
        **spread_info
    }, spread_info["log"]

def generate_all_sets() -> None:
    with open(SYNERGY_PATH, encoding="utf-8") as f:
        synergy = json.load(f)

    core = synergy["core"]
    threats = synergy["duels"]
    duel_log = synergy["duels"]
    log_all = {}

    for poke in core:
        roles = get_roles(poke)
        set_data, log_lines = build_set(poke, list(duel_log.get(poke, {}).keys()), duel_log, roles)

        # Sauvegarde
        with open(os.path.join(RESULT_PATH, f"{poke.replace(' ', '_')}_set.json"), "w", encoding="utf-8") as f:
            json.dump(set_data, f, indent=2)

        with open(os.path.join(LOG_PATH, f"{poke.replace(' ', '_')}_log.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

        print(f"✅ Set généré pour {poke}")

def generate_single(pkmn_name: str):
    # Fallback si pas de synergy
    meta = load_metagame_data()
    data = get_pokemon_data(pkmn_name)
    threats = list(meta.keys())[:5]  # top 5 menaces génériques
    fake_log = {pkmn_name: {th: "✅ Win" for th in threats}}  # simule victoire

    roles = get_roles(pkmn_name)
    set_data, log_lines = build_set(pkmn_name, threats, fake_log, roles)

    with open(os.path.join(RESULT_PATH, f"{pkmn_name.replace(' ', '_')}_set.json"), "w", encoding="utf-8") as f:
        json.dump(set_data, f, indent=2)

    with open(os.path.join(LOG_PATH, f"{pkmn_name.replace(' ', '_')}_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"✅ Set unique généré pour {pkmn_name}")

# === CLI ===
if __name__ == "__main__":
    import sys
    if os.path.exists(SYNERGY_PATH):
        print("📥 Fichier synergy détecté → génération de sets complète.")
        generate_all_sets()
    elif len(sys.argv) >= 2:
        name = sys.argv[1]
        generate_single(name)
    else:
        print("❌ Usage : python -m core.set_generator <Pokemon>")
