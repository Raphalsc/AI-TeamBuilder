# === Imports ===
import os
import re
import pprint
import subprocess
from core.metagame_analyzer import (
    load_metagame_data, get_top_threats, detect_common_cores, get_metagame_entry
)
from data.pokedex import (
    get_pokemon_data, get_roles, get_base_stats, get_all_sets, get_types
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(BASE_DIR, "tools", "callDamageFromJSON.mjs")

metagame = load_metagame_data()

def analyze_pokemon(name: str, top_n: int = 10) -> dict:
    poke_data = get_pokemon_data(name)
    meta_data = get_metagame_entry(name, metagame)
    if not poke_data:
        raise ValueError(f"Pokémon non trouvé : {name}")

    analysis = {
        "name": name.title(),
        "types": get_types(name),
        "base_stats": get_base_stats(name),
        "roles": get_roles(name),
        "sets": get_all_sets(name),
        "usage": round(meta_data.get("raw_count", 0) / 1000) if meta_data else 0,
        "viability_ceiling": meta_data.get("viability_ceiling") if meta_data else None,
        "meta": {}
    }

    if meta_data:
        analysis["meta"] = {
            "top_abilities": sorted(meta_data.get("abilities", {}).items(), key=lambda x: -x[1])[:3],
            "top_items": sorted(meta_data.get("items", {}).items(), key=lambda x: -x[1])[:3],
            "top_moves": sorted(meta_data.get("moves", {}).items(), key=lambda x: -x[1])[:5],
            "top_tera_types": sorted(meta_data.get("tera_types", {}).items(), key=lambda x: -x[1])[:3],
            "top_teammates": sorted(meta_data.get("teammates", {}).items(), key=lambda x: -x[1])[:5],
            "counters": [entry["name"] for entry in meta_data.get("checks_counters", [])]
        }

    return analysis

def normalize_name(name: str) -> str:
    return name.lower().replace("-", "").replace(" ", "")

def call_damage_script(poke1: str, poke2: str) -> str:
    try:
        process = subprocess.run(
            ["node", SCRIPT_PATH, poke1, poke2],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        return process.stdout.strip() or process.stderr.strip()
    except Exception as e:
        return f"⛔ Erreur : {str(e)}"

def summarize_duel(log_text: str) -> list[str]:
    blocks = re.findall(r"🧪 strategy: (.*?) vs strategy: (.*?)\n+🔬[^\n]*\n+((?:⚔️ .*?\n)+)", log_text, re.DOTALL)
    summaries = []
    for set1, set2, moves in blocks:
        summaries.append(f"📊 {set1.strip()} vs {set2.strip()}")
        for move_line in moves.strip().split("\n"):
            if match := re.match(r"⚔️ (.*?): ([\d\.]+)% ?-? ?([\d\.]*)", move_line):
                move, min_dmg, max_dmg = match.groups()
                max_dmg = float(max_dmg) if max_dmg else float(min_dmg)
                summaries.append(f"🔹 {move.strip()} → max {max_dmg}%")
        summaries.append("")
    return summaries

def simulate_matchups(name: str, top_n: int = 10) -> dict:
    top_threats = [t for t, _ in get_top_threats(metagame, top_n=top_n)]
    results = {}
    os.makedirs("data/results", exist_ok=True)
    summary_log = open(f"data/results/{normalize_name(name)}_matchups_summary.txt", "w", encoding="utf-8")

    print("\n⚔️ Matchups Résumé:")

    for threat in top_threats:
        if normalize_name(threat) == normalize_name(name):
            continue

        out1 = call_damage_script(normalize_name(name), normalize_name(threat))
        summaries = summarize_duel(out1)

        wins = sum("max 100.0%" in line or float(line.split("max ")[-1][:-1]) >= 100 for line in summaries if "max" in line)
        total = sum(1 for line in summaries if "max" in line)
        winrate = wins / total * 100 if total else 0
        verdict = "✅ Win" if winrate > 50 else "❌ Loss" if winrate < 50 else "⚖️ Draw"

        print(f"🆚 {threat}: {verdict} ({winrate:.0f}% win rate)")
        summary_log.write(f"{name.title()} vs {threat.title()}\n")
        summary_log.writelines(line + "\n" for line in summaries)
        summary_log.write(f"➡️ Résultat: {verdict} ({winrate:.0f}% win rate)\n\n")

        results[threat] = {
            "winrate": winrate,
            "verdict": verdict,
            "details": summaries
        }

    summary_log.close()
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("❌ Utilisation : python -m core.pokemon_analyzer <pokemon>")
        sys.exit(1)

    name = sys.argv[1]
    print(f"\n📘 Analyse de {name.title()}\n")
    info = analyze_pokemon(name)
    pprint.pprint(info, sort_dicts=False)

    simulate_matchups(name)
