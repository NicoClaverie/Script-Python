import csv

with open("ressource\\Fichier-A.csv", "r", encoding="utf-8") as csv_file:
    csv_A = csv.DictReader(csv_file)
    dataA =[]
    for line in csv_A:
        NumSerie = line ['N° de série']
        NumSerie = NumSerie.replace(" ", "")
        line ['N° de série'] = NumSerie
        dataA.append(line)
        #print(line)
#print(dataA)

with open("ressource\\Fichier-B.csv", "r", encoding="utf-8") as csv_file:
    
    csv_B = csv.DictReader(csv_file) 
    dataB = []

    for line in csv_B:
        NumSerie = line ['N° Série']
        NumSerie = NumSerie.strip().lstrip('.')
        line ['N° Série'] = NumSerie
        dataB.append(line)
        #print(line)
#print(dataB)

set_A = {line['N° de série'] for line in dataA}

liste_match = []

for lineB in dataB:
    numeroA = lineB['N° Série']
    if numeroA in set_A:
        liste_match.append(lineB)
        #print("true")
    #else:
        #print("false")

set_B = {line['N° Série'] for line in dataB}

liste_no_match = []

for lineA in dataA:
    numeroB = lineA['N° de série']
    if numeroB not in set_B:
        liste_no_match.append(lineA)
        #print("true")
    #else:
        #print("false")






with open("ressource\\match.csv", "w", encoding="utf-8", newline="") as csv_file:
    # Définition les noms de colonnes (en-tête du CSV)
    fieldnames = ["LIBELLE", "Nom Micro", "ETAT", "MARQUE", "NUMERO", "N° Série", "ADRESSE IP", "VUE", "UTILISATEUR", "Password", "Spare", "Fait", "CTR", "Société", "Site", "LN", "Office", "Accord", "Service", "Facture", "Modele UC", "Date Installation"]
    
    csv_dict_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    
    # Écriture de la ligne d’en-tête
    csv_dict_writer.writeheader()
    
    # Écriture de chaque ligne de données
    for line in liste_match:
        csv_dict_writer.writerow(line)


with open("ressource\\no_match.csv", "w", encoding="utf-8", newline="") as csv_file:
    # Définition les noms de colonnes (en-tête du CSV)
    fieldnames = ["N° du contrat de location", "Annexe", "Fin du contrat", "N° de série", "Fabriquant", "Modèle", "Catégorie"]
    
    csv_dict_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    
    # Écriture de la ligne d’en-tête
    csv_dict_writer.writeheader()
    
    # Écriture de chaque ligne de données
    for line in liste_no_match:
        csv_dict_writer.writerow(line)