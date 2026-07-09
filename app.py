import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Configuration de la page web (Doit impérativement être la première commande Streamlit)
st.set_page_config(page_title="PSA Production Analytics", layout="wide")

st.title("🏭 Application d'Analyse Approfondie de Production PSA")
st.markdown("Importez votre historique 2025 pour analyser la saisonnalité, le process et la qualité par produit et épaisseur.")

# 1. Zone d'importation du fichier Excel
uploaded_file = st.file_uploader("Glissez-déposez le fichier 'History Prod PSA 2025.xlsx' ici", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner('Analyse et calculs des données en cours...'):
        # Lecture du fichier Excel
        df = pd.read_excel(uploaded_file)
        
        # Nettoyage et préparation des dates
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Mois_Nom'] = df['Date'].dt.strftime('%m - %B')
        
        # Harmonisation automatique des colonnes d'après ton fichier réel
        renommage = {
            'Ep Mousse(la': 'Ep_mousse',
            'Ep_mousse': 'Ep_mousse',
            'production': 'production',
            'Chutes': 'Chutes',
            'Densité': 'Densité',
            'Mousse': 'Mousse',
            'Modèle': 'Modèle',
            'Produit': 'Produit',
            'Cause défaut': 'Cause_defaut'
        }
        df = df.rename(columns={k: v for k, v in renommage.items() if k in df.columns})

        # Forcer le type numérique pour éviter les bugs de calcul
        cols_num = ['production', 'Production Théorique', 'Chutes', 'Densité', 'Ep_mousse']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    st.success("✓ Données chargées avec succès !")

    # =====================================================================
    # EN-TÊTES / KPIS GLOBAUX
    # =====================================================================
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Production Totale Renseignée", f"{int(df['production'].sum()):,} m²")
    with col2:
        st.metric("Total des Chutes Générées", f"{int(df['Chutes'].sum()):,} m²")
    with col3:
        if 'Production Théorique' in df.columns and df['Production Théorique'].sum() > 0:
            rendement_global = (df['production'].sum() / df['Production Théorique'].sum() * 100)
            st.metric("Rendement Global Ligne (TRG)", f"{rendement_global:.1f} %")
        else:
            st.metric("Rendement Global Ligne (TRG)", "N/A (Col. Théorique absente)")

    # Création des onglets pour organiser l'application web
    onglet1, onglet2, onglet3 = st.tabs(["📈 Saisonnalité Détaillée", "🧪 Analyse Process & Densité", "❌ Qualité & Pertes"])

    # =====================================================================
    # ONGLET 1 : SAISONNALITÉ INTERACTIVE
    # =====================================================================
    with onglet1:
        st.header("Analyse Granulaire de la Saisonnalité")
        
        if 'Produit' in df.columns and 'Modèle' in df.columns and 'Ep_mousse' in df.columns:
            # Menu déroulant dynamique pour filtrer par produit sur le site
            f_produit = st.selectbox("Choisir un Produit pour filtrer les courbes", options=['Tous'] + list(df['Produit'].unique()))
            
            df_filtre = df.copy()
            if f_produit != 'Tous':
                df_filtre = df_filtre[df_filtre['Produit'] == f_produit]
                
            # Pivot des volumes mensuels par Modèle et Épaisseur
            pivot_vol = df_filtre.groupby(['Mois_Nom', 'Modèle', 'Ep_mousse'])['production'].sum().unstack(level=0).fillna(0)
            
            if not pivot_vol.empty:
                # Calcul des indices de saisonnalité (Mois / Moyenne du segment)
                pivot_indices = pivot_vol.div(pivot_vol.mean(axis=1), axis=0).round(2).reset_index()
                
                st.subheader("Tableau Dynamique des Indices Saisonniers (Moyenne du segment = 1.0)")
                st.dataframe(pivot_indices, use_container_width=True)
                
                # Préparation des données pour le graphique linéaire interactif
                df_melt = pivot_indices.melt(id_vars=['Modèle', 'Ep_mousse'], var_name='Mois', value_name='Indice')
                df_melt['Segment'] = df_melt['Modèle'].astype(str) + " - " + df_melt['Ep_mousse'].astype(str) + "mm"
                
                st.subheader("Courbes de Saisonnalité Interactives")
                fig_sais = px.line(df_melt, x='Mois', y='Indice', color='Segment', markers=True,
                                   title=f"Évolution des Indices Saisonniers pour : {f_produit}")
                fig_sais.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Seuil Moyen (1.0)")
                st.plotly_chart(fig_sais, use_container_width=True)
            else:
                st.warning("Aucune donnée de production trouvée pour ce filtre.")
        else:
            st.error("Les colonnes nécessaires ('Produit', 'Modèle', 'Ep_mousse') sont introuvables dans le fichier.")

    # =====================================================================
    # ONGLET 2 : PROCESS & MACHINE
    # =====================================================================
    with onglet2:
        st.header("Comportement Technique de la Ligne")
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            st.subheader("Stabilité de la Densité (Capabilité Chimie)")
            if 'Mousse' in df.columns and 'Densité' in df.columns:
                # Boîte à moustaches interactive Plotly
                fig_box = px.box(df[df['Densité'] > 0], x='Mousse', y='Densité', color='Mousse',
                                 title="Dispersion de la densité par type de formulation")
                st.plotly_chart(fig_box, use_container_width=True)
            else:
                st.info("Les colonnes 'Mousse' ou 'Densité' ne sont pas détectées.")
                
        with col_p2:
            st.subheader("Rendement Moyen par Épaisseur de Mousse")
            if 'Production Théorique' in df.columns and 'Ep_mousse' in df.columns:
                df['Rendement_Ligne'] = np.where(df['Production Théorique'] > 0, (df['production'] / df['Production Théorique']) * 100, np.nan)
                df_rend = df.groupby('Ep_mousse')['Rendement_Ligne'].mean().reset_index().dropna()
                
                fig_bar_rend = px.bar(df_rend, x='Ep_mousse', y='Rendement_Ligne', 
                                      labels={'Ep_mousse': 'Épaisseur (mm)', 'Rendement_Ligne': 'Rendement Moyen (%)'},
                                      color='Rendement_Ligne', color_continuous_scale='Blues')
                st.plotly_chart(fig_bar_rend, use_container_width=True)
            else:
                st.info("Données d'épaisseurs ou de production théorique insuffisantes pour calculer le rendement machine.")

    # =====================================================================
    # ONGLET 3 : QUALITÉ & PERTES
    # =====================================================================
    with onglet3:
        st.header("Analyse des Rebus Matière")
        
        col_cause = 'Cause_defaut' if 'Cause_defaut' in df.columns else ('Cause défaut' if 'Cause défaut' in df.columns else None)
        
        if col_cause and 'Chutes' in df.columns:
            pareto_data = df.groupby(col_cause)['Chutes'].sum().sort_values(ascending=False).reset_index()
            
            col_q1, col_q2 = st.columns([2, 1])
            with col_q1:
                fig_pareto = px.bar(pareto_data, x='Chutes', y=col_cause, orientation='h',
                                    title="Volume total de chutes (m²) par cause de défaut",
                                    color='Chutes', color_continuous_scale='Reds_r')
                fig_pareto.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_pareto, use_container_width=True)
                
            with col_q2:
                st.subheader("Classement des Pertes")
                st.dataframe(pareto_data, use_container_width=True)
        else:
            st.info("Les colonnes liées aux défauts ou aux chutes de production ne sont pas présentes.")
else:
    st.info("💡 En attente de l'importation de votre fichier Excel pour démarrer l'analyse approfondie.")
