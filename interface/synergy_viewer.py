import streamlit as st
import json
import os
import subprocess
from data.pokedex import get_roles

JSON_PATH = "data/results/synergy_result.json"
CALCULATOR_PATH = "core/synergy_calculator.py"

st.set_page_config(page_title="Synergy Viewer", layout="wide")
st.title("🧠 Synergy Core Viewer")

# === Formulaire de configuration du calcul ===
with st.expander("⚙️ Générer un core personnalisé", expanded=not os.path.exists(JSON_PATH)):
    with st.form("form_calc"):
        n_core = st.number_input("Taille du core", min_value=2, max_value=6, value=3)
        base_pokemon = st.text_input("Pokémon fixes (séparés par des virgules)", value="Kyurem")
        roles_input = st.text_input("Rôles visés pour les autres slots (séparés par des virgules)", value="aucun, special_sweeper")
        submitted = st.form_submit_button("Lancer le calcul")

    if submitted:
        base_args = [p.strip().replace(" ", "_") for p in base_pokemon.split(",") if p.strip()]
        role_args = [r.strip() for r in roles_input.split(",") if r.strip()]
        if len(base_args) + len(role_args) != n_core:
            st.error("Nombre de Pokémon + rôles ne correspond pas à la taille du core.")
            st.stop()

        full_cmd = ["python", "-m", "core.synergy_calculator", str(n_core)] + base_args + ["--roles"] + role_args
        st.info("🔄 Calcul en cours (cela peut prendre plusieurs minutes)...")
        with st.spinner("Simulation stratégique..."):
            result = subprocess.run(full_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            st.error(f"Erreur :\n{result.stderr}")
        else:
            st.success("✅ Core généré avec succès. Résultats affichés ci-dessous 👇")
            st.rerun()

# === Vérification des résultats ===
if not os.path.exists(JSON_PATH):
    st.warning("Aucun résultat trouvé. Lance d'abord une simulation.")
    st.stop()

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

core = data.get("core", [])
log_lines = data.get("log", [])
duels = data.get("duels", {})

# === Core final ===
st.header("🏁 Core final")
for poke in core:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(f"https://img.pokemondb.net/sprites/home/normal/{poke.lower().replace(' ', '-')}.png", width=96)
    with col2:
        st.markdown(f"**{poke}**")
        st.markdown(f"Rôles : `{', '.join(get_roles(poke))}`")

# === Menaces ===
st.divider()
st.header("🛡️ Menaces identifiées")

true_threats = [
    t for t in duels
    if all(duels[t].get(p) == "✅ Win" for p in core)
]
partial_threats = [
    t for t in duels
    if any(duels[t].get(p) == "✅ Win" for p in core)
    and not all(duels[t].get(p) == "✅ Win" for p in core)
]

if true_threats:
    st.subheader("❗ Menaces majeures (battent tout le core)")
    for t in true_threats:
        st.markdown(f"**{t}** gagne contre : {', '.join([p for p in core if duels[t].get(p) == '✅ Win'])}")
else:
    st.info("Aucune menace ne bat tous les membres du core.")

if partial_threats:
    st.subheader("⚠️ Menaces partielles (battent au moins un membre)")
    for t in partial_threats:
        winners = [p for p in core if duels[t].get(p) == "✅ Win"]
        st.markdown(f"**{t}** gagne contre : {', '.join(winners)}")

# === Duels individuels ===
st.divider()
st.header("📈 Résultats des duels")

selected = st.selectbox("Sélectionne un Pokémon pour voir ses duels", options=sorted(duels.keys()))
if selected in duels:
    for target, verdict in duels[selected].items():
        st.markdown(f"- {selected} vs {target}: **{verdict}**")

# === Log brut ===
st.divider()
with st.expander("📝 Log complet"):
    for line in log_lines:
        st.text(line)
