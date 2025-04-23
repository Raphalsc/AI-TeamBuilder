from core.metagame_analyzer import load_metagame_data, get_top_threats
from data.pokedex import get_pokemon_data, get_types
from core.synergy_calculator import is_compatible_with_team  # à créer bientôt

from typing import List

metagame = load_metagame_data()

class TeamBuilder:
    def __init__(self, style: str = "balance"):
        self.team = []
        self.style = style.lower()
        self.threats = [name for name, _ in get_top_threats(metagame)]

    def add_pokemon(self, name: str, force: bool = False) -> bool:
        """Ajoute un Pokémon à la team si compatible. Force = ignorer les synergies."""
        data = get_pokemon_data(name)
        if not data:
            print(f"❌ Pokémon inconnu : {name}")
            return False

        if not force and not is_compatible_with_team(self.team, data):
            print(f"⚠️ {name} ne s’intègre pas bien dans la team.")
            return False

        self.team.append(data)
        print(f"✅ Ajouté : {data['name']}")
        return True

    def is_full(self) -> bool:
        return len(self.team) >= 6

    def get_team_preview(self) -> List[str]:
        return [p["name"].capitalize() for p in self.team]

    def build(self, around: str = None):
        """Point d’entrée principal. Construit une équipe autour d’un Pokémon donné."""
        print(f"🔧 Construction d’une team '{self.style}'")
        if around:
            self.add_pokemon(around, force=True)

        while not self.is_full():
            suggestion = self.suggest_next_member()
            if not suggestion:
                print("🚫 Aucune suggestion trouvée")
                break
            self.add_pokemon(suggestion)

        print("\n🏁 Team finale :")
        print(" / ".join(self.get_team_preview()))

        # 🧪 Analyse post-teambuild
        from core.team_validator import print_team_diagnostics
        print_team_diagnostics(self.team)

    def suggest_next_member(self) -> str | None:
        candidates = [name for name, _ in get_top_threats(metagame, top_n=40)]

        for name in candidates:
            if name.lower() in [p["name"].lower() for p in self.team]:
                continue  # déjà dans l'équipe

            candidate_data = get_pokemon_data(name)
            if not candidate_data:
                continue

            from core.synergy_calculator import is_compatible_with_team
            if is_compatible_with_team(self.team, candidate_data):
                return name

        return None


if __name__ == "__main__":
    builder = TeamBuilder(style="balance")
    builder.build(around="Iron Valiant")
