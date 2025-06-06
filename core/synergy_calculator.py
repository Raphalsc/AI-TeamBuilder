import sys
import json
from core.new_pokemon_analyzer import duel_result_summary
from core.metagame_analyzer import load_metagame_data, detect_common_cores
from data.pokedex import get_roles
from collections import Counter, defaultdict
from typing import List

LOG_PATH = "data/results/synergy_core_summary.txt"
JSON_PATH = "data/results/synergy_result.json"

metagame = load_metagame_data()
common_cores = detect_common_cores(metagame)
all_pokemon_names = list(metagame.keys())

def get_top_pokemon(n=20):
    return sorted(all_pokemon_names, key=lambda x: metagame[x].get("raw_count", 0), reverse=True)[:n]

def identify_threats(core: List[str], top_n: int, duel_cache: dict, log: List[str], duel_log: dict) -> List[str]:
    top_pokemon = get_top_pokemon(top_n)
    beat_all_core = []

    log.append(f"\n🔎 Analyse des menaces dans le top {top_n} Pokémon :")

    for threat in top_pokemon:
        if threat in core:
            continue
        wins = 0
        for target in core:
            duel = duel_result_summary(threat, target, duel_cache)
            verdict = duel.get("verdict")
            duel_log.setdefault(str(threat), {})[str(target)] = verdict
            if verdict == "✅ Win":
                wins += 1

        if len(core) >= 2 and wins == len(core):
            beat_all_core.append(threat)
        elif len(core) < 2 and wins > 0:
            beat_all_core.append(threat)

    log.append(f"\n📊 Menaces conservées (battent {'tout' if len(core) >= 2 else 'au moins un'} le core) :")
    for threat in beat_all_core:
        score = 1.0
        score += metagame[threat].get("raw_count", 0) / 100000
        score += sum(threat in c for c in common_cores) * 0.5
        log.append(f" - {threat} (score approx : {round(score, 2)})")

    return beat_all_core

def find_best_counter(threats: List[str], core: List[str], used: set, desired_roles: List[str], duel_cache: dict, log: List[str], duel_log: dict) -> str:
    scores = Counter()

    for candidate in all_pokemon_names:
        if candidate in used or candidate in core:
            continue
        if desired_roles and not any(role in get_roles(candidate) for role in desired_roles):
            continue

        score = 0
        for threat in threats:
            duel = duel_result_summary(candidate, threat, duel_cache)
            verdict = duel.get("verdict")
            duel_log.setdefault(str(candidate), {})[str(threat)] = verdict
            if verdict == "✅ Win":
                score += 1
            elif verdict == "⚖️ Draw":
                score += 0.5

        if score:
            scores[candidate] = score

    log.append("\n🎯 Candidats (qui couvrent les menaces et respectent les rôles) :")
    for name, sc in scores.most_common(10):
        log.append(f" - {name}: {sc} (rôles: {', '.join(get_roles(name))})")

    return scores.most_common(1)[0][0] if scores else None

def sanitize_keys(obj):
    if isinstance(obj, dict):
        return {str(k): sanitize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_keys(i) for i in obj]
    else:
        return obj

def build_synergy_core(around: List[str], role_targets: List[List[str]], core_size: int = 3) -> List[str]:
    core = list(around)
    used = set(core)
    log = [f"🌐 Construction d’un core de {core_size} Pokémon autour de : {', '.join(around)}"]
    duel_log = {}
    duel_cache = {}

    while len(core) < core_size:
        top_n = 20
        found = False

        while not found and top_n <= 100:
            log.append(f"\n--- Nouvelle itération avec top {top_n} ---")
            threats = identify_threats(core, top_n, duel_cache, log, duel_log)
            desired_roles = role_targets[len(core)] if len(role_targets) > len(core) else []

            best = find_best_counter(threats, core, used, desired_roles, duel_cache, log, duel_log)
            if best:
                core.append(best)
                used.add(best)
                log.append(f"\n✅ Ajouté au core : {best} (rôles visés : {', '.join(desired_roles) or 'aucun'})")
                found = True
            else:
                log.append("⚠️ Aucun bon partenaire trouvé, élargissement du metagame analysé.")
                top_n += 20

        if not found:
            log.append("❌ Arrêt : impossible de compléter le core dans les contraintes actuelles.")
            break

    log.append("\n🏁 Core final :")
    for mon in core:
        log.append(f" - {mon}")

    # Sauvegarde
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "core": core,
            "log": log,
            "duels": sanitize_keys(duel_log)
        }, f, indent=2)

    print(f"\n📁 Résumé complet écrit dans {LOG_PATH}")
    print(f"📦 Données enregistrées dans {JSON_PATH}")
    return core

# === CLI ===
if __name__ == "__main__":
    if "--roles" not in sys.argv:
        print("❌ Usage : python -m core.synergy_calculator <core_size> <poke1> <poke2> ... --roles <role_n> ...")
        print("💡 Exemple : python -m core.synergy_calculator 4 Iron_Valiant --roles aucun physical_wall setup_sweeper")
        sys.exit(1)

    idx = sys.argv.index("--roles")
    core_size = int(sys.argv[1])
    around = [arg.replace("_", " ") for arg in sys.argv[2:idx]]
    role_args = sys.argv[idx + 1:]

    if len(around) + len(role_args) != core_size:
        print("❌ Incohérence entre nombre de Pokémon fixés et rôles fournis.")
        sys.exit(1)

    roles = []
    for role in role_args:
        roles.append([] if role.lower() == "aucun" else role.split(","))

    build_synergy_core(around, roles, core_size)
