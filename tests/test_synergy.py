import pytest
from core.synergy_calculator import is_compatible_with_team, get_team_type_coverage
from data.pokedex import get_pokemon_data

def test_type_overlap_blocks_addition():
    team = [
        get_pokemon_data("Garchomp"),   # Dragon / Ground
        get_pokemon_data("Dragonite")   # Dragon / Flying
    ]
    test_pokemon = get_pokemon_data("Roaring Moon")  # Dark / Dragon

    assert is_compatible_with_team(team, test_pokemon) == False

def test_type_diversity_allows_addition():
    team = [
        get_pokemon_data("Gholdengo"),  # Ghost / Steel
        get_pokemon_data("Great Tusk")  # Ground / Fighting
    ]
    test_pokemon = get_pokemon_data("Iron Valiant")  # Fairy / Fighting

    assert is_compatible_with_team(team, test_pokemon) == True

def test_type_coverage_summary():
    team = [
        get_pokemon_data("Ting-Lu"),
        get_pokemon_data("Iron Moth"),
        get_pokemon_data("Iron Valiant")
    ]
    coverage = get_team_type_coverage(team)
    assert coverage.get("poison") >= 1
    assert coverage.get("fighting") >= 1
