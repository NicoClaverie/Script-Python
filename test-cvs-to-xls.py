import pandas as pd
import re

# Fonction pour nettoyer les noms d'onglets (limite Excel de 31 caractères)
def clean_sheet_name(name):
    name = re.sub(r'[\\/*?:[\]]', '', str(name))
    return name[:31]

# 1. Chargement
df = pd.read_csv('ressource\\match.csv')

# 2. Filtrage des colonnes
keep_cols = ['Site', 'Société', 'Nom Micro', 'LIBELLE', 'ETAT', 'NUMERO', 'N° Série', 'UTILISATEUR',  ]
df_filtered = df[keep_cols].copy()

# 3. Création de la colonne combinée
df_filtered['Site_Societe'] = df_filtered['Site'].astype(str) + " - " + df_filtered['Société'].astype(str)

# 1. On récupère les listes et on les trie par ordre alphabétique
unique_libelles = sorted([str(l) for l in df_filtered['LIBELLE'].unique() if pd.notna(l)])
unique_sites_socs = sorted([str(ss) for ss in df_filtered['Site_Societe'].unique() if pd.notna(ss) and ss != "nan - nan"])

# 2. On boucle sur ces listes triées pour créer les onglets
with pd.ExcelWriter('Fichier_B_Trie.xlsx', engine='openpyxl') as writer:
    # Les onglets de libellés apparaîtront en premier, triés
    for lib in unique_libelles:
        sheet_name = clean_sheet_name(lib)
        subset = df_filtered[df_filtered['LIBELLE'] == lib][keep_cols]
        subset.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # Puis les onglets Site-Société, triés aussi
    for ss in unique_sites_socs:
        sheet_name = clean_sheet_name(ss)
        subset = df_filtered[df_filtered['Site_Societe'] == ss][keep_cols]
        subset.to_excel(writer, sheet_name=sheet_name, index=False)