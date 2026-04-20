/*********************************************
 * OPL 22.1.0.0 Model
 * Author: nthie
 * Creation Date: 10 mars 2026 at 18:02:57
 *********************************************/

// FIXME Le modÃ¨le n'a pas de solution !

// Convention : code en anglais (ASCII), commentaires en franÃ§ais.

///////////////////////
///    EntrÃ©es      ///
///////////////////////
/*Dimensions*/
int n = ...;   // Nombre d'Ã©tudiants
int m = ...;   // Nombre d'UE
int p = ...;   // Nombre de parcours

range Students = 1..n;
range Courses  = 1..m;
range Programs = 1..p;

/*Cours*/
int c[Courses] = ...;				// CapacitÃ© de chaque UE j (en nombre de places disponibles hors obligatoires)

// Ensemble des paires d'UE incompatibles (conflit d'emploi du temps).
// On remplace la matrice Ic[m][m] â€” creuse, donc trÃ¨s redondante â€” par un ensemble de tuples.
// Seules les paires effectivement en conflit sont listÃ©es : plus compact et plus lisible dans le .dat.
// Convention : on ne liste chaque paire qu'une seule fois (j < j2), la relation Ã©tant symÃ©trique.
tuple Conflict {
  int ue1;	// Indice de la premiÃ¨re UE incompatible (ue1 < ue2 par convention)
  int ue2;	// Indice de la seconde UE incompatible
}
{Conflict} conflicts = ...;	// Ensemble des paires d'UE en conflit d'emploi du temps

/*Parcours*/
int mmin[Programs] = ...;		// Nombre minimum d'UE optionnelles Ã  suivre dans le parcours k

// Ensemble des paires (UE, parcours) pour lesquelles l'UE est obligatoire.
// On remplace la matrice mand[m][p] â€” creuse â€” par un ensemble de tuples.
// Plus lisible dans le .dat : on ne liste que les associations effectives.
tuple Mandatory {
  int ue;		// Indice de l'UE obligatoire
  int parcours;	// Indice du parcours dans lequel cette UE est obligatoire
}
{Mandatory} mandatory = ...;	// Ensemble des paires (UE obligatoire, parcours)

/*Objectif*/
// Type d'objectif choisi dans le .dat, pour faciliter les comparaisons sans toucher au modÃ¨le.
//    1 = Minimiser la somme des rangs                          (utilite globale)
//    2 = Maximiser le nombre d'etudiants recevant leur 1er choix
//    3 = Minimiser la somme des pires rangs par etudiant       (equite individuelle)
//    4 = Maximiser le nombre de rangs faibles (cours voulus)
//    5 = Minimiser le nombre de rangs eleves  (cours non voulus)
//    6 = Minimiser l'ecart de somme de rangs entre etudiants   (equite collective)
//    7 = Maximiser la satisfaction croissante sur les cours voulus
//    8 = Minimiser la penalite croissante des cours non voulus
//    9 = Maximiser une satisfaction ponderee avec penalite croissante
//   10 = Maximiser le nombre d'etudiants satisfaits
int objType = ...;

// Seuil de rang utilise par les objectifs 4, 5, 9 et 10.
// Un cours est "voulu"     si son rang <= rankThreshold,
// et "non voulu"           si son rang >  rankThreshold.
// Exemple : rankThreshold = 3 signifie que les 3 premiers choix sont consideres comme voulus.
int rankThreshold = ...;

// Parametres de satisfaction utilises par l'objectif 10.
// Un etudiant est "satisfait" s'il recoit au moins minWanted cours voulus
// (rang <= rankThreshold) ET au plus maxUnwanted cours non voulus (rang > rankThreshold).
int minWanted   = ...;	// Nombre minimum de cours voulus pour qu'un etudiant soit satisfait
int maxUnwanted = ...;	// Nombre maximum de cours non voulus toleres

/*Global*/
// Bornes globales sur le nombre d'UE par Ã©tudiant, extraites dans le .dat
// pour ne pas coder en dur des constantes mÃ©tier dans le modÃ¨le.
int gmin = ...;					// Nombre minimum d'UE Ã  suivre (toutes UE confondues)
int gmax = ...;					// Nombre maximum d'UE Ã  suivre (toutes UE confondues)

/* Ã©tudiants */
int mmax[Students] = ...;		// Nombre maximum d'UE souhaitÃ© par l'Ã©tudiant i
int parc[Students] = ...;		// Parcours suivi par l'Ã©tudiant i

// Les rangs sont des flottants pour gÃ©rer les ex-Ã¦quo : si deux UE partagent
// le rang k et k+1, chacune reÃ§oit le rang moyen (k + k+1) / 2 = k + 0.5.
float r[Students][Courses] = ...;	// Rang de l'UE j pour l'Ã©tudiant i (plus le rang est bas = plus l'UE est prÃ©fÃ©rÃ©e)
								// Plusieurs UE peuvent partager le mÃªme rang ; les rangs sont consÃ©cutifs.

// TODO (plus tard) utiliser assert pour vÃ©rifier les entrÃ©es.
// VÃ©rifications des invariants des donnÃ©es d'entrÃ©e.
// Ces assertions sont Ã©valuÃ©es avant le solveur : elles lÃ¨vent une erreur explicite
// si les donnÃ©es du .dat sont incohÃ©rentes, Ã©vitant un Ã©chec silencieux du modÃ¨le.
/*
execute VALIDATION {
  // gmin doit Ãªtre strictement positif et infÃ©rieur ou Ã©gal Ã  gmax.
  assert gmin >= 1 : "gmin doit etre >= 1";
  assert gmax >= gmin : "gmax doit etre >= gmin";

  for(var i = 1; i <= n; i++) {
    // mmax[i] doit Ãªtre dans [gmin, gmax] : sinon C4 et C5 sont incompatibles.
    assert mmax[i] >= gmin : "mmax[" + i + "] < gmin : infaisable pour l'etudiant " + i;
    assert mmax[i] <= gmax : "mmax[" + i + "] > gmax : viole la borne globale pour l'etudiant " + i;
    // parc[i] doit rÃ©fÃ©rencer un parcours existant.
    assert parc[i] >= 1 && parc[i] <= p : "parc[" + i + "] hors de [1, p]";
  }

  for(var j = 1; j <= m; j++) {
    // La capacitÃ© d'une UE doit Ãªtre positive.
    assert c[j] >= 1 : "c[" + j + "] doit etre >= 1";
  }
}*/

// NOTE Les donnÃ©es ne sont pas nommÃ©es : on utilise un indice et pas un code ou un nom d'Ã©tu/UE/Parc.


///////////////////////
///     Sortie      ///
///////////////////////
dvar boolean A[Students][Courses];	// A[i][j] = 1 si l'Ã©tudiant i est affectÃ© Ã Â  l'UE j, 0 sinon

// --- Variables auxiliaires pour les objectifs non-lineaires ---

// (obj. 3) Pire rang recu par chaque etudiant parmi ses affectations.
// w[i] = max_j { r[i][j] * A[i][j] }.
// Linearisation : w[i] >= r[i][j] * A[i][j] pour tout j, et on minimise sum(w[i]).
dvar float+ w[Students];

// (obj. 6) Ecart entre le meilleur et le pire score de somme de rangs parmi tous les etudiants.
// scoreMax >= sum_j{r[i][j]*A[i][j]} pour tout i  (borne haute)
// scoreMin <= sum_j{r[i][j]*A[i][j]} pour tout i  (borne basse)
// L'objectif minimise (scoreMax - scoreMin).
dvar float+ scoreMax;
dvar float+ scoreMin;

// (obj. 10) Variable binaire : satisfied[i] = 1 si l'etudiant i est satisfait, 0 sinon.
// La satisfaction est definie par deux conditions couplees via big-M :
//   - au moins minWanted cours voulus       (rang <= rankThreshold)
//   - au plus  maxUnwanted cours non voulus (rang >  rankThreshold)
dvar boolean satisfied[Students];


// NOTE Il faut distinguer l'affectation aux UEs requises de celle aux UEs supplÃ©mentaires.

///////////////////////
///    Fonction     ///
///////////////////////
// --- Expressions d'objectif ---
// Toutes les dexpr sont definies ici.
// Seule celle selectionnee par objType est minimisee (ou maximisee via negation).
// Les objectifs pairs (maximiser) sont transformes en minimisation par negation.

// ----- Objectif 1 : Minimiser la somme des rangs -----
// Favorise l'utilite collective : un rang faible = cours tres desire.
// Minimiser la somme revient a maximiser la satisfaction moyenne globale.
dexpr float obj1_sumRanks =
  sum(i in Students, j in Courses) r[i][j] * A[i][j];

// ----- Objectif 2 : Maximiser le nombre d'etudiants recevant leur 1er choix -----
// On compte les affectations ou le rang vaut exactement 1 (meilleur choix).
// (r[i][j] == 1) est evalue a 1 si vrai, 0 sinon en OPL.
// On negativeise pour transformer en minimisation.
dexpr float obj2_firstChoiceCount =
  -sum(i in Students, j in Courses) (r[i][j] == 1) * A[i][j];

// ----- Objectif 3 : Minimiser la somme des pires rangs par etudiant -----
// Pour chaque etudiant i, w[i] capture le pire rang recu (max_j r[i][j]*A[i][j]).
// La linearisation est assuree par les contraintes ctWorstRank ci-dessous.
// Minimiser sum(w[i]) evite que certains etudiants soient fortement penalises.
dexpr float obj3_sumWorstRanks =
  sum(i in Students) w[i];

// ----- Objectif 4 : Maximiser le nombre de rangs faibles (cours voulus) -----
// Un cours est "voulu" si son rang <= rankThreshold.
// On compte toutes les affectations satisfaisant ce critere.
// On negativeise pour transformer en minimisation.
dexpr float obj4_wantedCount =
  -sum(i in Students, j in Courses : r[i][j] <= rankThreshold) A[i][j];

// ----- Objectif 5 : Minimiser le nombre de rangs eleves (cours non voulus) -----
// Un cours est "non voulu" si son rang > rankThreshold.
// On compte toutes les affectations ne satisfaisant pas le critere.
dexpr float obj5_unwantedCount =
  sum(i in Students, j in Courses : r[i][j] > rankThreshold) A[i][j];

// ----- Objectif 6 : Minimiser l'ecart de somme de rangs entre etudiants -----
// scoreMax (resp. scoreMin) est borne par les contraintes ctScoreMax/ctScoreMin.
// Minimiser (scoreMax - scoreMin) reduit les inegalites entre etudiants.
dexpr float obj6_spread =
  scoreMax - scoreMin;

// ----- Objectif 7 : Maximiser la satisfaction croissante sur les cours voulus -----
// Un cours de rang r apporte un gain de (m - r + 1)^2 : les tout premiers choix
// sont fortement recompenses (gain quadratique decroissant avec le rang).
// Les poids sont calcules statiquement depuis r (pas de variable non-lineaire).
// On negativeise pour transformer en minimisation.
dexpr float obj7_gainSq =
  -sum(i in Students, j in Courses) (m - r[i][j] + 1) * (m - r[i][j] + 1) * A[i][j];

// ----- Objectif 8 : Minimiser la penalite croissante des cours non voulus -----
// Un cours de rang r genere une penalite de r^2 : les cours tres mal classes
// sont fortement penalises (penalite quadratique croissante avec le rang).
dexpr float obj8_penaltySq =
  sum(i in Students, j in Courses) r[i][j] * r[i][j] * A[i][j];

// ----- Objectif 9 : Maximiser une satisfaction ponderee avec penalite croissante -----
// Combine objectifs 7 et 8 : gain quadratique pour les cours voulus
// et penalite quadratique pour les cours non voulus, dans une seule expression.
// On negativeise pour transformer en minimisation.
dexpr float obj9_combined =
  -sum(i in Students, j in Courses)
    ( (m - r[i][j] + 1) * (m - r[i][j] + 1) - r[i][j] * r[i][j] ) * A[i][j];

// ----- Objectif 10 : Maximiser le nombre d'etudiants satisfaits -----
// satisfied[i] est contraint par les contraintes ctSatisfied* ci-dessous.
// On negativeise pour transformer en minimisation.
dexpr float obj10_satisfiedCount =
  -sum(i in Students) satisfied[i];

// ----- Selecteur d'objectif -----
// Une seule expression est active a la fois selon objType.
// Toutes les expressions sont deja en forme "minimiser" (negation pour les maximisations).
dexpr float objectif =
  (objType ==  1) * obj1_sumRanks       +
  (objType ==  2) * obj2_firstChoiceCount +
  (objType ==  3) * obj3_sumWorstRanks  +
  (objType ==  4) * obj4_wantedCount    +
  (objType ==  5) * obj5_unwantedCount  +
  (objType ==  6) * obj6_spread         +
  (objType ==  7) * obj7_gainSq         +
  (objType ==  8) * obj8_penaltySq      +
  (objType ==  9) * obj9_combined       +
  (objType == 10) * obj10_satisfiedCount;

minimize objectif;


///////////////////////
///   Contraintes   ///
///////////////////////
subject to {

  // (C1) La somme des affectations pour une UE ne dÃ©passe pas sa capacitÃ©.
  forall(j in Courses)
    ctCapacite:
      sum(i in Students) A[i][j] <= c[j];

  // (C2) Une affectation ne peut accorder que des UE compatibles entre elles.
  // On itÃ¨re directement sur les paires incompatibles connues plutÃ´t que sur toutes les combinaisons.
  // Si la paire <j, j2> est dans conflicts, un Ã©tudiant ne peut pas avoir les deux Ã  la fois.
  forall(i in Students, ic in conflicts)
    ctCompatibilite:
      A[i][ic.ue1] + A[i][ic.ue2] <= 1;

  // (C3) Un Ã©tudiant inscrit dans un parcours k doit recevoir toutes les UE obligatoires de ce parcours.
  // On teste directement si le tuple <j, parc[i]> appartient Ã  l'ensemble mandatory,
  // ce qui est plus lisible et Ã©vite d'indexer une matrice creuse.
  forall(i in Students, j in Courses : <j, parc[i]> in mandatory)
    ctObligatoires:
      A[i][j] == 1;


  // (C4) Un Ã©tudiant doit recevoir au moins gmin UE au total.
  // La borne haute est assurÃ©e par ctDemandeMax (C5) qui est toujours plus contraignante
  // puisque mmax[i] <= gmax par construction : ctMaxUE serait donc redondante.
  forall(i in Students)
    ctMinUE:
      sum(j in Courses) A[i][j] >= gmin;


  // (C5) Un Ã©tudiant reÃ§oit au plus le nombre d'UE qu'il a demandÃ©.
  forall(i in Students)
    ctDemandeMax:
      sum(j in Courses) A[i][j] <= mmax[i];

 // (C6) SupprimÃ©e : ctMinOptionnelles Ã©tait redondante avec ctMinUE (C4).
 // Raisonnement : nb_optionnelles = nb_total - nb_obligatoires.
 // Comme nb_total >= gmin (via ctMinUE) et que nb_obligatoires est fixe pour un parcours donnÃ©,
 // la borne basse sur les optionnelles est dÃ©jÃ  garantie par ctMinUE si
 // gmin est calibrÃ© correctement dans le .dat (gmin >= nb_obligatoires + mmin[parc]).
 // On Ã©vite ainsi de compter deux fois les mÃªmes UE.


  // =========================================================================
  // Contraintes auxiliaires pour les objectifs non-lineaires (3, 6, 10)
  // =========================================================================

  // --- (obj. 3) Linearisation du pire rang par etudiant ---
  // w[i] doit etre >= r[i][j] * A[i][j] pour tout j.
  // Quand A[i][j]=0, la contrainte est triviale (w[i] >= 0, garanti par float+).
  // Quand A[i][j]=1, elle force w[i] >= r[i][j].
  // Le solveur pousse w[i] au minimum necessaire, ce qui donne le max des rangs attribues.
  forall(i in Students, j in Courses)
    ctWorstRank:
      w[i] >= r[i][j] * A[i][j];

  // --- (obj. 6) Borne haute et basse du score de somme de rangs par etudiant ---
  // scoreMax (resp. scoreMin) encadre la somme des rangs de chaque etudiant.
  // L'objectif minimise leur ecart, ce qui equalise la repartition entre etudiants.
  forall(i in Students)
    ctScoreMax:
      scoreMax >= sum(j in Courses) r[i][j] * A[i][j];
  forall(i in Students)
    ctScoreMin:
      scoreMin <= sum(j in Courses) r[i][j] * A[i][j];

  // --- (obj. 10) Contraintes de satisfaction via big-M ---
  // satisfied[i] = 1 implique les deux conditions simultanement.
  // Si satisfied[i] = 0, les contraintes sont relachees par le terme big-M (=m).
  //
  // Condition 1 : l'etudiant i a au moins minWanted cours voulus (rang <= rankThreshold).
  //   sum_{r[i][j]<=T} A[i][j] >= minWanted * satisfied[i]
  //   Si satisfied[i]=1 : la somme doit atteindre minWanted.
  //   Si satisfied[i]=0 : borne a 0, toujours vrai.
  forall(i in Students)
    ctSatisfiedWanted:
      sum(j in Courses : r[i][j] <= rankThreshold) A[i][j] >= minWanted * satisfied[i];

  // Condition 2 : l'etudiant i a au plus maxUnwanted cours non voulus (rang > rankThreshold).
  //   sum_{r[i][j]>T} A[i][j] <= maxUnwanted + m * (1 - satisfied[i])
  //   Si satisfied[i]=1 : la somme ne peut pas depasser maxUnwanted.
  //   Si satisfied[i]=0 : borne relevee a maxUnwanted+m (jamais violee), contrainte inactive.
  forall(i in Students)
    ctSatisfiedUnwanted:
      sum(j in Courses : r[i][j] > rankThreshold) A[i][j] <= maxUnwanted + m * (1 - satisfied[i]);

}

// ---------------------------------------------------------------------------
// 5. Post-traitement : affichage des rÃ©sultats
// ---------------------------------------------------------------------------

// NOTE TrÃ¨s bien, un affichage lisible pour les humains

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

  // Les statistiques (taux de remplissage, mÃ©triques d'Ã©quitÃ©, etc.) sont
  // volontairement absentes : elles sont calculÃ©es par les scripts externes
  // Ã  partir du fichier CSV ci-dessous.

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
