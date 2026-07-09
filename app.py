import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION INTERFACE (Doit rester la toute première commande) ---
st.set_page_config(page_title="PSA Dashboard Pro", layout="wide", initial_sidebar_state="expanded")

st.title("🏭 Dashboard de Performance Industrielle - Ligne PSA")
st.markdown("### Analyse Avancée Multi-Dimensionnelle : Saisonnalité, Épaisseurs de Parements & Qualité")

# --- BARRE LATÉRALE D'IMPORTATION ---
st.sidebar.header("📂 Données d'Entrée")
uploaded_file = st.sidebar.file_uploader("Charger l'extraction 'History Prod PSA 2025.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner('Extraction et parsing automatique des parements...'):
        df = pd.read_excel(uploaded_file)
        
        # 1. Gestion et standardisation des dates
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Mois_Nom'] = df['Date'].dt.strftime('%m - %B')
        
        # 2. Renommage des colonnes standards
        renames = {
            'Ep Mousse(la': 'Ep_mousse', 'Ep_mousse': 'Ep_mousse', 
            'production': 'production', 'Modèle': 'Modèle', 'Produit': 'Produit'
        }
        df = df.rename(columns={k: v for k, v in renames.items() if k in df.columns})
        
        # Gestion des chutes
        if 'Chutes EXT' in df.columns:
            df['Chutes'] = df['Chutes EXT']
        elif 'Chutes' in df.columns:
            pass
        else:
            df['Chutes'] = 0

        # 3. IDENTIFICATION ROBUSTE DES DEUX COLONNES "DIMENSION" PAR POSITION
        # On cherche toutes les colonnes qui s'appellent "Dimension" ou commencent par "Dimension"
        dimension_cols = [c for c in df.columns if str(c).startswith('Dimension')]
        
        if len(dimension_cols) >= 2:
            # La 1ère trouvée = Parement Extérieur
            col_ext = dimension_cols[0]
            # La 2ème trouvée = Parement Intérieur
            col_int = dimension_cols[1]
            
            # Extraction des épaisseurs (ex: "0.25x1165.0" -> "0.25")
            df['Ep_Parement_Ext'] = df[col_ext].astype(str).str.split('x').str[0].str.strip()
            df['Ep_Parement_Int'] = df[col_int].astype(str).str.split('x').str[0].str.strip()
        else:
            # Fallback de secours si jamais les noms ont été modifiés à l'import
            df['Ep_Parement_Ext'] = "Inconnu"
            df['Ep_Parement_Int'] = "Inconnu"

        # Conversion propre en chaînes textuelles propres pour éviter le mélange avec les 0 numériques
        df['Ep_Parement_Ext'] = df['Ep_Parement_Ext'].replace(['nan', '0', '0.0'], 'Non spécifié')
        df['Ep_Parement_Int'] = df['Ep_Parement_Int'].replace(['nan', '0', '0.0'], 'Non spécifié')

        # Nettoyage des types numériques pour les calculs sans bugs
        cols_num = ['production', 'Chutes', 'Densité', 'Ep_mousse']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    st.success("✓ Fichier PSA importé et analysé avec succès !")

    # --- BARRE LATÉRALE : FILTRES STRATÉGIQUES ---
    st.sidebar.header("🎯 Filtres Dynamiques")
    
    liste_produits = sorted(list(df['Produit'].dropna().unique()))
    selected_produit = st.sidebar.selectbox("Sélectionner un Produit Principal", options=['Tous'] + liste_produits)
    
    df_step = df.copy()
    if selected_produit != 'Tous':
        df_step = df_step[df_step['Produit'] == selected_produit]
        
    liste_modeles = sorted(list(df_step['Modèle'].dropna().unique()))
    selected_modeles = st.sidebar.multiselect("Filtrer par Modèle(s)", options=liste_modeles, default=liste_modeles[:4])
    
    df_filtered = df_step[df_step['Modèle'].isin(selected_modeles)]

    # =====================================================================
    # SECTION 1 : PANNEAU DES INDICATEURS CLÉS (KPIS)
    # =====================================================================
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Volume Produit Filé", f"{int(df_filtered['production'].sum()):,} m²")
    with kpi2:
        tot_chutes = df_filtered['Chutes'].sum()
        tot_prod = df_filtered['production'].sum()
        taux_rebut = (tot_chutes / tot_prod * 100) if tot_prod > 0 else 0
        st.metric("Taux de Chutes Généré", f"{taux_rebut:.2f} %")
    with kpi3:
        avg_dens = df_filtered[df_filtered['Densité'] > 0]['Densité'].mean()
        st.metric("Densité Moyenne Chimie", f"{avg_dens:.1f} kg/m³" if not np.isnan(avg_dens) else "N/A")
    with kpi4:
        mix_count = df_filtered.groupby(['Modèle', 'Ep_mousse', 'Ep_Parement_Ext', 'Ep_Parement_Int']).ngroups
        st.metric("Combinaisons de Mix Actives", mix_count)

    # =====================================================================
    # SECTION 2 : ONGLETS D'ANALYSE AVANCÉE
    # =====================================================================
    tab1, tab2, tab3 = st.tabs(["📊 Saisonnalité Globale & Indices", "🔬 Structure Produits & Parements", "📉 Analyse Qualité & Procédé"])

    # --- TAB 1 : SAISONNALITÉ ---
    with tab1:
        st.subheader("Analyse Matricielle des Profils Saisonniers")
        col_t1_1, col_t1_2 = st.columns([2, 1])
        
        with col_t1_1:
            st.markdown("**🔥 Carte de Chaleur (Heatmap) des Volumes Produits (m²)**")
            pivot_heat = df_filtered.groupby(['Modèle', 'Mois_Nom'])['production'].sum().unstack().fillna(0)
            if not pivot_heat.empty:
                fig_heat = px.imshow(pivot_heat, text_auto=True, aspect="auto", color_continuous_scale='Blues',
                                     labels=dict(x="Mois de l'Année", y="Modèle PSA", color="Volume (m²)"))
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("Sélectionnez des modèles dans la barre latérale pour afficher la Heatmap.")

        with col_t1_2:
            st.markdown("**📈 Courbes d'Indices Saisonniers Granulaires**")
            if not pivot_heat.empty:
                pivot_indices = pivot_heat.div(pivot_heat.mean(axis=1), axis=0).round(2).reset_index()
                df_melt = pivot_indices.melt(id_vars='Modèle', var_name='Mois', value_name='Indice')
                
                fig_line = px.line(df_melt, x='Mois', y='Indice', color='Modèle', markers=True,
                                   title="Variation Relative (Base moyenne = 1.0)")
                fig_line.add_hline(y=1.0, line_dash="dash", line_color="red")
                st.plotly_chart(fig_line, use_container_width=True)

    # --- TAB 2 : ANATOMIE DES PAREMENTS ---
    with tab2:
        st.subheader("Cartographie Technique des Épaisseurs de Métal")
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            st.markdown("**🍩 Distribution des Épaisseurs (Parement Extérieur)**")
            fig_pie_ext = px.pie(df_filtered, names='Ep_Parement_Ext', values='production', hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie_ext, use_container_width=True)
            
        with col_p2:
            st.markdown("**🍩 Distribution des Épaisseurs (Parement Intérieur)**")
            fig_pie_int = px.pie(df_filtered, names='Ep_Parement_Int', values='production', hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie_int, use_container_width=True)
            
        st.markdown("---")
        st.markdown("**🌳 Arborescence Multi-Couches (Sunburst Chart du Mix Produit)**")
        st.write("Ce graphique interactif se lit du centre vers l'extérieur : Produit ➔ Épaisseur Mousse ➔ Épaisseur Extérieure ➔ Épaisseur Intérieure.")
        
        # Préparation propre du Sunburst pour éviter tout crash hiérarchique
        df_sunburst = df_filtered[
            (df_filtered['production'] > 0) & 
            (df_filtered['Produit'].notna())
        ].copy()
        
        df_sunburst['Mousse'] = df_sunburst['Ep_mousse'].astype(str) + " mm"
        df_sunburst['Face_Ext'] = "Ext: " + df_sunburst['Ep_Parement_Ext'].astype(str)
        df_sunburst['Face_Int'] = "Int: " + df_sunburst['Ep_Parement_Int'].astype(str)

        if not df_sunburst.empty:
            fig_sun = px.sunburst(df_sunburst, 
                                  path=['Produit', 'Mousse', 'Face_Ext', 'Face_Int'], 
                                  values='production', 
                                  color='production', 
                                  color_continuous_scale='YlOrRd')
            st.plotly_chart(fig_sun, use_container_width=True)
        else:
            st.info("Données insuffisantes ou nulles pour générer l'arborescence complète.")

    # --- TAB 3 : QUALITÉ ---
    with tab3:
        st.subheader("Suivi de l'Efficience et Capabilité Ligne")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("**⚖️ Stabilité de la Densité de Mousse par Épaisseur**")
            fig_box = px.box(df_filtered[df_filtered['Densité'] > 0], x='Ep_mousse', y='Densité', color='Ep_mousse',
                             title="Dispersion de la densité matière")
            st.plotly_chart(fig_box, use_container_width=True)
            
        with col_g2:
            st.markdown("**📉 Évolution Temporelle des Chutes Industrielles (m²)**")
            df_time = df_filtered.groupby('Mois_Nom')['Chutes'].sum().reset_index()
            fig_bar_chutes = px.bar(df_time, x='Mois_Nom', y='Chutes', color='Chutes', color_continuous_scale='Reds')
            st.plotly_chart(fig_bar_chutes, use_container_width=True)

    # --- DATA EXPLORER ---
    with st.expander("🔍 Explorateur de Données Brutes Filtrées"):
        st.dataframe(df_filtered[['Date', 'Produit', 'Modèle', 'Ep_mousse', 'Ep_Parement_Ext', 'Ep_Parement_Int', 'production', 'Chutes']], use_container_width=True)

else:
    st.info("👋 Bienvenue sur votre nouveau Dashboard PSA ! Veuillez charger votre fichier Excel dans la barre latérale gauche pour générer les analyses complexes.")
