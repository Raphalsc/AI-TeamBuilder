import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from core.new_pokemon_analyzer import analyze_pokemon

st.set_page_config(page_title="AI TeamBuilder – Analyse de Pokémon", layout="wide")
st.title("🔍 Analyse de Pokémon (AI TeamBuilder)")

name = st.text_input("Nom du Pokémon à analyser", "")

if name:
    with st.spinner("Analyse en cours..."):
        try:
            data = analyze_pokemon(name)
        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")
            st.stop()

    # Onglets de navigation
    tab1, tab2, tab3, tab4 = st.tabs(["📘 Résumé", "⚔️ Matchups", "🔗 Cores Favorables", "🛡️ Cores Défavorables"])

    # === Onglet Résumé
    with tab1:
        st.header(f"📘 Résumé de {data['name']}")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🧬 Informations Générales")
            st.markdown(f"**Types**: {', '.join(data['types'])}")
            st.markdown(f"**Rôles**: {', '.join(data['roles'])}")
            st.markdown(f"**Usage**: {data['usage']}")
            st.markdown(f"**Viability Ceiling**: {data['viability_ceiling']}")

        with col2:
            st.subheader("📊 Statistiques de Base")
            st.json(data['base_stats'])

        st.subheader("🧪 Sets Possibles")
        sets = data.get('sets', {})
        if isinstance(sets, dict):
            for set_name, set_code in sets.items():
                st.markdown(f"**{set_name}**\n```{set_code}```")
        elif isinstance(sets, list):
            for set_code in sets:
                st.markdown(f"```{set_code}```")
        else:
            st.markdown("_Aucun set disponible._")

        st.subheader("📈 Données Méta")
        meta = data.get("meta", {})
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Top Abilities**")
            st.write(meta.get("top_abilities", "Non disponible"))
            st.markdown("**Top Moves**")
            st.write(meta.get("top_moves", "Non disponible"))
            st.markdown("**Top Teammates**")
            st.write(meta.get("top_teammates", "Non disponible"))

        with col4:
            st.markdown("**Top Items**")
            st.write(meta.get("top_items", "Non disponible"))
            st.markdown("**Top Tera Types**")
            st.write(meta.get("top_tera_types", "Non disponible"))
            st.markdown("**Counters**")
            st.write(meta.get("counters", "Non disponible"))

    # === Onglet Matchups
    with tab2:
        st.subheader("⚔️ Matchups vs Top Threats")
        matchups = data.get("matchups", {})
        if matchups:
            results_df = pd.DataFrame([
                {"Opponent": k, "Winrate": v["winrate"], "Verdict": v["verdict"]}
                for k, v in matchups.items() if "winrate" in v
            ])
            fig, ax = plt.subplots()
            results_df.sort_values("Winrate", ascending=True).plot.barh(
                x="Opponent", y="Winrate", color="skyblue", ax=ax, legend=False
            )
            ax.set_xlabel("Winrate (%)")
            ax.set_title("Matchups vs Top Threats")
            st.pyplot(fig)

            for opponent, result in matchups.items():
                col = "✅" if result["verdict"].startswith("✅") else "❌" if result["verdict"].startswith("❌") else "⚖️"
                summary = f"{col} {opponent} — {result['verdict']} ({result['winrate']}%)"
                with st.expander(summary):
                    st.write(result)
        else:
            st.info("Aucun matchup trouvé.")

    # === Onglet Core Synergies
    with tab3:
        st.subheader("🔗 Cores où ce Pokémon est utilisé")
        for core in data.get("core_synergies", []):
            st.write(" + ".join(core))
        if not data.get("core_synergies"):
            st.write("Aucun core détecté.")

    # === Onglet Core Counters
    with tab4:
        st.subheader("🛡️ Performance contre les cores adverses")
        for core_block in data.get("core_counters", []):
            core = " + ".join(core_block["core"])
            summary = core_block["summary"]
            verdict = summary["verdict"]
            badge = "✅" if verdict.startswith("✅") else "❌" if verdict.startswith("❌") else "⚖️"
            with st.expander(f"{badge} {core} — {verdict}"):
                st.markdown(f"**Résultats**: {summary['wins']} Win / {summary['losses']} Loss / {summary['draws']} Draw")
                for foe, res in core_block["details"]:
                    st.markdown(f"- {foe}: {res['verdict']} ({res.get('winrate', '—')}%)")

    st.success("✅ Analyse terminée.")
