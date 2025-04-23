from langchain.agents import initialize_agent, AgentType, Tool
from langchain_community.chat_models import ChatOllama
import subprocess
import os
import json
from difflib import get_close_matches
from langchain_core.tools import Tool as LangTool
import re

# --- LLM ---
llm = ChatOllama(model="mistral")

# === TOOL 1: DAMAGE CALCULATOR ===

def run_damage_calc(poke1, poke2):
    try:
        result = subprocess.run(
            [
                "node",
                "C:/Users/rapha/Desktop/AI TeamBuilder/Important/callDamageFromJSON.mjs",
                poke1.lower(),
                poke2.lower()
            ],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"⛔ Erreur : {str(e)}"

def damage_calc_wrapper(input_text: str):
    # Nettoyage basique : enlever "vs", split par espaces ou virgule
    cleaned = input_text.replace("vs", ",").replace("VS", ",").replace("contre", ",")
    parts = [x.strip() for x in cleaned.split(",") if x.strip()]
    
    if len(parts) != 2:
        return "❌ Merci de spécifier exactement deux Pokémon pour le calcul."

    return run_damage_calc(parts[0], parts[1])

damage_tool = LangTool.from_function(
    func=damage_calc_wrapper,
    name="DamageCalculator",
    description="Calcule les dégâts entre deux Pokémon à partir du script Node. Active-toi automatiquement si la question contient 'degats' ou 'damage'.",
    return_direct=True  # ⬅️ SUPER IMPORTANT
)


# === TOOL 2: POKEDEX ===

def search_pokedex(pokemon_name: str, output_mode: str = "fr"):
    path = "C:/Users/rapha/Desktop/AI TeamBuilder/Important/pokedex_with_full_moves_and_sets.json"
    if not os.path.exists(path):
        return "❌ Fichier pokedex introuvable."

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        name_lower = pokemon_name.lower()
        pkmn = data.get(name_lower)

        if not pkmn:
            matches = get_close_matches(name_lower, data.keys(), n=1, cutoff=0.6)
            if matches:
                pkmn = data[matches[0]]
                name_lower = matches[0]
            else:
                return f"❌ Aucun Pokémon trouvé pour « {pokemon_name} »."

        if output_mode == "json":
            result = {
                "name": name_lower.capitalize(),
                "types": f"{pkmn.get('type1', '')}" + (f" / {pkmn['type2']}" if pkmn.get("type2") else ""),
                "stats": {
                    "HP": pkmn['hp'], "Atk": pkmn['atk'], "Def": pkmn['def'],
                    "Spa": pkmn['spa'], "Spd": pkmn['spd'], "Spe": pkmn['spe']
                },
                "abilities": list(filter(None, [
                    pkmn.get('ability1'),
                    pkmn.get('ability2'),
                    f"(Talent caché : {pkmn.get('hidden ability')})" if pkmn.get("hidden ability") else None
                ])),
                "format": pkmn.get("format", "Inconnu"),
                "moves": pkmn.get("moves", [])
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        types = f"{pkmn.get('type1', '')}" + (f" / {pkmn['type2']}" if pkmn.get("type2") else "")
        abilities = list(filter(None, [
            pkmn.get('ability1'),
            pkmn.get('ability2'),
            f"(Talent caché : {pkmn.get('hidden ability')})" if pkmn.get("hidden ability") else None
        ]))
        stats = f"PV: {pkmn['hp']}, Atk: {pkmn['atk']}, Def: {pkmn['def']}, Atk Spé: {pkmn['spa']}, Def Spé: {pkmn['spd']}, Vit: {pkmn['spe']}"
        moves = ", ".join(pkmn.get("moves", []))

        return (
            f"📘 {name_lower.capitalize()} ({types}) — Format: {pkmn.get('format', 'Inconnu')}\n"
            f"Stats : {stats}\n"
            f"Talents : {', '.join(abilities)}\n"
            f"Attaques connues : {moves}"
        )

    except Exception as e:
        return f"❌ Erreur lors de la lecture du pokédex : {str(e)}"

def pokedex_wrapper(query: str):
    brut = any(word in query.lower() for word in ["json", "brut", "format brut"])
    output_mode = "json" if brut else "fr"

    noms_possibles = query.replace("et", ",").split(",")
    results = []

    for nom in noms_possibles:
        nom = nom.strip()
        if nom:
            res = search_pokedex(nom, output_mode=output_mode)
            results.append(res)

    return "\n\n".join(results)

pokedex_tool = Tool(
    name="PokedexReader",
    func=pokedex_wrapper,
    description="Affiche les informations d’un ou plusieurs Pokémon. Si le mot 'json' est dans la requête, le résultat est retourné en format brut JSON."
)

# === AGENT ===
tools = [damage_tool, pokedex_tool]

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True
)

print("🔧 Agent prêt. Tu peux lui parler ! (écris 'exit' pour quitter)")

while True:
    query = input("💬 > ")
    if query.lower() in ["exit", "quit"]:
        break
    response = agent.run(query)
    print("🤖", response)
