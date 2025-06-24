# Analyse saisonnière des rendements S&P 500

Cette application Streamlit télécharge les données historiques des composantes du S&P 500 et calcule les rendements sur une période saisonnière choisie.

## Fonctionnalités

- Choix de la période annuelle à analyser (ex: 14 juin au 30 octobre)
- Choix du nombre d'années d'analyse
- Calcul pour chaque ticker du rendement moyen, médian, écart-type et pourcentage d'années positives
- Téléchargement des résultats en format Excel (.xlsx)

## Utilisation

Déployable sur [Streamlit Cloud](https://streamlit.io/cloud) avec les fichiers :

- `sp500_streamlit_app.py`
- `requirements.txt`
