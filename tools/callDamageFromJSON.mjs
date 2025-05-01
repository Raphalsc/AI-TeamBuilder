// callDamageFromJSON.mjs
import { Generations, Pokemon, Move, calculate, Field } from '@smogon/calc';
import fs from 'fs';

const DEX_PATH = 'C:/Users/rapha/Desktop/AI TeamBuilder/data/pokedex_with_full_moves_and_sets.json';
const dex = JSON.parse(fs.readFileSync(DEX_PATH, 'utf-8'));
const gen = Generations.get(9);

function parseSet(pokemonName, rawSet) {
  const lines = rawSet.split('\n').map(l => l.trim()).filter(Boolean);
  const item = lines.find(line => line.startsWith('@'))?.slice(2) ?? '';
  const ability = lines.find(l => l.toLowerCase().startsWith('ability:'))?.split(': ')[1] ?? '';
  const natureLine = lines.find(line => line.includes('Nature'));
  const nature = natureLine?.split(' ')[0];

  const moves = lines.filter(line => line.startsWith('- ')).map(line => line.slice(2));

  const evs = { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 };
  const evLine = lines.find(l => l.startsWith('EVs'));
  if (evLine) {
    evLine.replace('EVs: ', '').split('/').forEach(part => {
      const [val, stat] = part.trim().split(' ');
      const statMap = {
        hp: 'hp', atk: 'atk', def: 'def', spa: 'spa', spd: 'spd', spe: 'spe',
        at: 'atk', df: 'def', sa: 'spa', sd: 'spd', sp: 'spe'
      };
      const key = statMap[stat.toLowerCase()] ?? '';
      evs[key] = parseInt(val);
    });
  }

  const ivs = { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 };
  const ivLine = lines.find(l => l.startsWith('IVs'));
  if (ivLine) {
    ivLine.replace('IVs: ', '').split('/').forEach(part => {
      const [val, stat] = part.trim().split(' ');
      const statMap = {
        hp: 'hp', atk: 'atk', def: 'def', spa: 'spa', spd: 'spd', spe: 'spe',
        at: 'atk', df: 'def', sa: 'spa', sd: 'spd', sp: 'spe'
      };
      const key = statMap[stat.toLowerCase()] ?? '';
      ivs[key] = parseInt(val);
    });
  }

  const teraType = lines.find(l => l.toLowerCase().startsWith('tera type:'))?.split(': ')[1];
  const boosts = {};
  const boostsLine = lines.find(l => l.toLowerCase().startsWith('boosts:'));
  if (boostsLine) {
    boostsLine.replace('Boosts: ', '').split(',').forEach(boost => {
      const [stat, val] = boost.trim().split('+');
      boosts[stat.toLowerCase()] = parseInt(val);
    });
  }

  return {
    name: pokemonName,
    item, ability, nature, moves, evs, ivs, teraType, boosts
  };
}

function buildPokemon(set) {
  return new Pokemon(gen, set.name, {
    item: set.item,
    ability: set.ability,
    nature: set.nature,
    evs: set.evs,
    ivs: set.ivs,
    boosts: set.boosts,
    teraType: set.teraType
  });
}

function simulateSet(attackerSet, defenderSet) {
  const attacker = buildPokemon(attackerSet);
  const defender = buildPokemon(defenderSet);
  const field = new Field({
    gameType: 'singles',
    attackerSide: {},
    defenderSide: {}
  });

  // Injecte les stats de l'objet calculé
  const attackerStats = {
    hp: attacker.stats.hp,
    atk: attacker.stats.atk,
    def: attacker.stats.def,
    spa: attacker.stats.spa,
    spd: attacker.stats.spd,
    spe: attacker.stats.spe
  };

  const defenderStats = {
    hp: defender.stats.hp,
    atk: defender.stats.atk,
    def: defender.stats.def,
    spa: defender.stats.spa,
    spd: defender.stats.spd,
    spe: defender.stats.spe
  };

  const result = {
    attacker: {
      name: attacker.name,
      item: attacker.item,
      ability: attacker.ability,
      nature: attackerSet.nature,
      evs: attackerSet.evs,
      ivs: attackerSet.ivs,
      stats: attackerStats
    },
    defender: {
      name: defender.name,
      item: defender.item,
      ability: defender.ability,
      nature: defenderSet.nature,
      evs: defenderSet.evs,
      ivs: defenderSet.ivs,
      stats: defenderStats
    },
    moves: []
  };

  for (const moveName of attackerSet.moves) {
    try {
      const move = new Move(gen, moveName);
      const calc = calculate(gen, attacker, defender, move, field);
      const damage = Array.isArray(calc.damage) ? calc.damage : [calc.damage];
      const min = Math.min(...damage);
      const max = Math.max(...damage);
      result.moves.push({ name: moveName, min, max });
    } catch (e) {
      result.moves.push({ name: moveName, error: 'invalid move' });
    }
  }
  return result;
}


const [rawA, rawB] = process.argv.slice(2);
if (!rawA || !rawB) {
  console.error('❌ Usage: node callDamageFromJSON.mjs <poke1[:set]> <poke2[:set]>');
  process.exit(1);
}

function parseArgs(raw) {
  const [nameRaw, ...setParts] = raw.split(':');
  return {
    name: nameRaw.toLowerCase(),
    setKey: setParts.length ? setParts.join(':').trim() : null
  };
}

const pkmA = parseArgs(rawA);
const pkmB = parseArgs(rawB);

const setsA = dex[pkmA.name];
const setsB = dex[pkmB.name];
if (!setsA || !setsB) {
  console.error(`❌ Pokémon introuvable : ${!setsA ? pkmA.name : pkmB.name}`);
  process.exit(1);
}

// On garde uniquement les clés de sets valides (souvent nommées "strategy: ...")
const parseSets = (sets, name) => Object.entries(sets)
  .filter(([k, v]) => typeof v === 'string' && k.startsWith('strategy:'))
  .map(([k, raw]) => ({ key: k, set: parseSet(name, raw) }));

const parsedSetsA = parseSets(setsA, pkmA.name);
const parsedSetsB = parseSets(setsB, pkmB.name);

const results = [];
for (const { key: keyA, set: setA } of parsedSetsA) {
  for (const { key: keyB, set: setB } of parsedSetsB) {
    const r = simulateSet(setA, setB);
    r.setNames = { a: keyA, b: keyB };
    results.push(r);
  }
}

console.log(JSON.stringify(results, null, 2));