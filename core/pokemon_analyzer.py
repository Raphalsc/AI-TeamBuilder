# === Imports ===
from core.metagame_analyzer import (
    load_metagame_data, get_top_threats, detect_common_cores, get_metagame_entry
)
from data.pokedex import (
    get_pokemon_data, get_roles, get_base_stats, get_all_sets, get_types
)
import subprocess
import pprint
import os
import re

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
        "viability_ceiling": meta_data.get("viability_ceiling", None) if meta_data else None,
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
    """Normalise un nom pour matcher le format des fichiers JSON."""
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

import re

def evaluate_duel(log_text: str) -> str:
    if not log_text or "❌" in log_text or "Erreur" in log_text:
        return "unknown"

    def parse_stats_and_moves(text):
        move_data = []
        move_blocks = re.findall(r"⚔️ (.*?): ([\d\.]+)%(?: - ([\d\.]+)%)?", text)
        for move_name, dmg1, dmg2 in move_blocks:
            min_dmg = float(dmg1)
            max_dmg = float(dmg2) if dmg2 else float(dmg1)
            move_data.append((move_name.strip().lower(), min_dmg, max_dmg))

        speed = "spe" in text.lower() or "speed" in text.lower()
        item = re.search(r"\((.*?)\)", text)
        item = item.group(1).lower() if item else ""

        return {
            "speed": speed,
            "item": item,
            "moves": move_data,
            "raw": text.lower()
        }

    blocks = re.split(r"🧪 strategy: ", log_text)
    if len(blocks) < 2:
        return "unknown"

    strat_a = parse_stats_and_moves(blocks[1])
    strat_b = parse_stats_and_moves(blocks[2]) if len(blocks) > 2 else {"moves": []}

    def can_ohko(attacker):
        for name, min_dmg, max_dmg in attacker["moves"]:
            if max_dmg >= 100 and name not in ("tailwind", "protect", "roost", "swords dance", "toxic", "substitute"):
                return True
        return False

    def has_setup_win(attacker):
        has_boost = any("swords dance" in name or "nasty plot" in name for name, _, _ in attacker["moves"])
        strong_hit = any(max_dmg >= 100 for _, _, max_dmg in attacker["moves"])
        return has_boost and strong_hit

    def has_stall_win(attacker, defender):
        has_toxic = any("toxic" in name for name, _, _ in attacker["moves"])
        has_recovery = "roost" in attacker["raw"] or "recover" in attacker["raw"]
        low_taken = all(max_dmg < 50 for _, _, max_dmg in defender["moves"])
        return has_toxic and has_recovery and low_taken

    a_faster = strat_a["speed"] or ("scarf" in strat_a["item"] and not strat_b["speed"])
    b_faster = strat_b["speed"] or ("scarf" in strat_b["item"] and not strat_a["speed"])

    if a_faster and can_ohko(strat_a):
        return "win"
    if b_faster and can_ohko(strat_b):
        return "loss"
    
    # NEW: if attacker can OHKO but no clear speed info
    if can_ohko(strat_a) and not can_ohko(strat_b):
        return "win"
    if can_ohko(strat_b) and not can_ohko(strat_a):
        return "loss"

    if has_setup_win(strat_a):
        return "softwin"
    if has_stall_win(strat_a, strat_b):
        return "softwin"
    if all(max_dmg < 30 for _, _, max_dmg in strat_a["moves"]) and all(max_dmg < 30 for _, _, max_dmg in strat_b["moves"]):
        return "draw"

    return "draw"

def simulate_matchups(name: str, top_n: int = 10) -> dict:
    top_threats = [t for t, _ in get_top_threats(metagame, top_n=top_n)]
    results = {}
    win_details = []

    os.makedirs("data/results", exist_ok=True)
    result_path = f"data/results/{name.lower().replace(' ', '_')}_matchups.txt"

    with open(result_path, "w", encoding="utf-8") as log_file:
        for threat in top_threats:
            if normalize_name(threat) == normalize_name(name):
                continue

            poke_a = normalize_name(name)
            poke_b = normalize_name(threat)

            out1 = call_damage_script(poke_a, poke_b)
            out2 = call_damage_script(poke_b, poke_a)
            verdict1 = evaluate_duel(out1)
            verdict2 = evaluate_duel(out2)

            log_file.write(f"🧪 {name.title()} vs {threat.title()}\n")
            log_file.write(f"{verdict1.upper()} ({name} attacking)\n")
            log_file.write(out1 + "\n\n")
            log_file.write(f"{verdict2.upper()} ({threat} attacking)\n")
            log_file.write(out2 + "\n\n")
            log_file.write("=" * 60 + "\n\n")

            win = (verdict1 == "win" or verdict2 == "loss")
            loss = (verdict1 == "loss" or verdict2 == "win")
            draw = not win and not loss

            results[threat] = {
                "win": win,
                "loss": loss,
                "draw": draw,
                "verdicts": (verdict1, verdict2)
            }

            if win:
                # Parse des noms de sets pour résumé
                set_matches = re.findall(r"🧪 strategy: (.*?) vs strategy: (.*?)\n", out1 + "\n" + out2)
                for set1, set2 in set_matches:
                    win_details.append(f"{set1.strip()} wins against {set2.strip()}")

        # ➕ Ajout du résumé tout en bas du fichier
        log_file.write("\n📊 Résumé des sets gagnants:\n")
        if win_details:
            for line in win_details:
                log_file.write("✔️ " + line + "\n")
        else:
            log_file.write("Aucune victoire nette identifiée via sets.\n")

    return results


# Ajouts dans simulate_vs_cores

def simulate_vs_cores(name: str, min_pct: float = 20.0):
    cores = detect_common_cores(metagame, min_pct=min_pct)
    results = []

    os.makedirs("data/results", exist_ok=True)
    result_path = f"data/results/{normalize_name(name)}_vs_cores.txt"

    with open(result_path, "w", encoding="utf-8") as log_file:
        for core in cores:
            if not any(normalize_name(name) == normalize_name(p) for p in core):
                continue

            core_outcome = []
            losses = []
            wins = []

            log_file.write(f"🧩 Core: {', '.join(core)}\n")

            for mate in core:
                if normalize_name(mate) == normalize_name(name):
                    continue

                attacker = normalize_name(name)
                defender = normalize_name(mate)

                out1 = call_damage_script(attacker, defender)
                out2 = call_damage_script(defender, attacker)
                verdict1 = evaluate_duel(out1)
                verdict2 = evaluate_duel(out2)

                # Log complet
                log_file.write(f"\n🧪 {name.title()} vs {mate.title()}\n")
                log_file.write(f"{verdict1.upper()} ({name} attacking)\n")
                log_file.write(out1 + "\n\n")
                log_file.write(f"{verdict2.upper()} ({mate} attacking)\n")
                log_file.write(out2 + "\n")
                log_file.write("=" * 60 + "\n\n")

                if verdict1 == "win" or verdict2 == "loss":
                    outcome = "✅ Win"
                    wins.append(mate)
                elif verdict1 == "loss" or verdict2 == "win":
                    outcome = "❌ Loss"
                    losses.append(mate)
                elif verdict1 == "draw" or verdict2 == "draw":
                    outcome = "⚖️ Draw"
                else:
                    outcome = "❓ Unknown"

                core_outcome.append((mate, outcome))

            summary_line = f"Résultat global: {len(wins)}W / {len(losses)}L / {len(core_outcome) - len(wins) - len(losses)}D\n"
            log_file.write(summary_line)

            results.append({
                "core": core,
                "outcome": core_outcome,
                "wins": wins,
                "losses": losses
            })

    return results



if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("❌ Utilisation : python -m core.pokemon_analyzer <pokemon>")
        sys.exit(1)

    name = sys.argv[1]
    print(f"📘 Analyse de {name.title()}\n")
    info = analyze_pokemon(name)
    pprint.pprint(info, sort_dicts=False)

    print("\n⚔️ Résumé des matchups :\n")
    matchups = simulate_matchups(name)
    for foe, data in matchups.items():
        verdict = "✅ Win" if data["win"] else "❌ Loss" if data["loss"] else "⚖️ Draw"
        print(f"🆚 {foe}: {verdict} ({data['verdicts'][0]}/{data['verdicts'][1]})")

    print("\n🤝 Matchups contre cores :\n")
    for entry in simulate_vs_cores(name):
        core = entry["core"]
        outcome = entry["outcome"]
        losses = entry["losses"]
        wins = entry["wins"]

        print(f"🧩 Core: {', '.join(core)}")
        for poke, res in outcome:
            print(f"{poke}: {res}")

        if losses:
            print(f"   ❌ Pertes contre : {', '.join(losses)}")
        else:
            winrate = 100 * len(wins) / len(outcome)
            print(f"   ✅ Winrate sur le core : {winrate:.0f}%")
        print()
