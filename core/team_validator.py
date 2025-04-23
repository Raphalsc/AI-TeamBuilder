from typing import List, Dict
from data.pokedex import get_types

COMMON_THREATS = [
    "Gholdengo", "Iron Valiant", "Roaring Moon", "Great Tusk", "Kingambit", "Dragonite"
]

def analyze_type_coverage(team: List[Dict]) -> Dict[str, int]:
    """Compte le nombre de résistances / faiblesses aux types défensifs."""
    type_count = {}
    for mon in team:
        for t in [mon.get("type1"), mon.get("type2")]:
            if t:
                type_count[t] = type_count.get(t, 0) + 1
    return type_count

def check_team_balance(team: List[Dict]) -> List[str]:
    """Donne des conseils basiques : diversité de type, de rôle, etc."""
    tips = []

    types_seen = set()
    for mon in team:
        types_seen.update([mon.get("type1"), mon.get("type2")])

    if len(types_seen) < 6:
        tips.append("⚠️ L'équipe manque de diversité de types.")

    if not any("rapid spin" in m["moves"] or "defog" in m["moves"]
               for m in team if "moves" in m):
        tips.append("🧹 Aucun hazard control détecté (Défoger ou Tour Rapide).")

    # Placeholder, peut être enrichi
    return tips

def print_team_diagnostics(team: List[Dict]):
    print("\n📋 Analyse de la team :")

    type_cov = analyze_type_coverage(team)
    print("🧬 Répartition des types :", dict(sorted(type_cov.items(), key=lambda x: -x[1])))

    for tip in check_team_balance(team):
        print(tip)

if __name__ == "__main__":
    from data.pokedex import get_pokemon_data
    team = [
        get_pokemon_data("Gholdengo"),
        get_pokemon_data("Great Tusk"),
        get_pokemon_data("Dragonite"),
        get_pokemon_data("Roaring Moon"),
        get_pokemon_data("Kingambit"),
        get_pokemon_data("Iron Valiant")
    ]

    print_team_diagnostics(team)
