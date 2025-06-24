# 📊 S&P 500 – Analyse des Rendements Saisonniers

Cette application Streamlit permet d’analyser les rendements saisonniers des actions du S&P 500 entre deux dates spécifiques, sur un nombre d’années défini.

## Fonctionnalités

- Téléchargement automatique des données boursières depuis Yahoo Finance
- Calcul du rendement de chaque action entre deux dates (ex: du 14 juin au 30 octobre) pour chaque année
- Statistiques générées :
  - Moyenne
  - Médiane
  - Écart-type
  - Pourcentage d'années positives
- Exportation des résultats en fichier Excel

## Déploiement

Le déploiement peut être effectué sur [Streamlit Cloud](https://streamlit.io/cloud) en important ce dépôt GitHub.

### Fichiers requis :
- `sp500_streamlit_app.py` (script principal)
- `requirements.txt` (dépendances)
- `README.md` (présentation du projet)

## Utilisation

1. Sélectionnez le nombre d'années à analyser et l'année de fin.
2. Indiquez la date de début et la date de fin de la période saisonnière.
3. L'application calcule les rendements pour chaque entreprise et les affiche dans un tableau interactif.
4. Un bouton permet de télécharger un fichier Excel des résultats.

## Auteur

Développé avec ❤️ par [TonNom].

