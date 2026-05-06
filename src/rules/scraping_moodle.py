from bs4 import BeautifulSoup
import pandas as pd

print("--- DEMARRAGE DU SCRAPING MOODLE ---")

nom_fichier = "Résumé Moodle IDU.html"

try:
    with open(nom_fichier, 'r', encoding='utf-8') as f:
        contenu_html = f.read()
except FileNotFoundError:
    print(f"Erreur : Le fichier {nom_fichier} est introuvable.")
    exit()

print("Analyse du code source en cours...")
soup = BeautifulSoup(contenu_html, 'html.parser')
boites_de_cours = soup.find_all('div', class_='coursebox')

liste_des_cours = []

for boite in boites_de_cours:
    # Extraction Titre et Lien
    balise_titre = boite.find('h3', class_='coursename')
    lien_tag = balise_titre.find('a') if balise_titre else None
    titre = lien_tag.text.strip() if lien_tag else "Titre inconnu"
    lien = lien_tag['href'] if lien_tag else "Pas de lien"
    
    # Extraction Categorie
    balise_cat = boite.find('div', class_='coursecat')
    lien_cat = balise_cat.find('a') if balise_cat else None
    categorie = lien_cat.text.strip() if lien_cat else "Non catégorisé"
    
    # Extraction Professeurs 
    balise_profs = boite.find('ul', class_='teachers')
    professeurs = []
    if balise_profs:
        for li in balise_profs.find_all('li'):
            nom_prof = li.find('a').text.strip()
            professeurs.append(nom_prof)
    liste_profs_texte = ", ".join(professeurs) if professeurs else "Aucun professeur renseigné"
            
    # Extraction Description
    balise_resume = boite.find('div', class_='summary')
    description = balise_resume.text.strip() if balise_resume else "Aucune description"
    texte_nettoye = " ".join(description.split())
    
    liste_des_cours.append({
        "Titre_du_Cours": titre,
        "Categorie": categorie,
        "Professeurs": liste_profs_texte,
        "Description": texte_nettoye,
        "Lien_Moodle": lien
    })

# 3. Traitement Pandas (CSV et Statistiques)

df = pd.DataFrame(liste_des_cours)

print(f"\n Extraction réussie : {len(df)} cours trouvés.")

# --- EXPORTATION CSV ---
nom_csv = "Catalogue_Cours_Moodle.csv"
df.to_csv(nom_csv, index=False, encoding='utf-8-sig', sep=';')
print(f" Les données ont été sauvegardées dans le fichier : {nom_csv}")

# --- AFFICHAGE DES STATISTIQUES ---
print("\n========================================")
print(" STATISTIQUES GLOBALES DU SCRAPING")
print("========================================")

# 1. Nombre de cours ayant une description vide
cours_sans_desc = len(df[df['Description'] == "Aucune description"])
pourcentage_sans_desc = round((cours_sans_desc / len(df)) * 100, 1)
print(f"- Cours sans description : {cours_sans_desc} ({pourcentage_sans_desc}%)")

# 2. Nombre de cours sans professeur affecté
cours_sans_prof = len(df[df['Professeurs'] == "Aucun professeur renseigné"])
pourcentage_sans_prof = round((cours_sans_prof / len(df)) * 100, 1)
print(f"- Cours sans professeur affecté : {cours_sans_prof} ({pourcentage_sans_prof}%)")

# 3. Le top 5 des catégories contenant le plus de cours
print("\n- Top 5 des catégories avec le plus de cours :")
top_categories = df['Categorie'].value_counts().head(5)
for nom_cat, nombre in top_categories.items():
    print(f"  * {nom_cat} : {nombre} cours")

print("\n--- FIN DE L'ANALYSE ---")