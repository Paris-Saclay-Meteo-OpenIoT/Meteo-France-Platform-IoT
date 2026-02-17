#!/bin/bash

#Script de bash qui permet de lancer le scénario de test et de gérer les logs, utilisé dans le cas de test sur une machine local.

# On crée le dossier logs au cas où si on en a pas
mkdir -p logs

#On génère un nom de fichier avec la date et l'heure exacte
NOM_FICHIER="logs/rapport_$(date +%Y-%m-%d_%Hh%Mm%Ss).log"

echo "Démarrage du pipeline de test !"
echo "Les résultats seront sauvegardés dans : $NOM_FICHIER"

#Commande qui lance le pîpeline de test
python3 -u test_scenario.py | tee "$NOM_FICHIER"