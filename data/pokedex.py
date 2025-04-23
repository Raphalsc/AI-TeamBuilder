import json
import os
import re
from difflib import get_close_matches

POKEDEX_PATH = os.path.join(os.path.dirname(__file__), "pokedex_with_full_moves_and_sets.json")

with open(POKEDEX_PATH, "r", encoding="utf-8") as f:
    pokedex = json.load(f)

# 🔁 Table des types (simplifiée)
TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy"
]

def get_pokemon_data(name: str, suggest: bool = True) -> dict | None:
    name = name.lower()
    if name in pokedex:
        return pokedex[name]

    if suggest:
        matches = get_close_matches(name, pokedex.keys(), n=1, cutoff=0.7)
        if matches:
            return pokedex[matches[0]]
    return None

def list_all_pokemon() -> list[str]:
    return sorted(pokedex.keys())

def get_types(name: str) -> tuple[str, str | None]:
    data = get_pokemon_data(name)
    if data:
        return (data.get("type1", "???"), data.get("type2"))
    return ("???", None)

def get_all_moves(name: str) -> list[str]:
    data = get_pokemon_data(name)
    return data.get("moves", []) if data else []

def has_move(name: str, move: str) -> bool:
    return move.lower() in [m.lower() for m in get_all_moves(name)]

def get_base_stats(name: str) -> dict:
    data = get_pokemon_data(name)
    if not data:
        return {}
    return {
        "hp": data.get("hp", 0),
        "atk": data.get("atk", 0),
        "def": data.get("def", 0),
        "spa": data.get("spa", 0),
        "spd": data.get("spd", 0),
        "spe": data.get("spe", 0)
    }

def get_abilities(name: str) -> list[str]:
    data = get_pokemon_data(name)
    if not data:
        return []
    return list(filter(None, [
        data.get("ability1"),
        data.get("ability2"),
        data.get("hidden ability")
    ]))

def get_all_sets(name: str) -> list[dict]:
    """Parse tous les sets stratégiques connus pour un Pokémon."""
    data = get_pokemon_data(name)
    if not data:
        return []

    sets = []
    for key, value in data.items():
        if not key.startswith("strategy:"):
            continue

        set_data = {
            "name": key.replace("strategy:", "").strip(),
            "raw": value,
            "ability": None,
            "tera_type": None,
            "evs": {},
            "ivs": {},
            "nature": None,
            "item": None,
            "moves": []
        }

        lines = value.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("@"):
                set_data["item"] = line[1:].strip()
            elif line.lower().startswith("ability:"):
                set_data["ability"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("tera type:"):
                set_data["tera_type"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("evs:"):
                ev_parts = line.split(":", 1)[1].strip().split("/")
                for ev in ev_parts:
                    val, stat = ev.strip().split()
                    set_data["evs"][stat.lower()] = int(val)
            elif line.lower().startswith("ivs:"):
                iv_parts = line.split(":", 1)[1].strip().split("/")
                for iv in iv_parts:
                    val, stat = iv.strip().split()
                    set_data["ivs"][stat.lower()] = int(val)
            elif line.lower().endswith("nature"):
                set_data["nature"] = line.replace("Nature", "").strip()
            elif line.startswith("-"):
                move = line[1:].strip().lower()
                set_data["moves"].append(move)

        sets.append(set_data)
    return sets

def get_roles(name: str) -> list[str]:
    data = get_pokemon_data(name)
    if not data:
        return []

    stats = get_base_stats(name)
    moves = get_all_moves(name)
    abilities = get_abilities(name)
    roles = set()

    # 🎯 Offensif (stat + abilité)
    if stats["atk"] >= 100 or "huge power" in abilities or "pure power" in abilities:
        roles.add("physical attacker")
    if stats["spa"] >= 100:
        roles.add("special attacker")

    if stats["spe"] >= 100:
        roles.add("fast")
    elif stats["spe"] <= 60:
        roles.add("slow")

    # 🛡️ Défensif
    bulk_score = stats["hp"] * ((stats["def"] + stats["spd"]) / 2)
    if bulk_score >= 40000:
        roles.add("tank")

    # 💼 Rôles fonctionnels via moves
    if any(m in moves for m in [
        "stealthrock", "spikes", "stickyweb", "toxicspikes"
    ]):
        roles.add("hazard setter")

    if any(m in moves for m in ["defog", "rapidspin", "courtchange"]):
        roles.add("hazard control")

    if any(m in moves for m in ["uturn", "voltswitch", "flipturn"]):
        roles.add("pivot")

    if any(m in moves for m in [
        "swordsdance", "nastyplot", "calmmind", "bulkup", "dragondance", "bellydrum",
        "irondefense", "agility", "quiverdance", "shellsmash", "growth", "curse",
        "victorydance", "takeheart", "clangoroussoul", "tailglow"
    ]):
        roles.add("setup sweeper")

    if any(m in moves for m in ["wish", "lunardance", "healingwish"]):
        roles.add("support")

    if any(m in moves for m in ["reflect", "lightscreen", "auroraveil"]):
        roles.add("screen")

    if any(m in moves for m in ["taunt", "encore", "trick", "switcheroo"]):
        roles.add("utilitaire")

    if any(m in moves for m in [
        "shadowsneak", "iceshard", "bulletpunch", "aquajet",
        "extremespeed", "suckerpunch", "machpunch", "vacuumwave"
    ]):
        roles.add("priority")
    
    if "contrary" in abilities:
        roles.add("setup sweeper")

    if "chillyreception" in moves:
        roles.add("pivot")

    if any(weather in abilities for weather in ["drought", "drizzle", "snowwarning", "sandstream"]):
        roles.add("weather setter")

    return sorted(roles)

def get_tier(name: str) -> str:
    """Retourne le tier Smogon du Pokémon (ex: 'OU', 'UU', etc.)."""
    data = get_pokemon_data(name)
    return data.get("format", "Inconnu") if data else "Inconnu"

def get_type_chart() -> dict:
    """Retourne le tableau des types (efficacités offensives/défensives)."""
    # Source simplifiée mais exacte (Gen 9), peut être étendue si besoin
    chart = {
        "normal":   {"offensive": ["ghost"], "weak": ["fighting"], "resist": [], "immune": ["ghost"]},
        "fire":     {"offensive": ["grass", "ice", "bug", "steel"], "weak": ["water", "rock", "ground"], "resist": ["fire", "grass", "ice", "bug", "steel", "fairy"], "immune": []},
        "water":    {"offensive": ["fire", "rock", "ground"], "weak": ["electric", "grass"], "resist": ["fire", "water", "ice", "steel"], "immune": []},
        "electric": {"offensive": ["water", "flying"], "weak": ["ground"], "resist": ["electric", "flying", "steel"], "immune": []},
        "grass":    {"offensive": ["water", "rock", "ground"], "weak": ["fire", "ice", "poison", "flying", "bug"], "resist": ["water", "electric", "grass", "ground"], "immune": []},
        "ice":      {"offensive": ["grass", "ground", "flying", "dragon"], "weak": ["fire", "fighting", "rock", "steel"], "resist": ["ice"], "immune": []},
        "fighting": {"offensive": ["normal", "ice", "rock", "dark", "steel"], "weak": ["flying", "psychic", "fairy"], "resist": ["bug", "rock", "dark"], "immune": []},
        "poison":   {"offensive": ["grass", "fairy"], "weak": ["ground", "psychic"], "resist": ["grass", "fighting", "poison", "bug", "fairy"], "immune": []},
        "ground":   {"offensive": ["fire", "electric", "poison", "rock", "steel"], "weak": ["water", "ice", "grass"], "resist": ["poison", "rock"], "immune": ["electric"]},
        "flying":   {"offensive": ["grass", "fighting", "bug"], "weak": ["electric", "ice", "rock"], "resist": ["grass", "fighting", "bug"], "immune": ["ground"]},
        "psychic":  {"offensive": ["fighting", "poison"], "weak": ["bug", "ghost", "dark"], "resist": ["fighting", "psychic"], "immune": []},
        "bug":      {"offensive": ["grass", "psychic", "dark"], "weak": ["fire", "flying", "rock"], "resist": ["grass", "fighting", "ground"], "immune": []},
        "rock":     {"offensive": ["fire", "ice", "flying", "bug"], "weak": ["water", "grass", "fighting", "ground", "steel"], "resist": ["normal", "fire", "poison", "flying"], "immune": []},
        "ghost":    {"offensive": ["psychic", "ghost"], "weak": ["ghost", "dark"], "resist": ["poison", "bug"], "immune": ["normal", "fighting"]},
        "dragon":   {"offensive": ["dragon"], "weak": ["ice", "dragon", "fairy"], "resist": ["fire", "water", "grass", "electric"], "immune": []},
        "dark":     {"offensive": ["psychic", "ghost"], "weak": ["fighting", "bug", "fairy"], "resist": ["ghost", "dark"], "immune": ["psychic"]},
        "steel":    {"offensive": ["ice", "rock", "fairy"], "weak": ["fire", "fighting", "ground"], "resist": ["normal", "grass", "ice", "flying", "psychic", "bug", "rock", "dragon", "steel", "fairy"], "immune": ["poison"]},
        "fairy":    {"offensive": ["fighting", "dragon", "dark"], "weak": ["poison", "steel"], "resist": ["fighting", "bug", "dark"], "immune": ["dragon"]}
    }

    # Format final : {type: {"offensive": [...], "defensive": {"weak": [...], "resist": [...], "immune": [...]}}}
    type_chart = {}
    for t, v in chart.items():
        type_chart[t] = {
            "offensive": v["offensive"],
            "defensive": {
                "weak": v["weak"],
                "resist": v["resist"],
                "immune": v["immune"]
            }
        }
    return type_chart

def get_weaknesses(type_name: str) -> list[str]:
    chart = get_type_chart()
    return chart.get(type_name.lower(), {}).get("defensive", {}).get("weak", [])

def get_resistances(type_name: str) -> list[str]:
    chart = get_type_chart()
    return chart.get(type_name.lower(), {}).get("defensive", {}).get("resist", [])

def get_immunities(type_name: str) -> list[str]:
    chart = get_type_chart()
    return chart.get(type_name.lower(), {}).get("defensive", {}).get("immune", [])

def get_effective_targets(type_name: str) -> list[str]:
    chart = get_type_chart()
    return chart.get(type_name.lower(), {}).get("offensive", [])


# 🧪 Test CLI
if __name__ == "__main__":
    name = "CharizardMegaY"

    print(f"\n📘 {name}")
    print("Types :", get_types(name))
    print("Stats :", get_base_stats(name))
    print("Abilities :", get_abilities(name))
    print("Roles :", get_roles(name))
    print("Has U-turn ?", has_move(name, "u-turn"))

    print("\n📋 Sets stratégiques :")
    for s in get_all_sets(name):
        print(f"• {s['name']}")
        print("  Moves:", s["moves"])
        print("  EVs:", s["evs"])
        print("  Tera:", s["tera_type"])

    print(get_roles("Cinderace"))
    print(get_tier("Roaring Moon"))
    print(get_resistances("fire"))
    print(get_immunities("ghost"))