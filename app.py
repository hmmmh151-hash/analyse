import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.express as px
import io
import base64

# --- INITIALISATION DE L'APPLICATION DASH ---
# On utilise un thème Bootstrap moderne (FLATLY)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # Nécessaire pour le déploiement sur le Cloud

# --- LAYOUT (L'ARCHITECTURE VISUELLE) ---
app.layout = dbc.Container([
    # En-tête principal
    dbc.Row([
        dbc.Col([
            html.H1("🏭 Dashboard de Performance Industrielle — Ligne PSA", className="text-primary mt-4 mb-2 font-weight-bold"),
            html.H5("Analyse Avancée Multi-Dimensionnelle (Version Dash Haute Performance)", className="text-muted mb-4")
        ], width=12)
    ]),
    
    # Corps principal : Barre latérale + Contenu
    dbc.Row([
        # --- BARRE LATÉRALE ---
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("📂 Importation", className="card-title font-weight-bold"),
                    # Composant d'importation de fichier propre à Dash
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Glisser-déposer ou ',
                            html.A('sélectionner le fichier Excel')
                        ]),
                        style={
                            'width': '100%', 'height': '60px', 'lineHeight': '60px',
                            'borderWidth': '2px', 'borderStyle': 'dashed',
                            'borderRadius': '8px', 'textAlign': 'center', 'margin': '10px 0'
                        },
                        multiple=False
                    ),
                    html.Div(id='output-upload-status', className="text-success font-weight-bold mb-3"),
                    
                    html.Hr(),
                    
                    html.H4("🎯 Segmentation", className="card-title font-weight-bold"),
                    html.Label("Produit Principal :"),
                    dcc.Dropdown(id='dropdown-produit', options=[{'label': 'Tous', 'value': 'Tous'}], value='Tous', clearable=False, className="mb-3"),
                    
                    html.Label("Modèles PSA :"),
                    dcc.Dropdown(id='dropdown-modeles', multi=True, placeholder="Sélectionner les modèles...", className="mb-3"),
                ])
            ], color="light")
        ], md=3, className="mb-4"),
        
        # --- CONTENU DE L'APPLICATION ---
        dbc.Col([
            # Zone invisible pour stocker les données brutes lues (Format JSON)
            dcc.Store(id='stored-data'),
            
            # Grille des KPIs
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Volume Produit Filé", className="text-muted"), html.H3(id="kpi-volume", className="text-primary font-weight-bold")]), color="light"), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Taux de Rébut Métallique", className="text-muted"), html.H3(id="kpi-rebut", className="text-danger font-weight-bold")]), color="light"), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Densité Moyenne Chimie", className="text-muted"), html.H3(id="kpi-densite", className="text-success font-weight-bold")]), color="light"), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Configurations Actives", className="text-muted"), html.H3(id="kpi-mix", className="text-info font-weight-bold")]), color="light"), md=3),
            ], className="mb-4"),
            
            # Système d'onglets de Dash
            dcc.Tabs(id="tabs-analyses", value='tab-saisonnalite', children=[
                dcc.Tab(label='📊 Saisonnalité & Matrice d\'Indices', value='tab-saisonnalite', className="p-3"),
                dcc.Tab(label='🔬 Anatomie Structurale des Parements', value='tab-parements', className="p-3"),
                dcc.Tab(label='📉 Capabilité Procédé & Qualité', value='tab-qualite', className="p-3"),
            ], className="custom-tabs"),
            
            # Conteneur dynamique où les graphiques s'afficheront selon l'onglet actif
            html.Div(id='tabs-content', className="mt-4")
        ], md=9)
    ])
], fluid=True)

# --- CALLBACK 1 : LECTURE DU FICHIER EXCEL ET ALIMENTATION DES FILTRES ---
@app.callback(
    Output('stored-data', 'data'),
    Output('output-upload-status', 'children'),
    Output('dropdown-produit', 'options'),
    Output('dropdown-modeles', 'options'),
    Output('dropdown-modeles', 'value'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def parse_excel(contents, filename):
    if contents is None:
        return dash.no_update
    
    # Décodage du fichier chargé
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        df = pd.read_excel(io.BytesIO(decoded))
        
        # 1. Traitement des dates
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Mois_Index'] = df['Date'].dt.month
            df['Mois_Nom'] = df['Date'].dt.strftime('%m - %B')
        else:
            df['Mois_Index'] = 1
            df['Mois_Nom'] = "Non spécifié"

        # 2. Harmonisation des colonnes numériques
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

        # Remplissage des options des menus déroulants
        produits = sorted(list(df['Produit'].dropna().unique())) if 'Produit' in df.columns else []
        options_produit = [{'label': 'Tous', 'value': 'Tous'}] + [{'label': p, 'value': p} for p in produits]
        
        modeles = sorted(list(df['Modèle'].dropna().unique())) if 'Modèle' in df.columns else []
        options_modeles = [{'label': m, 'value': m} for m in modeles]
        
        status_msg = f"✓ {filename} analysé avec succès !"
        
        # On sauvegarde le DataFrame converti en JSON dans la mémoire temporaire du navigateur
        return df.to_json(date_format='iso', orient='split'), status_msg, options_produit, options_modeles, modeles

    except Exception as e:
        return dash.no_update, "❌ Erreur de lecture du fichier.", dash.no_update, dash.no_update, dash.no_update


# --- CALLBACK 2 : FILTRAGE DES DONNÉES ET MISE À JOUR DES KPIS / ONGLETS ---
@app.callback(
    Output('kpi-volume', 'children'),
    Output('kpi-rebut', 'children'),
    Output('kpi-densite', 'children'),
    Output('kpi-mix', 'children'),
    Output('tabs-content', 'children'),
    Input('stored-data', 'data'),
    Input('dropdown-produit', 'value'),
    Input('dropdown-modeles', 'value'),
    Input('tabs-analyses', 'value')
)
def update_dashboard(json_data, selected_produit, selected_modeles, active_tab):
    if json_data is None:
        return "0 m²", "0.00 %", "N/A", "0", html.Div(dbc.Alert("Veuillez importer un fichier Excel pour démarrer l'analyse.", color="info"))

    # Rechargement du DataFrame depuis la mémoire cache
    df = pd.read_json(json_data, orient='split')
    
    # Application des filtres en cascade
    if selected_produit != 'Tous':
        df = df[df['Produit'] == selected_produit]
    if selected_modeles:
        df = df[df['Modèle'].isin(selected_modeles)]
        
    if df.empty:
        return "0 m²", "0.00 %", "N/A", "0", html.Div("Aucune donnée disponible pour ces filtres.")

    # 1. Calculs mathématiques pour les KPIs
    tot_prod = df['production'].sum()
    tot_chutes = df['Chutes'].sum()
    taux_rebut = (tot_chutes / tot_prod * 100) if tot_prod > 0 else 0
    avg_dens = df[df['Densité'] > 0]['Densité'].mean()
    mix_count = df.groupby(['Modèle', 'Ep_mousse', 'Ep_Parement_Ext', 'Ep_Parement_Int']).ngroups

    kpi_vol_str = f"{int(tot_prod):,} m²"
    kpi_reb_str = f"{taux_rebut:.2f} %"
    kpi_den_str = f"{avg_dens:.1f} kg/m³" if not np.isnan(avg_dens) else "N/A"
    kpi_mix_str = str(mix_count)

    # 2. Rendu dynamique du contenu selon l'onglet actif (Génération des graphiques Plotly)
    if active_tab == 'tab-saisonnalite':
        pivot_heat = df.groupby(['Modèle', 'Mois_Nom'])['production'].sum().unstack().fillna(0)
        if not pivot_heat.empty:
            fig_heat = px.imshow(pivot_heat, text_auto=True, aspect="auto", color_continuous_scale='Density')
            
            pivot_indices = pivot_heat.div(pivot_heat.mean(axis=1), axis=0).round(2).reset_index()
            df_melt = pivot_indices.melt(id_vars='Modèle', var_name='Mois', value_name='Indice Saisonnier')
            fig_line = px.line(df_melt, x='Mois', y='Indice Saisonnier', color='Modèle', markers=True)
            fig_line.add_hline(y=1.0, line_dash="dash", line_color="crimson")
            
            content = dbc.Row([
                dbc.Col([html.H5("🔥 Carte de Chaleur Mensuelle (m²)"), dcc.Graph(figure=fig_heat)], md=7),
                dbc.Col([html.H5("📈 Indices Saisonniers Matriciels"), dcc.Graph(figure=fig_line)], md=5)
            ])
        else:
            content = html.Div("Données de saisonnalité indisponibles.")

    elif active_tab == 'tab-parements':
        fig_pie_ext = px.pie(df, names='Ep_Parement_Ext', values='production', hole=0.45, color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_pie_int = px.pie(df, names='Ep_Parement_Int', values='production', hole=0.45, color_discrete_sequence=px.colors.sequential.Teal_r)
        
        # Utilisation du Treemap pour une stabilité structurelle absolue
        df_tree = df[df['production'] > 0].copy()
        df_tree['Mousse'] = df_tree['Ep_mousse'].astype(str) + " mm"
        df_tree['Tôle_Ext'] = "Ext: " + df_tree['Ep_Parement_Ext'].astype(str)
        df_tree['Tôle_Int'] = "Int: " + df_tree['Ep_Parement_Int'].astype(str)
        fig_tree = px.treemap(df_tree, path=['Produit', 'Mousse', 'Tôle_Ext', 'Tôle_Int'], values='production', color='production', color_continuous_scale='Viridis')

        content = html.Div([
            dbc.Row([
                dbc.Col([html.H5("🍩 Répartition Face Extérieure"), dcc.Graph(figure=fig_pie_ext)], md=6),
                dbc.Col([html.H5("🍩 Répartition Face Intérieure"), dcc.Graph(figure=fig_pie_int)], md=6)
            ], className="mb-4"),
            html.Hr(),
            html.H5("🌳 Diagramme de Stratification Global (Catalogue & Flux PSA)"),
            dcc.Graph(figure=fig_tree)
        ])

    elif active_tab == 'tab-qualite':
        df_dens_clean = df[df['Densité'] > 0].copy()
        if not df_dens_clean.empty:
            df_dens_clean['Ep_mousse_label'] = df_dens_clean['Ep_mousse'].astype(str) + " mm"
            fig_box = px.box(df_dens_clean, x='Ep_mousse_label', y='Densité', color='Ep_mousse_label')
        else:
            fig_box = px.express.line(title="Aucune densité disponible")

        df_time = df.groupby(['Mois_Nom'])['Chutes'].sum().reset_index()
        fig_bar_chutes = px.bar(df_time, x='Mois_Nom', y='Chutes', color='Chutes', color_continuous_scale='Reds')

        content = dbc.Row([
            dbc.Col([html.H5("⚖️ Capabilité & Dispersion de la Densité Chimie"), dcc.Graph(figure=fig_box)], md=6),
            dbc.Col([html.H5("📉 Génération Mensuelle des Chutes Industrielles (m²)"), dcc.Graph(figure=fig_bar_chutes)], md=6)
        ])

    return kpi_vol_str, kpi_reb_str, kpi_den_str, kpi_mix_str, content

# --- DÉMARRAGE DU SERVEUR ---
if __name__ == '__main__':
    app.run_server(debug=False)
