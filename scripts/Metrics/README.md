# Visualisation

Ce dossier contient les scripts de visualisation des affectations d'UE, ainsi que les sorties graphiques (qui sont generes a partir de metrics_utils.py)

## Structure

visualisation/
├── gini.py              # Courbe de Lorenz et coefficient de Gini
├── split_heatmap.py     # Heatmaps de satisfaction par parcours
├── results.py           # Graphiques interactifs (Plotly)
└── out/                 # Graphiques générés

## Utilisation
Les visualisations sont generees en executant "metrics_utils.py" depuis le dossier "scripts/Metrics/":

python metrics_utils.py

Les fichiers d'entrée attendus sont dans "srcFiles/" :

- "FCFSaffectation.csv" - matrice d'affectation binaire (étudiants × UEs)
- "studentsRandom.csv" - préférences et rangs des étudiants
- "courses.csv" - liste des UEs avec leurs UEs obligatoires par parcours
- "parameters.json" - paramètres du problème (nombre d'UEs min/max par parcours)

## Sorties

Tous les graphiques sont produits dans "visualisation/out/".

### Heatmaps globales ("metrics_utils.py")
4 versions selon la stratégie de tri des étudiants (du plus satisfait au moins satisfait) :

mean_std.png -> Moyenne corrigée + écart-type
median.png -> Médiane corrigée
ranksum.png -> Somme des rangs corrigée
mean_IQR.png -> Moyenne corrigée + IQR

Les rangs sont normalisés par rapport au rang maximum global (rang moyen max sur l'ensemble des étudiants), de sorte que les couleurs sont comparables entre tous les étudiants.

### Heatmaps par parcours (`split_heatmap.py`)
Même logique que les heatmaps globales, mais les étudiants sont séparés par parcours (AI Track / CS Track), côte à côte. 3 stratégies de tri disponibles. Une version `_optional` est également générée, dans laquelle les UEs obligatoires du parcours AI sont retirées avant normalisation, afin de comparer les deux parcours sur un pied d'égalité.

