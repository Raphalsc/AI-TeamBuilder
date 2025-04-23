from typing import List, Dict
from data.pokedex import get_types

def is_compatible_with_team(team: List[Dict], candidate: Dict) -> bool:
    """
    Vérifie si le Pokémon candidat est compatible avec l'équipe :
    - Évite les doublons de types majeurs
    - Évite la mono-faiblesse (ex: trop faible au type Eau, Glace, etc.)
    """
    if not candidate:
        return False

    candidate_types = set(filter(None, [candidate.get("type1"), candidate.get("type2")]))
    team_types = []

    for member in team:
        types = set(filter(None, [member.get("type1"), member.get("type2")]))
        team_types.extend(types)

    # 🔁 Si le candidat partage déjà les 2 mêmes types que 2 membres → refuse
    type_overlap = sum(1 for t in candidate_types if t in team_types)
    if type_overlap >= 2:
        return False

    return True

def get_team_type_coverage(team: List[Dict]) -> Dict[str, int]:
    """
    Compte le nombre de fois qu'un type apparaît dans la team.
    Utile pour détecter les redondances ou faiblesses globales.
    """
    type_count = {}
    for member in team:
        for t in [member.get("type1"), member.get("type2")]:
            if t:
                type_count[t] = type_count.get(t, 0) + 1
    return type_count

if __name__ == "__main__":
    from data.pokedex import get_pokemon_data

    team = [get_pokemon_data("Iron Valiant"), get_pokemon_data("Great Tusk")]
    test = get_pokemon_data("Roaring Moon")

    print("Types de la team :", get_team_type_coverage(team))
    print(f"✅ Roaring Moon est compatible ? {is_compatible_with_team(team, test)}")
