import json
import os
import subprocess
from collections import Counter
from typing import Literal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(BASE_DIR, "tools", "callDamageFromJSON.mjs")
DATA_DIR = os.path.join(BASE_DIR, "data", "results")
os.makedirs(DATA_DIR, exist_ok=True)

def normalize(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "")

def is_valid_set(entry: dict) -> bool:
    # Un set valide doit avoir un vrai nom de stratégie
    return (
        isinstance(entry.get('attacker'), dict)
        and isinstance(entry.get('defender'), dict)
        and 'moves' in entry
        and 'name' in entry['attacker']
        and 'name' in entry['defender']
        and entry.get("setNames")  # doit exister pour identifier les sets
        and all(k in entry['setNames'] for k in ("a", "b"))
        and not entry['setNames']['a'].startswith(('type', 'ability', 'format', 'name', 'hidden'))
        and not entry['setNames']['b'].startswith(('type', 'ability', 'format', 'name', 'hidden'))
    )

def run_damage_calc(poke1: str, poke2: str) -> list:
    result = subprocess.run(
        ["node", SCRIPT_PATH, poke1, poke2, "--json"],
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"Erreur Node.js :\n{result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("❌ Sortie invalide JSON.")

def best_move_damage(moves: list[dict]) -> int:
    return max((m['max'] for m in moves if 'max' in m), default=0)

def simulate_multi_turn_duel(setA: dict, setB: dict, movesA: list[dict], movesB: list[dict], max_turns: int = 8) -> Literal['win', 'loss', 'draw']:
    hpA, hpB = setA['hp'], setB['hp']
    speedA, speedB = setA['speed'], setB['speed']

    for _ in range(max_turns):
        dmgA = best_move_damage(movesA)
        dmgB = best_move_damage(movesB)

        if speedA > speedB:
            hpB -= dmgA
            if hpB <= 0:
                return 'win'
            hpA -= dmgB
            if hpA <= 0:
                return 'loss'
        elif speedB > speedA:
            hpA -= dmgB
            if hpA <= 0:
                return 'loss'
            hpB -= dmgA
            if hpB <= 0:
                return 'win'
        else:
            hpB -= dmgA
            hpA -= dmgB
            if hpA <= 0 and hpB <= 0:
                return 'draw'
            elif hpB <= 0:
                return 'win'
            elif hpA <= 0:
                return 'loss'
    return 'draw'

def duel_summary(poke1: str, poke2: str):
    poke1 = normalize(poke1)
    poke2 = normalize(poke2)
    print(f"\n⚔️ Simulation de tous les duels entre {poke1} et {poke2}...")

    try:
        raw_output = run_damage_calc(poke1, poke2)
    except Exception as e:
        print(f"❌ Erreur lors du calcul de dégâts : {e}")
        return

    raw = [entry for entry in raw_output if is_valid_set(entry)]

    if not raw:
        print("⚠️ Aucun set valide trouvé après filtrage. Vérifie le fichier JSON ou les noms des Pokémon.")
        return

    damage_map = {}
    set_pairs = []

    for entry in raw:
        setA = entry['attacker']
        setB = entry['defender']
        key = (entry['setNames']['a'], entry['setNames']['b'])
        damage_map[key] = entry['moves']
        set_pairs.append((setA, setB, key))

    results = []
    for setA, setB, key in set_pairs:
        reverse_key = (key[1], key[0])
        movesA = damage_map[key]
        movesB = damage_map.get(reverse_key)

        if not movesB:
            reverse_raw = [e for e in run_damage_calc(normalize(setB['name']), normalize(setA['name'])) if is_valid_set(e)]
            for r in reverse_raw:
                k = (r['setNames']['a'], r['setNames']['b'])
                damage_map[k] = r['moves']
            movesB = damage_map.get(reverse_key, [])

        verdict = simulate_multi_turn_duel(setA, setB, movesA, movesB)
        results.append((key[0], key[1], verdict))

    counter = Counter(v for _, _, v in results)
    total = len(results)
    print(f"\n📊 Résumé:")
    print(f"{poke1.title()} vs {poke2.title()} :")
    print(f"✅ Wins : {counter['win']} ({100 * counter['win'] // total}%)")
    print(f"🟡 Draws : {counter['draw']} ({100 * counter['draw'] // total}%)")
    print(f"❌ Losses : {counter['loss']} ({100 * counter['loss'] // total}%)")

    path = os.path.join(DATA_DIR, f"{poke1}_vs_{poke2}_summary.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Résumé du duel {poke1} vs {poke2}\n")
        f.write(f"Wins: {counter['win']}\n")
        f.write(f"Draws: {counter['draw']}\n")
        f.write(f"Losses: {counter['loss']}\n\n")
        for a, b, verdict in results:
            f.write(f"{a} vs {b} → {verdict}\n")

    print(f"\n📁 Résumé sauvegardé dans {path}")

if __name__ == '__main__':
    import sys
    try:
        if len(sys.argv) < 3:
            print("❌ Utilisation : python -m core.duel_simulator <pokemon1> <pokemon2>")
            sys.exit(1)
        duel_summary(sys.argv[1], sys.argv[2])
    except Exception as e:
        print(f"🔥 Une erreur inattendue s'est produite : {e}")
