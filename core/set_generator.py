import os
import json
from typing import List, Dict
from collections import Counter

from data.pokedex import get_pokemon_data, get_roles
from core.duel_simulator import simulate_multi_turn_duel, run_damage_calc
from core.metagame_analyzer import load_metagame_data

# === Constantes ===
RESULT_PATH = "data/results/final_sets/"
LOG_PATH = "data/results/set_logs/"
SYNERGY_PATH = "data/results/synergy_result.json"

os.makedirs(RESULT_PATH, exist_ok=True)
os.makedirs(LOG_PATH, exist_ok=True)

ROLE_FORCED_MOVES = {
    "hazard_setter": ["stealth rock", "toxic spikes", "spikes"],
    "setup_sweeper": ["swords dance", "calm mind", "dragon dance", "nasty plot"],
    "pivot": ["u-turn", "volt switch", "flip turn"],
    "status_spreader": ["will-o-wisp", "toxic", "thunder wave"]
}

def get_forced_moves(roles: List[str], legal_moves: List[str]) -> List[str]:
    forced = []
    for role in roles:
        for move in ROLE_FORCED_MOVES.get(role, []):
            if move in legal_moves:
                forced.append(move)
    return list(set(forced))

def count_wins(attacker, movesA, threats: List[Dict]) -> int:
    wins = 0
    for entry in threats:
        result = simulate_multi_turn_duel(attacker, entry["defender"], movesA, entry["moves"])
        if result == "win":
            wins += 1
    return wins

def simulate_duels_against_targets(pokemon_name: str, targets: List[str]) -> List[Dict]:
    """Retourne tous les duels simulables contre les cibles"""
    raw_results = []
    for target in targets:
        try:
            duel_entries = run_damage_calc(pokemon_name, target)
            raw_results.extend([e for e in duel_entries])
        except Exception:
            continue
    return raw_results

def select_best_set(pokemon_name: str, target_list: List[str], log: List[str]):
    duels = simulate_duels_against_targets(pokemon_name, target_list)
    sets_by_id = {}

    for duel in duels:
        key = tuple(duel["moves"])
        sets_by_id.setdefault(key, []).append(duel)

    best_set = None
    best_score = -1

    for move_set, entries in sets_by_id.items():
        attacker = entries[0]["attacker"]
        wins = count_wins(attacker, list(move_set), entries)
        if wins > best_score:
            best_score = wins
            best_set = {
                "set": attacker,
                "moves": list(move_set),
                "wins": wins,
                "entries": entries
            }

    log.append(f"✅ Meilleur set : {best_set['moves']} avec {best_set['wins']} victoires")
    return best_set

def inject_forced_moves(current_moves: List[str], forced_moves: List[str], threat_entries: List[Dict], log: List[str]) -> List[str]:
    effective = Counter()
    for duel in threat_entries:
        for m in duel["moves"]:
            effective[m] += 1

    for fm in forced_moves:
        if fm not in current_moves:
            if len(current_moves) < 4:
                current_moves.append(fm)
                log.append(f"➕ Ajout de {fm} (move requis par rôle)")
            else:
                # remplace move le moins utile
                to_remove = min(current_moves, key=lambda m: effective.get(m, 0))
                log.append(f"♻️ Remplacement : {to_remove} → {fm}")
                current_moves.remove(to_remove)
                current_moves.append(fm)
    return current_moves

def optimize_spread(set_data: Dict, threats: List[Dict], moves: List[str], log: List[str]) -> Dict:
    """Optimise les EVs, nature, etc. selon la manière dont les menaces sont battues"""
    stats = set_data["stats"]
    offense = "atk" if stats["atk"] > stats["spa"] else "spa"
    log.append(f"🧠 Offense principale : {offense.upper()}")

    nature = "Jolly" if offense == "atk" else "Timid"
    evs = {stat: 0 for stat in ["hp", "atk", "def", "spa", "spd", "spe"]}
    evs[offense] = 252
    evs["spe"] = 252
    evs["hp"] = 4

    # Re-simule
    wins = 0
    for duel in threats:
        result = simulate_multi_turn_duel(set_data, duel["defender"], moves, duel["moves"])
        if result == "win":
            wins += 1

    log.append(f"⚙️ Recalcul après EVs : {wins} victoires conservées")
    return {
        "evs": evs,
        "ivs": {k: 31 for k in evs},
        "nature": nature
    }

def build_final_set(poke: str, synergy: Dict) -> (Dict, List[str]):
    log = [f"=== SET POUR {poke.upper()} ==="]
    threats = list(synergy["duels"].get(poke, {}).keys())
    roles = synergy["roles"].get(poke, get_roles(poke))

    legal_data = get_pokemon_data(poke)
    legal_moves = legal_data["moves"]

    forced = get_forced_moves(roles, legal_moves)
    best = select_best_set(poke, threats, log)

    set_data = best["set"]
    moves = inject_forced_moves(best["moves"], forced, best["entries"], log)
    spread = optimize_spread(set_data, best["entries"], moves, log)

    result = {
        "name": poke,
        "moves": moves,
        "ability": set_data["ability"],
        "item": set_data.get("item", "Leftovers"),
        "tera_type": "???",
        **spread
    }
    return result, log

def generate_all_sets():
    with open(SYNERGY_PATH, encoding="utf-8") as f:
        synergy = json.load(f)

    for poke in synergy["core"]:
        final, log_lines = build_final_set(poke, synergy)

        with open(os.path.join(RESULT_PATH, f"{poke.replace(' ', '_')}_set.json"), "w") as f:
            json.dump(final, f, indent=2)

        with open(os.path.join(LOG_PATH, f"{poke.replace(' ', '_')}_log.txt"), "w") as f:
            f.write("\n".join(log_lines))

        print(f"✅ Set final généré pour {poke}")

def generate_single(pokemon_name: str):
    meta = load_metagame_data()
    threats = list(meta.keys())[:5]
    fake_synergy = {
        "core": [pokemon_name],
        "roles": {pokemon_name: get_roles(pokemon_name)},
        "duels": {
            pokemon_name: {t: "✅ Win" for t in threats}
        }
    }
    final, log_lines = build_final_set(pokemon_name, fake_synergy)

    with open(os.path.join(RESULT_PATH, f"{pokemon_name}_set.json"), "w") as f:
        json.dump(final, f, indent=2)

    with open(os.path.join(LOG_PATH, f"{pokemon_name}_log.txt"), "w") as f:
        f.write("\n".join(log_lines))

    print(f"✅ Set final généré pour {pokemon_name} (mono test)")

if __name__ == "__main__":
    import sys
    if os.path.exists(SYNERGY_PATH):
        print("📥 synergy_result.json détecté")
        generate_all_sets()
    elif len(sys.argv) >= 2:
        generate_single(sys.argv[1])
    else:
        print("❌ Usage : python -m core.set_generator <NomPokemon>")
