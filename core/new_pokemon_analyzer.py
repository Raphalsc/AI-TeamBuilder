import pprint
from core.metagame_analyzer import (
    load_metagame_data,
    get_metagame_entry,
    get_top_threats,
    detect_common_cores
)
from core.duel_simulator import run_damage_calc, is_valid_set, simulate_multi_turn_duel
from data.pokedex import (
    get_pokemon_data,
    get_roles,
    get_base_stats,
    get_types,
    get_all_sets
)

def normalize(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "")

def duel_result_summary(attacker_name: str, defender_name: str, cache: dict) -> dict:
    a = normalize(attacker_name)
    b = normalize(defender_name)
    key = (a, b)

    if key in cache:
        return cache[key]

    try:
        atk_res = run_damage_calc(a, b)
        def_res = run_damage_calc(b, a)

        results = []
        for atk_entry in atk_res:
            if not is_valid_set(atk_entry):
                continue
            setA = atk_entry['attacker']
            setB = atk_entry['defender']
            movesA = atk_entry['moves']

            mirror = next(
                (r for r in def_res if is_valid_set(r)
                 and r['setNames']['a'] == atk_entry['setNames']['b']
                 and r['setNames']['b'] == atk_entry['setNames']['a']),
                None
            )

            if mirror:
                movesB = mirror['moves']
                verdict = simulate_multi_turn_duel(setA, setB, movesA, movesB)
                results.append(verdict)

        wins = results.count("win")
        losses = results.count("loss")
        draws = results.count("draw")
        total = len(results)
        winrate = 100 * wins / total if total else 0
        summary = {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "winrate": round(winrate, 1),
            "verdict": "✅ Win" if winrate > 50 else "❌ Loss" if winrate < 50 else "⚖️ Draw"
        }
    except Exception as e:
        summary = {"error": str(e)}

    cache[key] = summary
    return summary

def analyze_pokemon(name: str, top_n: int = 10) -> dict:
    normalized = normalize(name)
    meta_data = load_metagame_data()
    poke_data = get_pokemon_data(normalized)
    meta_entry = get_metagame_entry(normalized, meta_data)

    if not poke_data:
        raise ValueError(f"Pokémon non trouvé : {name}")

    analysis = {
        "name": name.title(),
        "types": get_types(normalized),
        "base_stats": get_base_stats(normalized),
        "roles": get_roles(normalized),
        "sets": get_all_sets(normalized),
        "usage": round(meta_entry.get("raw_count", 0) / 1000) if meta_entry else 0,
        "viability_ceiling": meta_entry.get("viability_ceiling") if meta_entry else None,
        "meta": {},
        "matchups": {},
        "core_synergies": [],
        "core_counters": []
    }

    if meta_entry:
        analysis["meta"] = {
            "top_abilities": sorted(meta_entry.get("abilities", {}).items(), key=lambda x: -x[1])[:3],
            "top_items": sorted(meta_entry.get("items", {}).items(), key=lambda x: -x[1])[:3],
            "top_moves": sorted(meta_entry.get("moves", {}).items(), key=lambda x: -x[1])[:5],
            "top_tera_types": sorted(meta_entry.get("tera_types", {}).items(), key=lambda x: -x[1])[:3],
            "top_teammates": sorted(meta_entry.get("teammates", {}).items(), key=lambda x: -x[1])[:5],
            "counters": [entry["name"] for entry in meta_entry.get("checks_counters", [])]
        }

    duel_cache = {}

    # Matchups vs top threats
    top_threats = get_top_threats(meta_data, top_n=top_n)
    for threat, _ in top_threats:
        if normalize(threat) == normalized:
            continue
        analysis["matchups"][threat] = duel_result_summary(normalized, threat, duel_cache)

    # Cores où ce Pokémon est utilisé
    all_cores = detect_common_cores(meta_data, min_pct=15.0)
    analysis["core_synergies"] = [
        core for core in all_cores if normalized in [normalize(x) for x in core]
    ]

    # Cores adverses (où le Pokémon n’est pas présent)
    seen_cores = set()
    for core in all_cores:
        core_key = tuple(sorted(normalize(x) for x in core))
        if normalized in core_key or core_key in seen_cores:
            continue
        seen_cores.add(core_key)

        individual_results = []
        for foe in core:
            if normalize(foe) == normalized:
                continue
            res = duel_result_summary(normalized, foe, duel_cache)
            individual_results.append((foe, res))

        wins = sum(1 for _, r in individual_results if r.get("verdict") == "✅ Win")
        losses = sum(1 for _, r in individual_results if r.get("verdict") == "❌ Loss")
        draws = sum(1 for _, r in individual_results if r.get("verdict") == "⚖️ Draw")
        analysis["core_counters"].append({
            "core": core,
            "summary": {
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "verdict": "✅ Dominates" if wins > losses else "❌ Outmatched" if losses > wins else "⚖️ Even"
            },
            "details": individual_results
        })

    return analysis

# === CLI usage ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("❌ Utilisation : python -m core.pokemon_analyzer <pokemon>")
        sys.exit(1)

    name = sys.argv[1]
    print(f"\n📘 Analyse de {name.title()}...\n")
    result = analyze_pokemon(name)
    pprint.pprint(result, sort_dicts=False)
