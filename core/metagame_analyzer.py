import json
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Optional

DATA_PATH = "C:/Users/rapha/Desktop/AI TeamBuilder/data/parsed_metagame.json"

# === Chargement des données ===

def load_metagame_data(path: str = DATA_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# === Fonctions d’accès direct ===

def get_metagame_entry(name: str, data: dict) -> Optional[dict]:
    return data.get(name)

def get_all_pokemon(data: dict) -> List[str]:
    return list(data.keys())

# === Analyses globales ===

def get_most_common_pokemon(data: dict, top_n: int = 10) -> List[Tuple[str, int]]:
    usage = [(name, stats.get("raw_count", 0)) for name, stats in data.items()]
    usage.sort(key=lambda x: x[1], reverse=True)
    return usage[:top_n]

def get_top_threats(data: dict, top_n: int = 10) -> List[Tuple[str, int]]:
    viability = [(name, stats.get("viability_ceiling", 0)) for name, stats in data.items()]
    viability.sort(key=lambda x: x[1], reverse=True)
    return viability[:top_n]

def get_most_common_moves(data: dict, top_n: int = 10) -> List[Tuple[str, float]]:
    move_counter = defaultdict(float)
    for entry in data.values():
        for move, pct in entry.get("moves", {}).items():
            move_counter[move] += pct
    return sorted(move_counter.items(), key=lambda x: -x[1])[:top_n]

def get_most_common_items(data: dict, top_n: int = 10) -> List[Tuple[str, float]]:
    item_counter = defaultdict(float)
    for entry in data.values():
        for item, pct in entry.get("items", {}).items():
            item_counter[item] += pct
    return sorted(item_counter.items(), key=lambda x: -x[1])[:top_n]

def get_most_common_tera_types(data: dict, top_n: int = 10) -> List[Tuple[str, float]]:
    tera_counter = defaultdict(float)
    for entry in data.values():
        for tera, pct in entry.get("tera_types", {}).items():
            tera_counter[tera] += pct
    return sorted(tera_counter.items(), key=lambda x: -x[1])[:top_n]

def get_most_common_teammates(data: dict, top_n: int = 10) -> List[Tuple[str, float]]:
    teammates = defaultdict(float)
    for entry in data.values():
        for name, value in entry.get("teammates", {}).items():
            teammates[name] += value
    return sorted(teammates.items(), key=lambda x: -x[1])[:top_n]

# === Analyses ciblées ===

def get_top_sets(pokemon: str, data: dict, top_n: int = 5) -> List[str]:
    info = data.get(pokemon)
    if not info:
        return []
    spreads = info.get("spreads", {})
    sorted_spreads = sorted(spreads.items(), key=lambda x: x[1], reverse=True)
    return [f"{nature_ev} ({percent:.2f}%)" for nature_ev, percent in sorted_spreads[:top_n]]

def get_top_teammates(pokemon: str, data: dict, top_n: int = 5) -> List[str]:
    info = data.get(pokemon)
    if not info:
        return []
    teammates = info.get("teammates", {})
    sorted_team = sorted(teammates.items(), key=lambda x: x[1], reverse=True)
    return [f"{pkmn} ({percent:.2f}%)" for pkmn, percent in sorted_team[:top_n]]

def get_checks_and_counters(pokemon: str, data: dict, top_n: int = 5) -> List[Tuple[str, str]]:
    info = data.get(pokemon)
    if not info:
        return []
    counters = info.get("checks_counters", [])[:top_n]
    return [(entry["name"], entry["detail"]) for entry in counters]

def detect_common_cores(data: dict, min_pct: float = 15.0, max_depth: int = 3) -> List[List[str]]:
    """Détecte les cores récurrents à 2 ou 3 Pokémon basés sur les co-teammates fréquents."""
    cores = []
    seen = set()

    for pkmn, info in data.items():
        teammates = info.get("teammates", {})
        relevant_mates = [mate for mate, pct in teammates.items() if pct >= min_pct]

        for mate in relevant_mates:
            # Éviter les doublons d’ordre (A,B) == (B,A)
            core2 = tuple(sorted([pkmn, mate]))
            if core2 in seen:
                continue

            # Check si la relation est réciproque
            mate_info = data.get(mate, {})
            mate_teammates = mate_info.get("teammates", {})

            if mate_teammates.get(pkmn, 0) >= min_pct:
                cores.append(list(core2))
                seen.add(core2)

                # Essayer de compléter avec un 3e partenaire
                if max_depth >= 3:
                    for third in relevant_mates:
                        if third == mate:
                            continue
                        third_info = data.get(third, {})
                        third_teammates = third_info.get("teammates", {})
                        if (
                            third_teammates.get(pkmn, 0) >= min_pct and
                            third_teammates.get(mate, 0) >= min_pct
                        ):
                            core3 = tuple(sorted([pkmn, mate, third]))
                            if core3 not in seen:
                                cores.append(list(core3))
                                seen.add(core3)

    return cores

# === Résumé global du méta ===

def summarize_metagame(data: dict) -> dict:
    return {
        "top_pokemon": get_most_common_pokemon(data, top_n=10),
        "top_threats": get_top_threats(data, top_n=10),
        "common_moves": get_most_common_moves(data, top_n=10),
        "common_items": get_most_common_items(data, top_n=10),
        "common_tera_types": get_most_common_tera_types(data, top_n=10),
        "common_cores": get_most_common_teammates(data, top_n=10)
    }

# === Test CLI ===

if __name__ == "__main__":
    data = load_metagame_data()

    print("🔝 Top 10 Pokémon joués :")
    for name, count in get_most_common_pokemon(data):
        print(f"{name} ({count})")

    print("\n⚠️ Menaces majeures (viability ceiling) :")
    for name, score in get_top_threats(data):
        print(f"{name} ({score})")

    print("\n🎯 Moves les plus répandus :")
    for move, pct in get_most_common_moves(data):
        print(f"{move} ({pct:.2f}%)")

    print("\n🛠️ Items fréquents :")
    for item, pct in get_most_common_items(data):
        print(f"{item} ({pct:.2f}%)")

    print("\n🔥 Tera types populaires :")
    for tera, pct in get_most_common_tera_types(data):
        print(f"{tera} ({pct:.2f}%)")

    print("\n🤝 Cores fréquents dans le méta :")
    for teammate, pct in get_most_common_teammates(data):
        print(f"{teammate} ({pct:.2f}%)")

    print("\n🛡️ Counters de Great Tusk :")
    for name, detail in get_checks_and_counters("Great Tusk", data):
        print(f"{name} — {detail}")

    print("\n🔗 Cores fréquents dans le méta :")
    for core in detect_common_cores(data, min_pct=20.0):
        print(" + ".join(core))
