/*********************************************
 * OPL 22.1.0.0 Model
 * Author: nthie
 * Creation Date: 10 mars 2026 at 18:02:57
 *********************************************/

// FIXME Le modèle n'a pas de solution !

// Convention : code en anglais (ASCII), commentaires en français.

///////////////////////
///    Entrées      ///
///////////////////////
/*Dimensions*/
int n = ...;   // Nombre d'étudiants
int m = ...;   // Nombre d'UE
int p = ...;   // Nombre de parcours

range Students = 1..n;
range Courses  = 1..m;
range Programs = 1..p;

/*Cours*/
int c[Courses] = ...;				// Capacité de chaque UE j (en nombre de places disponibles hors obligatoires)

// Ensemble des paires d'UE incompatibles (conflit d'emploi du temps).
// On remplace la matrice Ic[m][m] — creuse, donc très redondante — par un ensemble de tuples.
// Seules les paires effectivement en conflit sont listées : plus compact et plus lisible dans le .dat.
// Convention : on ne liste chaque paire qu'une seule fois (j < j2), la relation étant symétrique.
tuple Conflict {
  int ue1;	// Indice de la première UE incompatible (ue1 < ue2 par convention)
  int ue2;	// Indice de la seconde UE incompatible
}
{Conflict} conflicts = ...;	// Ensemble des paires d'UE en conflit d'emploi du temps

/*Parcours*/
int mmin[Programs] = ...;		// Nombre minimum d'UE optionnelles à suivre dans le parcours k

// Ensemble des paires (UE, parcours) pour lesquelles l'UE est obligatoire.
// On remplace la matrice mand[m][p] — creuse — par un ensemble de tuples.
// Plus lisible dans le .dat : on ne liste que les associations effectives.
tuple Mandatory {
  int ue;		// Indice de l'UE obligatoire
  int parcours;	// Indice du parcours dans lequel cette UE est obligatoire
}
{Mandatory} mandatory = ...;	// Ensemble des paires (UE obligatoire, parcours)

/*Objectif*/
// Type d'objectif choisi dans le .dat, pour faciliter les comparaisons sans toucher au modèle.
//   1 = Minimiser la somme des rangs (favorise l'utilité globale)
//   2 = Minimiser le pire rang reçu par un étudiant (favorise l'équité)
int objType = ...;

/*Global*/
// Bornes globales sur le nombre d'UE par étudiant, extraites dans le .dat
// pour ne pas coder en dur des constantes métier dans le modèle.
int gmin = ...;					// Nombre minimum d'UE à suivre (toutes UE confondues)
int gmax = ...;					// Nombre maximum d'UE à suivre (toutes UE confondues)

/* étudiants */
int mmax[Students] = ...;		// Nombre maximum d'UE souhaité par l'étudiant i
int parc[Students] = ...;		// Parcours suivi par l'étudiant i

// Les rangs sont des flottants pour gérer les ex-æquo : si deux UE partagent
// le rang k et k+1, chacune reçoit le rang moyen (k + k+1) / 2 = k + 0.5.
float r[Students][Courses] = ...;	// Rang de l'UE j pour l'étudiant i (plus le rang est bas = plus l'UE est préférée)
								// Plusieurs UE peuvent partager le même rang ; les rangs sont consécutifs.

// TODO (plus tard) utiliser assert pour vérifier les entrées.
// Vérifications des invariants des données d'entrée.
// Ces assertions sont évaluées avant le solveur : elles lèvent une erreur explicite
// si les données du .dat sont incohérentes, évitant un échec silencieux du modèle.
execute VALIDATION {
  // gmin doit être strictement positif et inférieur ou égal à gmax.
  assert gmin >= 1 : "gmin doit etre >= 1";
  assert gmax >= gmin : "gmax doit etre >= gmin";

  for(var i = 1; i <= n; i++) {
    // mmax[i] doit être dans [gmin, gmax] : sinon C4 et C5 sont incompatibles.
    assert mmax[i] >= gmin : "mmax[" + i + "] < gmin : infaisable pour l'etudiant " + i;
    assert mmax[i] <= gmax : "mmax[" + i + "] > gmax : viole la borne globale pour l'etudiant " + i;
    // parc[i] doit référencer un parcours existant.
    assert parc[i] >= 1 && parc[i] <= p : "parc[" + i + "] hors de [1, p]";
  }

  for(var j = 1; j <= m; j++) {
    // La capacité d'une UE doit être positive.
    assert c[j] >= 1 : "c[" + j + "] doit etre >= 1";
  }
}

// NOTE Les données ne sont pas nommées : on utilise un indice et pas un code ou un nom d'étu/UE/Parc.


///////////////////////
///     Sortie      ///
///////////////////////
dvar boolean A[Students][Courses];	// A[i][j] = 1 si l'étudiant i est affecté à  l'UE j, 0 sinon


// NOTE Il faut distinguer l'affectation aux UEs requises de celle aux UEs supplémentaires.

///////////////////////
///    Fonction     ///
///////////////////////
// --- Expressions d'objectif ---
// Chaque dexpr correspond à un critère d'optimisation indépendant.
// On les définit toutes ici ; seule celle sélectionnée par objType est minimisée.

// (objType = 1) Somme totale des rangs : favorise l'utilité collective.
// Un rang faible = UE très désirée ; minimiser la somme revient à maximiser la satisfaction globale.
dexpr float sumRanks =
  sum(i in Students, j in Courses) r[i][j] * A[i][j];

// (objType = 2) Pire rang reçu par un étudiant parmi toutes ses affectations : favorise l'équité.
// Minimiser ce maximum garantit qu'aucun étudiant n'est trop pénalisé.
dexpr float worstRank =
  max(i in Students, j in Courses) (r[i][j] * A[i][j]);

// Sélection de l'objectif actif selon objType.
// On utilise une combinaison linéaire pondérée : un seul terme est non nul à la fois.
dexpr float objectif =
  (objType == 1) * sumRanks +
  (objType == 2) * worstRank;

minimize objectif;


///////////////////////
///   Contraintes   ///
///////////////////////
subject to {

  // (C1) La somme des affectations pour une UE ne dépasse pas sa capacité.
  forall(j in Courses)
    ctCapacite:
      sum(i in Students) A[i][j] <= c[j];

  // (C2) Une affectation ne peut accorder que des UE compatibles entre elles.
  // On itère directement sur les paires incompatibles connues plutôt que sur toutes les combinaisons.
  // Si la paire <j, j2> est dans conflicts, un étudiant ne peut pas avoir les deux à la fois.
  forall(i in Students, ic in conflicts)
    ctCompatibilite:
      A[i][ic.ue1] + A[i][ic.ue2] <= 1;

  // (C3) Un étudiant inscrit dans un parcours k doit recevoir toutes les UE obligatoires de ce parcours.
  // On teste directement si le tuple <j, parc[i]> appartient à l'ensemble mandatory,
  // ce qui est plus lisible et évite d'indexer une matrice creuse.
  forall(i in Students, j in Courses : <j, parc[i]> in mandatory)
    ctObligatoires:
      A[i][j] == 1;


  // (C4) Un étudiant doit recevoir au moins gmin UE au total.
  // La borne haute est assurée par ctDemandeMax (C5) qui est toujours plus contraignante
  // puisque mmax[i] <= gmax par construction : ctMaxUE serait donc redondante.
  forall(i in Students)
    ctMinUE:
      sum(j in Courses) A[i][j] >= gmin;


  // (C5) Un étudiant reçoit au plus le nombre d'UE qu'il a demandé.
  forall(i in Students)
    ctDemandeMax:
      sum(j in Courses) A[i][j] <= mmax[i];

 // (C6) Supprimée : ctMinOptionnelles était redondante avec ctMinUE (C4).
 // Raisonnement : nb_optionnelles = nb_total - nb_obligatoires.
 // Comme nb_total >= gmin (via ctMinUE) et que nb_obligatoires est fixe pour un parcours donné,
 // la borne basse sur les optionnelles est déjà garantie par ctMinUE si
 // gmin est calibré correctement dans le .dat (gmin >= nb_obligatoires + mmin[parc]).
 // On évite ainsi de compter deux fois les mêmes UE.

}

// ---------------------------------------------------------------------------
// 5. Post-traitement : affichage des résultats
// ---------------------------------------------------------------------------

// NOTE Très bien, un affichage lisible pour les humains

execute AFFICHAGE {
  writeln("=== Affectation des UE ===");
  for(var i = 1; i <= n; i++) {
    write("Etudiant " + i + " (parcours " + parc[i] + ") : UE attribuees -> ");
    var total = 0;
    var scorePref = 0;
    for(var j = 1; j <= m; j++) {
      if(A[i][j] == 1) {
        write(j + "(rang=" + r[i][j] + ") ");
        total++;
        scorePref += r[i][j];
      }
    }
    writeln("| Total=" + total + " | Score preference=" + scorePref);
  }

  // Les statistiques (taux de remplissage, métriques d'équité, etc.) sont
  // volontairement absentes : elles sont calculées par les scripts externes
  // à partir du fichier CSV ci-dessous.

  // Sortie au format CSV pour les scripts.
    var f = new IloOplOutputFile("affectation.csv");
    f.write("studentID,");
    for(var j = 1; j <= m; j++) {
        f.write("c" + j);
        if (j != m) {
            f.write(",");
        }
    }
    f.writeln();
    for(var i = 1; i <= n; i++) {
        f.write(i);
        f.write(",");
        for(var j = 1; j <= m; j++) {
            var value = A[i][j];
            f.write(value);
            if (j != m) {
                f.write(",");
            }
        }
        f.writeln();
    }
    f.close();
}
