from data.pokedex import get_pokemon_data
from core.metagame_analyzer import load_metagame_data, get_top_sets

metagame = load_metagame_data()

def generate_set(pokemon_name: str, role_hint: str = None) -> dict | None:
    """Propose un set pour un Pokémon donné, basé sur le méta ou une intention."""
    pkmn_data = get_pokemon_data(pokemon_name)
    if not pkmn_data:
        print(f"❌ Pokémon inconnu : {pokemon_name}")
        return None

    meta_info = metagame.get(pokemon_name)
    moves = pkmn_data.get("moves", [])

    # 🎯 Si le rôle est donné, on filtre par mots-clés
    selected_moves = []
    if role_hint:
        if "hazard" in role_hint.lower():
            for m in ["stealth rock", "toxic spikes", "spikes", "sticky web"]:
                if m in moves:
                    selected_moves.append(m)
        if "setup" in role_hint.lower():
            for m in ["swords dance", "nasty plot", "dragon dance", "calm mind", "bulk up"]:
                if m in moves:
                    selected_moves.append(m)
        if "pivot" in role_hint.lower():
            for m in ["u-turn", "volt switch", "flip turn"]:
                if m in moves:
                    selected_moves.append(m)

    # 🧠 Si on ne trouve rien via role_hint → fallback sur les sets les plus utilisés
    if not selected_moves and meta_info:
        top_spreads = meta_info.get("spreads", {})
        top_moves = meta_info.get("moves", {})
        sorted_moves = sorted(top_moves.items(), key=lambda x: -x[1])
        selected_moves = [m for m, _ in sorted_moves[:4] if m in moves]

    # 📦 Construction du set
    set_data = {
        "name": pokemon_name,
        "moves": selected_moves or moves[:4],
        "ability": pkmn_data.get("ability1"),
        "tera_type": "???",  # Tu pourras calculer ça plus tard
        "evs": "252 Atk / 252 Spe / 4 HP",
        "nature": "Jolly"
    }
    return set_data

if __name__ == "__main__":
    result = generate_set("Great Tusk", role_hint="hazard")
    print("🔧 Set généré :")
    print(result)
