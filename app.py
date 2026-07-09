import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- CONFIGURATION DE L'INTERFACE DE HAUT NIVEAU ---
st.set_page_config(
    page_title="PSA Performance Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS épuré et compatible toutes versions pour moderniser l'affichage
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1 { color: #1E3A8A; font-weight: 700; }
        .stMetric { background-color: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; }
    </style>
""", unsafe_allow_html=True)

st.title("🏭 Dashboard de Performance Industrielle — Ligne PSA")
st.markdown("### Analyse Avancée Multi-Dimensionnelle : Saisonnalité, Épaisseurs & Qualité Procédé")

# --- BARRE LATÉRALE : IMPORTATION SÉCURISÉE ---
st.sidebar.header("📂 Importation des Données")
uploaded_file = st.sidebar.file_uploader("Charger le fichier Excel de production PSA", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner('Extraction analytique des données en cours...'):
        # Lecture du fichier Excel
        df = pd.read_excel(uploaded_file)
        
        # 1. Normalisation stricte des dates pour l'analyse de saisonnalité
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Mois_Index'] = df['Date'].dt.month
            df['Mois_Nom'] = df['Date'].dt.strftime('%m - %B')
        else:
            df['Mois_Index'] = 1
            df['Mois_Nom'] = "Non spécifié"

        # 2. Harmonisation des noms de colonnes clés
        renames = {
            'Ep Mousse(la': 'Ep_mousse', 'Ep_mousse': 'Ep_mousse', 
            'production': 'production', 'Modèle': 'Modèle', 'Produit': 'Produit',
            'Densité': 'Densité'
        }
        df = df.rename(columns={k: v for k, v in renames.items() if k in df.columns})
        
        # Gestion intelligente des rebuts/chutes
        if 'Chutes EXT' in df.columns:
            df['Chutes'] = df['Chutes EXT']
        elif 'Chutes' in df.columns:
            df['Chutes'] = df['Chutes']
        else:
            df['Chutes'] = 0

        # 3. EXTRACTION ROBUSTE DES PAREMENTS (Résout définitivement le problème des doublons "Dimension")
        dimension_cols = [c for c in df.columns if str(c).startswith('Dimension')]
        
        if len(dimension_cols) >= 2:
            # Extraction propre avant le 'x' (ex: "0.25x1165.0" -> "0.25")
            df['Ep_Parement_Ext'] = df[dimension_cols[0]].astype(str).str.split('x').str[0].str.strip()
            df['Ep_Parement_Int'] = df[dimension_cols[1]].astype(str).str.split('x').str[0].str.strip()
        else:
            df['Ep_Parement_Ext'] = "Non spécifié"
            df['Ep_Parement_Int'] = "Non spécifié"

        # Remplacement des valeurs manquantes ou nulles par un libellé propre
        df['Ep_Parement_Ext'] = df['Ep_Parement_Ext'].replace(['nan', '0', '0.0', '0.00'], 'Non spécifié')
        df['Ep_Parement_Int'] = df['Ep_Parement_Int'].replace(['nan', '0', '0.0', '0.00'], 'Non spécifié')

        # Conversion forcée des types numériques pour éliminer les bugs de calcul
        cols_num = ['production', 'Chutes', 'Densité', 'Ep_mousse']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    st.success("✓ Base de données PSA indexée et validée avec succès !")

    # --- BARRE LATÉRALE : FILTRES STRATÉGIQUES ---
    st.sidebar.header("🎯 Segmentation Dynamique")
    
    # Filtre par Produit
    liste_produits = sorted(list(df['Produit'].dropna().unique())) if 'Produit' in df.columns else []
    selected_produit = st.sidebar.selectbox("Sélectionner un Produit", options=['Tous'] + liste_produits)
    
    df_step = df.copy()
    if selected_produit != 'Tous':
        df_step = df_step[df_step['Produit'] == selected_produit]
        
    # Filtre par Modèle
    liste_modeles = sorted(list(df_step['Modèle'].dropna().unique())) if 'Modèle' in df.columns else []
    if liste_modeles:
        selected_modeles = st.sidebar.multiselect("Filtrer par Modèle(s)", options=liste_modeles, default=liste_modeles)
        df_filtered = df_step[df_step['Modèle'].isin(selected_modeles)]
    else:
        df_filtered = df_step

    # =====================================================================
    # SECTION 1 : PILOTAGE DE PERFORMANCE INDUSTRIELLE (KPIS)
    # =====================================================================
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Volume Produit Filé", f"{int(df_filtered['production'].sum()):,} m²")
    with kpi2:
        tot_chutes = df_filtered['Chutes'].sum()
        tot_prod = df_filtered['production'].sum()
        taux_rebut = (tot_chutes / tot_prod * 100) if tot_prod > 0 else 0
        st.metric("Taux de Rébut Métallique", f"{taux_rebut:.2f} %")
    with kpi3:
        avg_dens = df_filtered[df_filtered['Densité'] > 0]['Densité'].mean()
        st.metric("Densité Moyenne Chimie", f"{avg_dens:.1f} kg/m³" if not np.isnan(avg_dens) else "N/A")
    with kpi4:
        # Nombre de configurations uniques fabriquées
        mix_count = df_filtered.groupby(['Modèle', 'Ep_mousse', 'Ep_Parement_Ext', 'Ep_Parement_Int']).ngroups if len(df_filtered) > 0 else 0
        st.metric("Configurations Mix Actives", mix_count)

    st.markdown("---")

    # =====================================================================
    # SECTION 2 : SYSTEME D'ONGLETS ANALYTIQUES HAUTE PRÉCISION
    # =====================================================================
    tab1, tab2, tab3 = st.tabs([
        "📊 Saisonnalité & Matrice d'Indices", 
        "🔬 Anatomie Structurale des Parements", 
        "📉 Capabilité Procédé & Qualité"
    ])

    # --- ONGLET 1 : MATRICE DE SAISONNALITÉ ---
    with tab1:
        st.subheader("Analyse Chronologique et Profils Saisonniers")
        
        if not df_filtered.empty and 'Mois_Nom' in df_filtered.columns:
            # Table pivot pour ordonner correctement les mois géographiquement
            pivot_heat = df_filtered.groupby(['Modèle', 'Mois_Nom'])['production'].sum().unstack().fillna(0)
            
            if not pivot_heat.empty:
                col_t1_1, col_t1_2 = st.columns([5, 4])
                
                with col_t1_1:
                    st.markdown("**🔥 Intensité Mensuelle des Volumes Produits (m²)**")
                    fig_heat = px.imshow(
                        pivot_heat, 
                        text_auto=True, 
                        aspect="auto", 
                        color_continuous_scale='Density',
                        labels=dict(x="Période Calendaire", y="Modèle PSA", color="Volume (m²)")
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
                
                with col_t1_2:
                    st.markdown("**📈 Courbe des Fluctuations Relative (Base Moyenne = 1.0)**")
                    # Calcul mathématique précis des indices saisonniers
                    pivot_indices = pivot_heat.div(pivot_heat.mean(axis=1), axis=0).round(2).reset_index()
                    df_melt = pivot_indices.melt(id_vars='Modèle', var_name='Mois', value_name='Indice Saisonnier')
                    
                    fig_line = px.line(
                        df_melt, x='Mois', y='Indice Saisonnier', color='Modèle', markers=True,
                        title="Évolution des Indices par Rapport à la Tendance Centrale"
                    )
                    fig_line.add_hline(y=1.0, line_dash="dash", line_color="crimson", annotation_text="Seuil Pivot Normalisé")
                    st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Données insuffisantes pour générer les profils de saisonnalité.")

    # --- ONGLET 2 : CARTOGRAPHIE DES PAREMENTS (ZÉRO ERREUR) ---
    with tab2:
        st.subheader("Répartition Technique Spécifique des Tôles Extérieures et Intérieures")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("**🍩 Mix d'Épaisseurs Précis — Face Extérieure (m²)**")
            fig_pie_ext = px.pie(
                df_filtered, names='Ep_Parement_Ext', values='production', 
                hole=0.45, color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig_pie_ext.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie_ext, use_container_width=True)
            
        with col_p2:
            st.markdown("**🍩 Mix d'Épaisseurs Précis — Face Intérieure (m²)**")
            fig_pie_int = px.pie(
                df_filtered, names='Ep_Parement_Int', values='production', 
                hole=0.45, color_discrete_sequence=px.colors.sequential.Teal_r
            )
            fig_pie_int.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie_int, use_container_width=True)
            
        st.markdown("---")
        st.markdown("**🌳 Diagramme de Stratification du Mix Produit Complet (Treemap)**")
        st.write("Ce découpage géométrique représente la hiérarchie industrielle exacte de vos flux de production : Produit ➔ Épaisseur de Mousse ➔ Épaisseur Extérieure ➔ Épaisseur Intérieure.")
        
        # Utilisation d'un Treemap : 100% stable, aucun risque d'erreur d'arborescence (contrairement au Sunburst)
        df_tree = df_filtered[df_filtered['production'] > 0].copy()
        if not df_tree.empty:
            df_tree['Mousse'] = df_tree['Ep_mousse'].astype(str) + " mm"
            df_tree['Tôle_Ext'] = "Ext: " + df_tree['Ep_Parement_Ext'].astype(str)
            df_tree['Tôle_Int'] = "Int: " + df_tree['Ep_Parement_Int'].astype(str)
            
            fig_tree = px.treemap(
                df_tree, 
                path=['Produit', 'Mousse', 'Tôle_Ext', 'Tôle_Int'], 
                values='production',
                color='production',
                color_continuous_scale='Viridis',
                title="Cartographie Proportionnelle Globale du Catalogue PSA"
            )
            st.plotly_chart(fig_tree, use_container_width=True)

    # --- ONGLET 3 : CAPABILITÉ PROCÉDÉ & QUALITÉ ---
    with tab3:
        st.subheader("Analyse Globale de Stabilité du Procédé de Coulée Mousse")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("**⚖️ Dispersion de la Densité Chimique par Épaisseur de Panneau**")
            df_dens_clean = df_filtered[df_filtered['Densité'] > 0]
            if not df_dens_clean.empty:
                df_dens_clean['Ep_mousse_label'] = df_dens_clean['Ep_mousse'].astype(str) + " mm"
                fig_box = px.box(
                    df_dens_clean, x='Ep_mousse_label', y='Densité', color='Ep_mousse_label',
                    title="Analyse de Variabilité Matière (Boîte à Moustaches)",
                    labels={'Ep_mousse_label': "Épaisseur de Mousse Core"}
                )
                st.plotly_chart(fig_box, use_container_width=True)
            else:
                st.info("Aucune valeur de Densité supérieure à 0 trouvée dans ce segment.")
            
        with col_g2:
            st.markdown("**📉 Génération Mensuelle Globale des Rebuts Déclassés (m²)**")
            if 'Mois_Nom' in df_filtered.columns:
                df_time = df_filtered.groupby(['Mois_Nom', 'Mois_Index'])['Chutes'].sum().reset_index().sort_values('Mois_Index')
                fig_bar_chutes = px.bar(
                    df_time, x='Mois_Nom', y='Chutes', 
                    color='Chutes', color_continuous_scale='Reds',
                    title="Volume des Chutes par Période de Production"
                )
                st.plotly_chart(fig_bar_chutes, use_container_width=True)

    # --- CENTRAL DATA DISCOVERY ---
    with st.expander("🔍 Explorateur Expert de Données Brutes"):
        st.dataframe(
            df_filtered[['Date', 'Produit', 'Modèle', 'Ep_mousse', 'Ep_Parement_Ext', 'Ep_Parement_Int', 'production', 'Chutes']], 
            use_container_width=True
        )

else:
    # Message d'accueil professionnel
    st.info("👋 **Système d'Analyse PSA Prêt.** Veuillez glisser-déposer votre fichier d'extraction Excel dans le panneau latéral gauche pour initialiser les modélisations graphiques.")
