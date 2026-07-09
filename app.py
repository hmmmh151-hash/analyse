import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- CONFIGURATION INTERFACE (Stabilité maximale) ---
st.set_page_config(page_title="PSA Dashboard Pro", layout="wide")

st.title("🏭 Dashboard de Performance Industrielle — Ligne PSA")
st.markdown("### Analyse Avancée Multi-Dimensionnelle")

# --- BARRE LATÉRALE ---
st.sidebar.header("📂 Importation des Données")
uploaded_file = st.sidebar.file_uploader("Charger le fichier Excel de production PSA", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner('Extraction analytique des données en cours...'):
        df = pd.read_excel(uploaded_file)
        
        # 1. Normalisation des dates
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Mois_Nom'] = df['Date'].dt.strftime('%m - %B')
        else:
            df['Mois_Nom'] = "Non spécifié"

        # 2. Harmonisation des noms de colonnes clés
        renames = {'Ep Mousse(la': 'Ep_mousse', 'Ep_mousse': 'Ep_mousse', 'production': 'production', 'Modèle': 'Modèle', 'Produit': 'Produit', 'Densité': 'Densité'}
        df = df.rename(columns={k: v for k, v in renames.items() if k in df.columns})
        
        if 'Chutes EXT' in df.columns:
            df['Chutes'] = df['Chutes EXT']
        elif 'Chutes' in df.columns:
            df['Chutes'] = df['Chutes']
        else:
            df['Chutes'] = 0

        # 3. Extraction Robuste des Parements (Pattern Matching sur "Dimension")
        dimension_cols = [c for c in df.columns if str(c).startswith('Dimension')]
        if len(dimension_cols) >= 2:
            df['Ep_Parement_Ext'] = df[dimension_cols[0]].astype(str).str.split('x').str[0].str.strip()
            df['Ep_Parement_Int'] = df[dimension_cols[1]].astype(str).str.split('x').str[0].str.strip()
        else:
            df['Ep_Parement_Ext'] = "Non spécifié"
            df['Ep_Parement_Int'] = "Non spécifié"

        df['Ep_Parement_Ext'] = df['Ep_Parement_Ext'].replace(['nan', '0', '0.0', '0.00'], 'Non spécifié')
        df['Ep_Parement_Int'] = df['Ep_Parement_Int'].replace(['nan', '0', '0.0', '0.00'], 'Non spécifié')

        cols_num = ['production', 'Chutes', 'Densité', 'Ep_mousse']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    st.success("✓ Base de données PSA indexée avec succès !")

    # --- FILTRES ---
    liste_produits = sorted(list(df['Produit'].dropna().unique())) if 'Produit' in df.columns else []
    selected_produit = st.sidebar.selectbox("Sélectionner un Produit", options=['Tous'] + liste_produits)
    
    df_filtered = df.copy()
    if selected_produit != 'Tous':
        df_filtered = df_filtered[df_filtered['Produit'] == selected_produit]

    # --- AFFICHAGE KPIS ---
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Volume Produit Filé", f"{int(df_filtered['production'].sum()):,} m²")
    with k2:
        tot_chutes = df_filtered['Chutes'].sum()
        tot_prod = df_filtered['production'].sum()
        taux_rebut = (tot_chutes / tot_prod * 100) if tot_prod > 0 else 0
        st.metric("Taux de Rébut Métallique", f"{taux_rebut:.2f} %")
    with k3:
        avg_dens = df_filtered[df_filtered['Densité'] > 0]['Densité'].mean()
        st.metric("Densité Moyenne Chimie", f"{avg_dens:.1f} kg/m³" if not np.isnan(avg_dens) else "N/A")

    # --- SYSTEME D'ONGLETS ---
    tab1, tab2 = st.tabs(["🔬 Épaisseurs des Parements", "📊 Saisonnalité & Chutes"])
    
    with tab1:
