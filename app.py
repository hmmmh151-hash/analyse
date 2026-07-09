import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

print("⚡ Démarrage de l'analyse approfondie de la saisonnalité PSA...")

# Configuration des graphiques
sns.set_theme(style="whitegrid")

# Chemins d'accès automatiques (dossier Téléchargements)
dossier_telechargements = os.path.join(os.path.expanduser("~"), "Downloads")
file_path = os.path.join(dossier_telechargements, "History Prod PSA 2025.xlsx")
output_excel = os.path.join(dossier_telechargements, "Rapport_Saisonnalite_Detaille_PSA.xlsx")

# Chargement du fichier
try:
    df = pd.read_excel(file_path)
    print("✓ Fichier PSA historique chargé avec succès !")
except Exception as e:
    print(f"❌ Erreur : Impossible de trouver ou lire 'History Prod PSA 2025.xlsx' dans tes Téléchargements.\nDétails : {e}")
    input("\nAppuie sur Entrée pour quitter...")
    exit()

# Nettoyage et préparation des dates
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df['Mois_Nom'] = df['Date'].dt.strftime('%m - %B')

# Harmonisation des colonnes d'après ton fichier réel
renommage = {
    'Ep Mousse(la': 'Ep_mousse',
    'Ep_mousse': 'Ep_mousse',
    'production': 'production',
    'Chutes': 'Chutes',
    'Densité': 'Densité'
}
df = df.rename(columns=renommage)

# Forcer les types numériques
cols_num = ['production', 'Chutes', 'Densité', 'Ep_mousse']
for c in cols_num:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

# =====================================================================
# CALCUL DE LA SAISONNALITÉ PAR PRODUIT x MODÈLE x ÉPAISSEUR
# =====================================================================
print("📈 Calcul des indices de saisonnalité granulaires...")

# Volumes bruts cumulés par mois
pivot_vol = df.groupby(['Produit', 'Modèle', 'Ep_mousse', 'Mois_Nom'])['production'].sum().unstack().fillna(0)

# Moyenne annuelle de chaque configuration spécifique
moyennes_configurations = pivot_vol.mean(axis=1)

# Calcul de l'indice (Mois / Moyenne)
pivot_indices = pivot_vol.div(moyennes_configurations, axis=0).round(2)

# =====================================================================
# EXPORT DES RÉSULTATS DANS UN NOUVEAU FICHIER EXCEL
# =====================================================================
print("💾 Génération du fichier Excel de synthèse...")
try:
    with pd.ExcelWriter(output_excel) as writer:
        pivot_vol.to_excel(writer, sheet_name='Volumes Bruts m²')
        pivot_indices.to_excel(writer, sheet_name='Indices de Saisonnalité')
    print(f"✓ Le fichier Excel détaillé a été créé : Rapport_Saisonnalite_Detaille_PSA.xlsx")
except Exception as e:
    print(f"⚠️ Erreur lors de l'écriture Excel : {e}")

# =====================================================================
# CRÉATION DES GRAPHIQUES ET SAUVEGARDE EN IMAGES
# =====================================================================
print("📊 Génération des graphiques analytiques...")

# Graphique 1 : Top 5 des configurations les plus produites
try:
    plt.figure(figsize=(14, 7))
    top_configurations = pivot_vol.sum(axis=1).nlargest(5).index
    for config in top_configurations:
        plt.plot(pivot_indices.columns, pivot_indices.loc[config], marker='o', 
                 label=f"{config[0]} - {config[1]} - {config[2]}mm")
    
    plt.axhline(y=1.0, color='r', linestyle='--', alpha=0.6, label='Moyenne de référence (1.0)')
    plt.title("Profil Saisonnier des 5 Principaux Segments PSA (2025)", fontsize=14, fontweight='bold')
    plt.xlabel("Mois")
    plt.ylabel("Indice Saisonnier du Segment")
    plt.xticks(rotation=35)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.tight_layout()
    plt.savefig(os.path.join(dossier_telechargements, "graphique_saisonnalite_segments.png"))
    plt.close()
    print("✓ Graphique de saisonnalité enregistré (graphique_saisonnalite_segments.png)")
except Exception as e:
    print(f"Échec graphique 1 : {e}")

# Graphique 2 : Boite à moustaches de la Densité par type de Mousse
if 'Mousse' in df.columns and 'Densité' in df.columns:
    try:
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=df[df['Densité'] > 0], x='Mousse', y='Densité', palette='Set2')
        plt.title("Analyse de la Stabilité de la Densité de Mousse en Production")
        plt.ylabel("Densité (kg/m³)")
        plt.tight_layout()
        plt.savefig(os.path.join(dossier_telechargements, "graphique_stabilite_densite.png"))
        plt.close()
        print("✓ Graphique de stabilité matière enregistré (graphique_stabilite_densite.png)")
    except Exception as e:
        print(f"Échec graphique 2 : {e}")

print("\n=====================================================================")
print("⭐ ANALYSE TERMINÉE AVEC SUCCÈS !")
print("Regarde dans ton dossier 'Téléchargements', tu y trouveras :")
print("  1. Le fichier Excel : Rapport_Saisonnalite_Detaille_PSA.xlsx")
print("  2. L'image de la saisonnalité : graphique_saisonnalite_segments.png")
print("  3. L'image de contrôle qualité : graphique_stabilite_densite.png")
print("=====================================================================")
input("\nAppuie sur Entrée pour fermer cette fenêtre...")