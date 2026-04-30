import json
import pandas as pd

print("--- DEBUT DE L'ANALYSE GLOBALE (IDU 3, 4 et 5) ---")


# 1. OUVERTURE ET FUSION DES FICHIERS
print("Ouverture et fusion des fichiers...")

# Chargement du fichier des regles
with open('dependance_sequence_IDU.json', 'r', encoding='utf-8') as fichier_regles:
    donnees_brutes_regles = json.load(fichier_regles)

# Liste des 3 emplois du temps a analyser
noms_fichiers_ade = ['ADECal_IDU3.json', 'ADECal_IDU4.json', 'ADECal_IDU5.json']
donnees_ade_totales = []

# On ouvre chaque fichier un par un et on ajoute son contenu a notre grande liste
for nom_fichier in noms_fichiers_ade:
    with open(nom_fichier, 'r', encoding='utf-8') as f:
        donnees_ade_totales.extend(json.load(f))

print(f"J'ai charge un total de {len(donnees_ade_totales)} seances dans l'emploi du temps global.")

# 2. CHERCHER LA BONNE TABLE DE REGLES

vraies_regles = []
for bloc in donnees_brutes_regles:
    if bloc.get('name') == 'MAQUETTE_dependance_sequence':
        vraies_regles = bloc.get('data', [])
        break

# 3. FAIRE LA LISTE DES MATIERES A VERIFIER
liste_des_matieres = []
for regle in vraies_regles:
    nom_matiere = regle.get('module_precedent')
    
    if nom_matiere not in liste_des_matieres:
        liste_des_matieres.append(nom_matiere)

print(f"J'ai trouve {len(liste_des_matieres)} matieres a verifier.\n")

carnet_erreurs = []

# 4. VERIFIER CHAQUE MATIERE UNE PAR UNE
for matiere in liste_des_matieres:
    mot_cle_recherche = matiere.split('_')[0] 
    
    regles_de_la_matiere = []
    for regle in vraies_regles:
        if regle.get('module_precedent') == matiere:
            regles_de_la_matiere.append(regle)
            
    cours_trouves = []
    
    for evenement in donnees_ade_totales:
        titre = evenement.get('Title', '')
        description = evenement.get('Description', '')
        
        if mot_cle_recherche in titre or mot_cle_recherche in description:
            titre_majuscule = titre.upper()
            if 'CM' in titre_majuscule:
                type_de_cours = 'CM'
            elif 'TD' in titre_majuscule:
                type_de_cours = 'TD'
            elif 'TP' in titre_majuscule:
                type_de_cours = 'TP'
            else:
                type_de_cours = 'INCONNU'
                
            cours_trouves.append({
                'titre': titre,
                'debut': pd.to_datetime(evenement['Starts']),
                'type_seance': type_de_cours
            })
            
    tableau_cours = pd.DataFrame(cours_trouves)
    
    if tableau_cours.empty:
        print(f"Ignore : {matiere} (Aucun cours trouve)")
        continue
        
    tableau_cours = tableau_cours.sort_values(by='debut').reset_index(drop=True)
    
    compteurs = {'CM': 1, 'TD': 1, 'TP': 1, 'INCONNU': 1, 'Exam': 1, 'PROJ': 1}
    liste_des_numeros = []
    
    for index, ligne in tableau_cours.iterrows():
        type_actuel = ligne['type_seance']
        liste_des_numeros.append(compteurs[type_actuel])
        compteurs[type_actuel] = compteurs[type_actuel] + 1
        
    tableau_cours['numero'] = liste_des_numeros

    erreurs_trouvees = 0
    for regle in regles_de_la_matiere:
        type_avant = regle['type_precedent']
        numero_avant = int(regle['numero_precedent'])
        
        type_apres = regle['type_suivant']
        numero_apres = int(regle['numero_suivant'])
        
        cours_avant = tableau_cours[(tableau_cours['type_seance'] == type_avant) & (tableau_cours['numero'] == numero_avant)]
        cours_apres = tableau_cours[(tableau_cours['type_seance'] == type_apres) & (tableau_cours['numero'] == numero_apres)]
        
        if not cours_avant.empty and not cours_apres.empty:
            date_avant = cours_avant.iloc[0]['debut']
            date_apres = cours_apres.iloc[0]['debut']
            
            if date_apres < date_avant:
                erreurs_trouvees = erreurs_trouvees + 1
                
                # Affichage de l'erreur dans le terminal
                print(f"  -> ERREUR {matiere} : Le {type_avant} {numero_avant} ({date_avant}) a ete mis APRES le {type_apres} {numero_apres} ({date_apres})")
                
                carnet_erreurs.append({
                    "Code Module": matiere,
                    "Type Erreur": "Ordre chronologique non respecte",
                    "Regle cassee": f"Le {type_avant} {numero_avant} devait etre avant le {type_apres} {numero_apres}",
                    "Date du premier cours": str(date_avant),
                    "Date du second cours": str(date_apres)
                })
                
    if erreurs_trouvees == 0:
        print(f"OK : {matiere}")
    else:
        print(f"ERREUR : {matiere} ({erreurs_trouvees} problemes chronologiques)")

# 5. CREATION DU FICHIER EXCEL
print("\n--- CREATION DU RAPPORT EXCEL ---")

if len(carnet_erreurs) > 0:
    tableau_final = pd.DataFrame(carnet_erreurs)
    nom_fichier = "Rapport_Anomalies_Sequencement_Global.xlsx"
    tableau_final.to_excel(nom_fichier, index=False)
    print(f"Termine. J'ai enregistre {len(carnet_erreurs)} erreurs dans le fichier Excel : {nom_fichier}.")
else:
    print("Termine. Tout est parfait, aucune erreur trouvee.")