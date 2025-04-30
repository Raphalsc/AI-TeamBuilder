import sys
from core.new_pokemon_analyzer import duel_result_summary
from core.metagame_analyzer import load_metagame_data, detect_common_cores
from data.pokedex import get_pokemon_data, get_roles
from collections import Counter
from typing import List

LOG_PATH = "data/results/synergy_core_summary.txt"

metagame = load_metagame_data()
common_cores = detect_common_cores(metagame)
all_pokemon_names = list(metagame.keys())

def get_top_pokemon(n=20):
    return sorted(all_pokemon_names, key=lambda x: metagame[x].get("raw_count", 0), reverse=True)[:n]

def identify_threats(core: List[str], top_n: int, log: List[str]) -> List[str]:
    """Retourne les Pokémon qui battent le plus souvent les membres du core."""
    threats = Counter()
    duel_cache = {}

    top_pokemon = get_top_pokemon(top_n)

    log.append(f"\n🔎 Analyse des menaces dans le top {top_n} Pokémon :")

    for core_mon in core:
        for threat in top_pokemon:
            if threat == core_mon:
                continue
            result = duel_result_summary(threat, core_mon, duel_cache)
            if result.get("verdict") == "✅ Win":
                threats[threat] += 1
                log.append(f" - {threat} bat {core_mon}")

    # Pondération selon raw_count et présence dans des cores
    weighted_threats = Counter()
    for mon, count in threats.items():
        weight = count
        weight += metagame.get(mon, {}).get("raw_count", 0) / 100000  # Fréquence
        weight += sum(mon in core for core in common_cores) * 0.5     # Présence dans des cores
        weighted_threats[mon] = weight

    log.append("\n📊 Menaces pondérées :")
    for mon, score in weighted_threats.most_common():
        log.append(f" - {mon}: {round(score, 2)}")

    return [mon for mon, _ in weighted_threats.most_common()]

def find_best_counter(threats: List[str], core: List[str], used: set, desired_roles: List[str], log: List[str]) -> str:
    duel_cache = {}
    scores = Counter()

    for candidate in all_pokemon_names:
        if candidate in used or candidate in core:
            continue
        if desired_roles and not any(role in get_roles(candidate) for role in desired_roles):
            continue

        score = 0
        for threat in threats:
            result = duel_result_summary(candidate, threat, duel_cache)
            if result.get("verdict") == "✅ Win":
                score += 1
            elif result.get("verdict") == "⚖️ Draw":
                score += 0.5
        if score:
            scores[candidate] = score

    log.append("\n🎯 Candidats (couvrant les menaces et respectant les rôles) :")
    for name, score in scores.most_common(10):
        log.append(f" - {name}: {score} (rôles: {', '.join(get_roles(name))})")

    return scores.most_common(1)[0][0] if scores else None

def build_synergy_core(around: List[str], role_targets: List[List[str]], core_size: int = 3) -> List[str]:
    core = list(around)
    used = set(core)
    log = [f"🌐 Construction d’un core de {core_size} Pokémon autour de : {', '.join(around)}"]

    while len(core) < core_size:
        top_n = 20
        found = False

        while not found and top_n <= 100:
            log.append(f"\n--- Nouvelle itération avec top {top_n} ---")
            threats = identify_threats(core, top_n, log)
            desired_roles = role_targets[len(core)] if len(role_targets) > len(core) else []

            best = find_best_counter(threats, core, used, desired_roles, log)
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

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    print(f"\n📁 Résumé complet écrit dans {LOG_PATH}")
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
