import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.express as px
import io
import base64

# --- INITIALISATION DE L'APPLICATION DASH ---
# Le thème 'FLATLY' donne un aspect moderne, épuré et professionnel
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # Ligne CRUCIALE pour que Render puisse lancer l'application via Gunicorn

# --- LAYOUT (L'ARCHITECTURE VISUELLE) ---
app.layout = dbc.Container([
    # En-tête principal
    dbc.Row([
        dbc.Col([
            html.H1("🏭 Dashboard de Performance Industrielle — Ligne PSA", className="text-primary mt-4 mb-2 font-weight-bold"),
            html.H5("Analyse Avancée Multi-Dimensionnelle (Version Dash Production)", className="text-muted mb-4")
        ], width=12)
    ]),
    
    # Corps principal : Barre latérale + Zone de visualisation
    dbc.Row([
        # --- BARRE LATÉRALE DE FILTRES ---
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("📂 Importation", className="card-title font-weight-bold"),
                    # Zone d'importation Drag & Drop de Dash
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Glisser-déposer ou ',
                            html.A('sélectionner l\'Excel')
                        ]),
                        style={
                            'width': '100%', 'height': '65px', 'lineHeight': '65px',
                            'borderWidth': '2px', 'borderStyle': 'dashed',
                            'borderRadius': '8px', 'textAlign': 'center', 'margin': '10px 0'
                        },
                        multiple=False
                    ),
                    html.Div(id='output-upload-status', className="text-success font-weight-bold mb-3"),
                    
                    html.Hr(),
                    
                    html.H4("🎯 Segmentation", className="card-title font-weight-bold"),
                    html.Label("Produit Principal :", className="font-weight-bold"),
                    dcc.Dropdown(id='dropdown-produit', options=[{'label': 'Tous', 'value': 'Tous'}], value='Tous', clearable=False, className="mb-3"),
                    
                    html.Label("Modèles PSA :", className="font-weight-bold"),
                    dcc.Dropdown(id='dropdown-modeles', multi=True, placeholder="Sélectionner les modèles...", className="mb-3"),
                ])
            ], color="light")
        ], md=3, className="mb-4"),
        
        # --- CONTENU DYNAMIQUE DES ANALYSES ---
        dbc.Col([
            # Stockage local invisible pour conserver le DataFrame en cache dans le navigateur
            dcc.Store(id='stored-data'),
            
            # Grille d'affichage des 4 indicateurs KPIs
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Volume Produit Filé", className="text-muted"), html.H3(id="kpi-volume", className="text-primary font-weight-bold")]), color="light"), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Taux de Rébut Métallique", className="text-muted"), html.H3(id="kpi-rebut", className="text-danger font-weight-bold")]), color="light"), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Densité Moyenne Chimie", className="text-muted"), html.H3(id="kpi-densite", className="text-success font-weight-bold")]), color="light"), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.H6("Configurations Actives", className="text-muted"), html.H3(id="kpi-mix", className="text-info font-weight-bold")]), color="light"), md=3),
            ], className="mb-4"),
            
            # Système d'onglets pour segmenter les différentes analyses graphiques
            dcc.Tabs(id="tabs-analyses", value='tab-saisonnalite', children=[
                dcc.Tab(label='📊 Saisonnalité & Volumes', value='tab-saisonnalite', className="p-3 font-weight-bold"),
                dcc.Tab(label='🔬 Anatomie des Parements (Metal)', value='tab-parements', className="p-3 font-weight-bold"),
                dcc.Tab(label='📉 Capabilité Chimie & Rebuts', value='tab-qualite', className="p-3 font-weight-bold"),
            ]),
            
            # Conteneur injecté dynamiquement par le Callback
            html.Div(id='tabs-content', className="mt-4")
        ], md=9)
    ])
], fluid=True)


# --- CALLBACK 1 : CHARGEMENT ET PARSING SÉCURISÉ DU FICHIER EXCEL ---
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
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        df = pd.read_excel(io.BytesIO(decoded))
        
        # 1. Traitement temporel des dates
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Mois_Nom'] = df['Date'].dt.strftime('%m - %B')
        else:
            df['Mois_Nom'] = "Non spécifié"

        # 2. Harmonisation et renommage des colonnes critiques
        renames = {'Ep Mousse(la': 'Ep_mousse', 'Ep_mousse': 'Ep_mousse', 'production': 'production', 'Modèle': 'Modèle', 'Produit': 'Produit', 'Densité': 'Densité'}
        df = df.rename(columns={k: v for k, v in renames.items() if k in df.columns})
        
        if 'Chutes EXT' in df.columns:
            df['Chutes'] = df['Chutes EXT']
        elif 'Chutes' in df.columns:
            df['Chutes'] = df['Chutes']
        else:
            df['Chutes'] = 0

        # 3. Extraction par découpage de chaînes des épaisseurs de parements métalliques (ex: '0.6x1000' -> 0.6)
        dimension_cols = [c for c in df.columns if str(c).startswith('Dimension')]
        if len(dimension_cols) >= 2:
            df['Ep_Parement_Ext'] = df[dimension_cols[0]].astype(str).str.split('x').str[0].str.strip()
            df['Ep_Parement_Int'] = df[dimension_cols[1]].astype(str).str.split('x').str[0].str.strip()
        else:
            df['Ep_Parement_Ext'] = "Non spécifié"
            df['Ep_Parement_Int'] = "Non spécifié"

        df['Ep_Parement_Ext'] = df['Ep_Parement_Ext'].replace(['nan', '0', '0.0', '0.00'], 'Non spécifié')
        df['Ep_Parement_Int'] = df['Ep_Parement_Int'].replace(['nan', '0', '0.0', '0.00'], 'Non spécifié')

        # Conversion et nettoyage numérique pour éviter les plantages
        cols_num = ['production', 'Chutes', 'Densité', 'Ep_mousse']
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # Remplissage dynamique des filtres de la barre latérale
        produits = sorted(list(df['Produit'].dropna().unique())) if 'Produit' in df.columns else []
        options_produit = [{'label': 'Tous', 'value': 'Tous'}] + [{'label': p, 'value': p} for p in produits]
        
        modeles = sorted(list(df['Modèle'].dropna().unique())) if 'Modèle' in df.columns else []
        options_modeles = [{'label': m, 'value': m} for m in modeles]
        
        # Sauvegarde au format JSON structuré
        return df.to_json(date_format='iso', orient='split'), f"✓ {filename} indexé !", options_produit, options_modeles, modeles

    except Exception as e:
        return dash.no_update, "❌ Fichier incompatible ou corrompu.", dash.no_update, dash.no_update, dash.no_update


# --- CALLBACK 2 : FILTRAGE MULTI-CRITÈRES ET RE-CALCUL DES GRAPHIQUES ---
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
        return "0 m²", "0.00 %", "N/A", "0", html.Div(dbc.Alert("Veuillez charger votre fichier Excel pour activer l'analyse.", color="info", className="mt-3"))

    # Extraction du DataFrame depuis le cache local
    df = pd.read_json(json_data, orient='split')
    
    # Application des filtres en cascade
    if selected_produit != 'Tous':
        df = df[df['Produit'] == selected_produit]
    if selected_modeles:
        df = df[df['Modèle'].isin(selected_modeles)]
        
    if df.empty:
        return "0 m²", "0.00 %", "N/A", "0", html.Div("Aucune ligne de production ne correspond à ces filtres.")

    # 1. Calculs mathématiques des indicateurs de performance (KPIs)
    tot_prod = df['production'].sum()
    tot_chutes = df['Chutes'].sum()
    taux_rebut = (tot_chutes / tot_prod * 100) if tot_prod > 0 else 0
    avg_dens = df[df['Densité'] > 0]['Densité'].mean()
    mix_count = df.groupby(['Modèle', 'Ep_mousse', 'Ep_Parement_Ext', 'Ep_Parement_Int']).ngroups

    kpi_vol_str = f"{int(tot_prod):,} m²"
    kpi_reb_str = f"{taux_rebut:.2f} %"
    kpi_den_str = f"{avg_dens:.1f} kg/m³" if not np.isnan(avg_dens) else "N/A"
    kpi_mix_str = str(mix_count)

    # 2. Construction dynamique de l'onglet sélectionné
    if active_tab == 'tab-saisonnalite':
        pivot_heat = df.groupby(['Modèle', 'Mois_Nom'])['production'].sum().unstack().fillna(0)
        if not pivot_heat.empty:
            fig_heat = px.imshow(pivot_heat, text_auto=True, aspect="auto", color_continuous_scale='Blues')
            fig_heat.update_layout(margin=dict(l=20, r=20, t=30, b=20))
            
            content = dbc.Row([
                dbc.Col([html.H5("🔥 Carte de Chaleur Mensuelle des Productions (m²)", className="text-secondary font-weight-bold mt-2"), dcc.Graph(figure=fig_heat)], md=12)
            ])
        else:
            content = html.Div("Données temporelles incomplètes pour générer la matrice.")

    elif active_tab == 'tab-parements':
        fig_pie_ext = px.pie(df, names='Ep_Parement_Ext', values='production', hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_pie_int = px.pie(df, names='Ep_Parement_Int', values='production', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal_r)
        
        df_tree = df[df['production'] > 0].copy()
        df_tree['Mousse'] = df_tree['Ep_mousse'].astype(str) + " mm"
        fig_tree = px.treemap(df_tree, path=['Produit', 'Mousse', 'Ep_Parement_Ext', 'Ep_Parement_Int'], values='production', color='production', color_continuous_scale='Viridis')

        content = html.Div([
            dbc.Row([
                dbc.Col([html.H5("🍩 Répartition Épaisseurs Face Extérieure", className="text-secondary font-weight-bold"), dcc.Graph(figure=fig_pie_ext)], md=6),
                dbc.Col([html.H5("🍩 Répartition Épaisseurs Face Intérieure", className="text-secondary font-weight-bold"), dcc.Graph(figure=fig_pie_int)], md=6)
            ], className="mb-4"),
            html.Hr(),
            html.H5("🌳 Diagramme de Stratification Logistique (Catalogue Technique)", className="text-secondary font-weight-bold"),
            dcc.Graph(figure=fig_tree)
        ])

    elif active_tab == 'tab-qualite':
        df_dens_clean = df[df['Densité'] > 0].copy()
        if not df_dens_clean.empty:
            df_dens_clean['Mousse_Label'] = df_dens_clean['Ep_mousse'].astype(str) + " mm"
            fig_box = px.box(df_dens_clean, x='Mousse_Label', y='Densité', color='Mousse_Label', title="Dispersion par classe d'épaisseur")
        else:
            fig_box = px.express.line(title="Aucune mesure de densité trouvée")

        df_time = df.groupby(['Mois_Nom'])['Chutes'].sum().reset_index()
        fig_bar_chutes = px.bar(df_time, x='Mois_Nom', y='Chutes', color='Chutes', color_continuous_scale='Reds', title="Volume de chutes mensuel")

        content = dbc.Row([
            dbc.Col([html.H5("⚖️ Analyse de Capabilité & Stabilité de la Densité Chimie", className="text-secondary font-weight-bold"), dcc.Graph(figure=fig_box)], md=6),
            dbc.Col([html.H5("📉 Évolution des Chutes Métalliques (m²)", className="text-secondary font-weight-bold"), dcc.Graph(figure=fig_bar_chutes)], md=6)
        ])

    return kpi_vol_str, kpi_reb_str, kpi_den_str, kpi_mix_str, content


# --- DÉMARRAGE DU SERVEUR COMPATIBLE AVEC TOUS LES CLOUDS ---
if __name__ == '__main__':
    # Configuration réseau requise pour Render (port 8050)
    app.run(host='0.0.0.0', port=8050, debug=False)
