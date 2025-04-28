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
        hp: 'hp',
        at: 'atk', atk: 'atk',
        df: 'def', def: 'def',
        sa: 'spa', spa: 'spa',
        sd: 'spd', spd: 'spd',
        sp: 'spe', spe: 'spe'
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
        hp: 'hp',
        at: 'atk', atk: 'atk',
        df: 'def', def: 'def',
        sa: 'spa', spa: 'spa',
        sd: 'spd', spd: 'spd',
        sp: 'spe', spe: 'spe'
      };      
      const key = statMap[stat.toLowerCase()] ?? '';
      ivs[key] = parseInt(val);
    });
  }

  const teraType = lines.find(l => l.toLowerCase().startsWith('tera type:'))?.split(': ')[1] ?? undefined;

  const boosts = {};
  const boostsLine = lines.find(l => l.toLowerCase().startsWith('boosts:'));
  if (boostsLine) {
    boostsLine.replace('Boosts: ', '').split(',').forEach(boost => {
      const [stat, val] = boost.trim().split('+');
      boosts[stat.toLowerCase()] = parseInt(val);
    });
  }

  const status = lines.find(l => l.toLowerCase().startsWith('status:'))?.split(': ')[1] ?? undefined;

  return {
    name: pokemonName,
    item,
    ability,
    nature,
    evs,
    ivs,
    moves,
    teraType,
    boosts,
    status
  };
}

function getWeatherFromAbility(ability) {
  const a = ability.toLowerCase();
  if (a === 'drizzle') return 'Rain';
  if (a === 'drought') return 'Sun';
  if (a === 'snow warning') return 'Snow';
  if (a === 'sand stream') return 'Sand';
  return undefined;
}

function buildPokemon(set) {
  return new Pokemon(gen, set.name, {
    item: set.item,
    ability: set.ability,
    nature: set.nature,
    evs: set.evs,
    ivs: set.ivs,
    boosts: set.boosts,
    teraType: set.teraType,
    status: set.status
  });
}

function calculateDamage(attackerSet, defenderSet) {
  const attacker = buildPokemon(attackerSet);
  const defender = buildPokemon(defenderSet);

  const autoWeather = getWeatherFromAbility(attackerSet.ability) || getWeatherFromAbility(defenderSet.ability);

  const field = new Field({
    gameType: 'singles',
    weather: autoWeather || undefined,
    terrain: '',
    isGravity: false,
    isMagicRoom: false,
    isWonderRoom: false,
    attackerSide: {
      spikes: 1,
      stealthRock: true
    },
    defenderSide: {
      spikes: 2,
      stealthRock: true
    }
  });

  console.log(`\n🔬 ${attacker.name} (${attacker.item}, ${attacker.ability}, Tera: ${attacker.teraType ?? 'aucun'}) vs ${defender.name} (${defender.item}, ${defender.ability})`);

  for (const moveName of attackerSet.moves) {
    try {
      const move = new Move(gen, moveName);
      const result = calculate(gen, attacker, defender, move, field);
      const hp = result.defender.stats.hp;

      let percents;
      if (Array.isArray(result.damage)) {
        const min = Math.min(...result.damage);
        const max = Math.max(...result.damage);
        const minPct = ((min / hp) * 100).toFixed(1);
        const maxPct = ((max / hp) * 100).toFixed(1);
        percents = `${minPct}% - ${maxPct}%`;
      } else {
        const pct = ((result.damage / hp) * 100).toFixed(1);
        percents = `${pct}%`;
      }

      console.log(`⚔️ ${moveName}: ${percents}`);
    } catch (e) {
      console.warn(`❌ Move invalide: ${moveName}`);
    }
  }
}

function parseArgs(raw) {
  const [nameRaw, ...setParts] = raw.split(':');
  const name = nameRaw.toLowerCase();
  const setKey = setParts.length ? setParts.join(':').trim() : null;
  return { name, setKey };
}

const [rawA, rawB] = process.argv.slice(2);
if (!rawA || !rawB) {
  console.error("❌ Utilisation : node callDamageFromJSON.mjs <poke1[:set]> <poke2[:set]>");
  process.exit(1);
}

const pkmA = parseArgs(rawA);
const pkmB = parseArgs(rawB);

const setsA = dex[pkmA.name];
const setsB = dex[pkmB.name];

if (!setsA || !setsB) {
  console.error(`❌ Pokémon introuvable : ${!setsA ? pkmA.name : pkmB.name}`);
  process.exit(1);
}

const isValidSet = (key, val) =>
  typeof val === 'string' && !/^(name|type1|type2|ability1|ability2|hidden ability|format)$/i.test(key);

const parsedSetsA = Object.entries(setsA)
  .filter(([k, v]) => isValidSet(k, v))
  .map(([k, raw]) => ({ key: k, set: parseSet(pkmA.name, raw) }));

const parsedSetsB = Object.entries(setsB)
  .filter(([k, v]) => isValidSet(k, v))
  .map(([k, raw]) => ({ key: k, set: parseSet(pkmB.name, raw) }));

if (pkmA.setKey && pkmB.setKey) {
  const rawSetA = setsA[pkmA.setKey];
  const rawSetB = setsB[pkmB.setKey];
  if (!rawSetA || !rawSetB) {
    console.error(`❌ Set introuvable : ${!rawSetA ? pkmA.setKey : pkmB.setKey}`);
    process.exit(1);
  }
  const parsedA = parseSet(pkmA.name, rawSetA);
  const parsedB = parseSet(pkmB.name, rawSetB);
  calculateDamage(parsedA, parsedB);
} else {
  for (const { key: kA, set: setA } of parsedSetsA) {
    for (const { key: kB, set: setB } of parsedSetsB) {
      console.log(`\n🧪 ${kA} vs ${kB}`);
      calculateDamage(setA, setB);
    }
  }
}
