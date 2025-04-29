import sys
from core.new_pokemon_analyzer import duel_result_summary, analyze_pokemon
from core.metagame_analyzer import load_metagame_data, detect_common_cores
from data.pokedex import get_pokemon_data, get_roles
from collections import Counter
from typing import List, Dict

metagame = load_metagame_data()
all_pokemon_names = list(metagame.keys())
LOG_PATH = "data/results/synergy_core_summary.txt"

def normalize(name: str) -> str:
    return name.lower().replace("-", "").replace(" ", "")

def get_most_relevant_threats(pokemon_list: List[str], log_lines: List[str]) -> List[str]:
    all_threats = Counter()
    cores = detect_common_cores(metagame)

    for name in pokemon_list:
        info = analyze_pokemon(name)
        raw_counters = info.get("meta", {}).get("counters", [])
        counters = [entry.split()[0] for entry in raw_counters]

        log_lines.append(f"\n🛡️ Menaces identifiées pour {name} : {', '.join(counters)}")

        for threat in counters:
            score = 1.0

            # 🔹 Pondération 1 : fréquence dans le metagame
            if threat in metagame:
                score += metagame[threat].get("raw_count", 0) / 100000  # normalisation

            # 🔹 Pondération 2 : présence dans des cores avec d'autres threats ou pokés très joués
            score += sum(threat in core for core in cores) * 0.5

            all_threats[threat] += score

    log_lines.append(f"\n📊 Menaces combinées pondérées :")
    for name, score in all_threats.most_common():
        log_lines.append(f"- {name}: {round(score, 2)}")

    return [t for t, _ in all_threats.most_common()]


def get_best_counters(threats: List[str], current_core: List[str], used: set, log_lines: List[str]) -> List[str]:
    scores = Counter()
    duel_cache = {}

    for candidate in all_pokemon_names:
        if candidate in used or candidate in current_core:
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

    log_lines.append(f"\n📈 Candidats ayant battu le plus de menaces :")
    for name, score in scores.most_common(15):
        log_lines.append(f"- {name}: {score}")

    return [name for name, _ in scores.most_common()]

def matches_desired_roles(name: str, desired_roles: List[str]) -> bool:
    roles = get_roles(name)
    return any(role.lower() in roles for role in desired_roles)

def build_core(around: List[str], roles: List[List[str]], core_size: int = 3) -> List[Dict]:
    core = list(around)
    full_team = [get_pokemon_data(p) for p in core]
    used = set(core)
    log_lines = [f"🎯 Construction d’un core de {core_size} Pokémon autour de {', '.join(around)}"]

    while len(core) < core_size:
        threats = get_most_relevant_threats(core, log_lines)
        candidates = get_best_counters(threats, core, used, log_lines)

        index = len(core)
        if index >= len(roles):
            log_lines.append(f"\n🚫 Aucun rôle défini pour le slot #{index+1}, arrêt.")
            break

        for name in candidates:
            if matches_desired_roles(name, roles[index]):
                core.append(name)
                full_team.append(get_pokemon_data(name))
                used.add(name)
                log_lines.append(f"\n✅ Ajouté au core : {name} (rôle(s) visé(s) : {', '.join(roles[index])})")
                break
        else:
            log_lines.append(f"\n❌ Aucun bon candidat trouvé pour le rôle(s) {roles[index]}")
            break

    log_lines.append("\n🏁 Core final :")
    for mon in core:
        log_lines.append(f" - {mon}")

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"\n📁 Résumé complet écrit dans {LOG_PATH}")
    return full_team

# === Interface CLI corrigée ===
if __name__ == "__main__":
    if "--roles" not in sys.argv:
        print("❌ Usage : python -m core.synergy_calculator <core_size> <poke1> <poke2> ... --roles <role_n> ...")
        print("💡 Exemple : python -m core.synergy_calculator 4 Iron_Valiant Great_Tusk --roles aucun special_sweeper")
        sys.exit(1)

    split_idx = sys.argv.index("--roles")
    if split_idx < 3:
        print("❌ Pas assez d'informations sur les Pokémon fixés.")
        sys.exit(1)

    try:
        core_size = int(sys.argv[1])
    except ValueError:
        print("❌ Le premier argument doit être un entier (taille du core).")
        sys.exit(1)

    around = [arg.replace("_", " ") for arg in sys.argv[2:split_idx]]
    role_args = sys.argv[split_idx + 1:]

    if len(around) + len(role_args) != core_size:
        print("❌ Incohérence entre le nombre de Pokémon fixés et la taille totale du core.")
        print("💡 Exemple : 4 Iron_Valiant Great_Tusk --roles aucun special_sweeper")
        sys.exit(1)

    roles = []
    for role in role_args:
        if role.lower() == "aucun":
            roles.append([])
        else:
            roles.append(role.split(","))

    build_core(around=around, roles=roles, core_size=core_size)
