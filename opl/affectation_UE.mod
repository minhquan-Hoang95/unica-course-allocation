/*********************************************
 * OPL 22.1.0.0 Model
 * Author: nthie
 * Creation Date: 10 mars 2026 at 18:02:57
 *********************************************/

// FIXME Le modèle n'a pas de solution !

// TODO Utiliser des noms clairs.

// TODO Décider définitivement si la langue est l'anglais ou le français.
// Pour le code, je recommande anglais pour rester en ASCII.
// Pour la documentation, on peut rester en français pour faciliter la rédaction

///////////////////////
///    Entrées      ///
///////////////////////
/*Dimensions*/
int n = ...;   // Nombre d'étudiants
int m = ...;   // Nombre d'UE
int p = ...;   // Nombre de parcours

range Etudiants = 1..n;
range UEs       = 1..m;
range Parcours  = 1..p;

/*Cours*/
int c[UEs] = ...;				// Capacité de chaque UE j (en nombre de places disponibles hors obligatoires)
// TODO Simplifier et compresser l'information avec un ensemble de tuples d'incompatibilité {<i,j>}.
// En général, il n'y a incompatibilité qu'avec un seul autre cours !
int Ic[UEs][UEs] = ...;			// Matrice d'incompatibilité : Ic[j][j2] = 1 si les UE j et j2 sont incompatibles

/*Parcours*/
int mmin[Parcours] = ...;		// Nombre minimum d'UE optionnelles à suivre dans le parcours k
// TODO Simplifier et compresser l'information avec un ensemble {int}
int mand[UEs][Parcours] = ...;	// Matrice d'association des UE aux parcours (mand[2][3] = 1 <=> L'UE 2 est obligatoire dans le parcours 3).

/* étudiants */
int mmax[Etudiants] = ...;		// Nombre maximum d'UE souhaité par l'étudiant i
int parc[Etudiants] = ...;		// Parcours suivi par l'étudiant i

// TODO Attention les ranges sont des flottants, car on prend le rang moyen en cas d'égalité.
int r[Etudiants][UEs] = ...;	// Rang de l'UE j pour l'étudiant i (plus le rang est bas = plus l'UE est préférée)
								// Plusieurs UE peuvent partager le même rang ; les rangs sont consécutifs.

// TODO (plus tard) utiliser assert pour vérifier les entrées.

// NOTE Les données ne sont pas nommées : on utilise un indice et pas un code ou un nom d'étu/UE/Parc.


///////////////////////
///     Sortie      ///
///////////////////////
dvar boolean A[Etudiants][UEs];	// A[i][j] = 1 si l'étudiant i est affecté à  l'UE j, 0 sinon

// TODO Définir l'objectif de manière abstraite.
// int objType = ...;
// dexpr int objectif;

// TODO dexpr int RangMoyen =
// TODO dexpr int PireRang =

// NOTE Il faut distinguer l'affectation aux UEs requises de celle aux UEs supplémentaires.

///////////////////////
///    Fonction     ///
///////////////////////
// On minimise la somme des rangs des UE attribuées à chaque étudiant.
// Un rang faible signifie que l'UE est très désirée : on favorise
// l'attribution des UE les mieux classées par chaque étudiant.
minimize
  sum(i in Etudiants, j in UEs) r[i][j] * A[i][j];


///////////////////////
///   Contraintes   ///
///////////////////////
subject to {

  // (C1) La somme des affectations pour une UE ne dépasse pas sa capacité.
  forall(j in UEs)
    ctCapacite:
      sum(i in Etudiants) A[i][j] <= c[j];

  // (C2) Une affectation ne peut accorder que des UE compatibles entre elles.
  forall(i in Etudiants, j in UEs, j2 in UEs : j < j2)
    ctCompatibilite:
      Ic[j][j2] + A[i][j] + A[i][j2] <= 2;							// Si Ic[j][j2] = 1, un étudiant ne peut pas avoir les deux UE j et j2.

  // TODO Simplifier en ne posant la contraint A[i][j] == 1 que si  mand[j][parc[i]] == 1
  // (C3) Un étudiant inscrit dans un parcours k doit recevoir toutes les UE obligatoires de ce parcours.
  forall(i in Etudiants, j in UEs)
    ctObligatoires:
      A[i][j] >= sum(k in Parcours) ((parc[i] == k) * mand[j][k]);	// Si parc[i] == k et mand[j][k] == 1, alors A[i][j] doit valoir 1.


  // (C4) Un étudiant doit recevoir entre 8 et 10 UE au total.
  // TODO Extraire les données dans le fichier .dat : ce sont des attributs globaux ou du parcours.
  forall(i in Etudiants) {
    ctMinUE:
      sum(j in UEs) A[i][j] >= 8;
   // TODO Contrainte redondante avec ctDemandeMax
    ctMaxUE:
      sum(j in UEs) A[i][j] <= 10;
  }


  // (C5) Un étudiant reçoit au plus le nombre d'UE qu'il a demandé.
  forall(i in Etudiants)
    ctDemandeMax:
      sum(j in UEs) A[i][j] <= mmax[i];

 // TODO Avec le modèle actuel, l'étudiant ne suivra aucune UE optionnelle.
 // En effet, les UEs optionnelles seront nécessairement les moins bien classées.
 // Donc, elles feront augmenter la moyenne ce qui est sous-optimal.


 // TODO Cette contrainte est redondant avec ctMinUE : ce n'est pas la peine de compter le nombre d'UEs optionnelles si on connaît le nombre total et d'obligatoires.

 // (C6) Un étudiant doit suivre au moins mmin[k] UE optionnelles dans son parcours k.
 // Une UE est optionnelle pour l'étudiant i si elle n'est PAS obligatoire dans son parcours.
  forall(i in Etudiants)
    ctMinOptionnelles:
      sum(j in UEs : mand[j][parc[i]] == 0) A[i][j]
        >= mmin[parc[i]];

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


// TODO Ne pas calculer de statistiques ou métriques : cela serait fait par les scripts.

  writeln("");
  writeln("=== Taux de remplissage des UE ===");
  for(var j = 1; j <= m; j++) {
    var inscrits = 0;
    for(var i = 1; i <= n; i++) {
      if(A[i][j] == 1) inscrits++;
    }
    writeln("UE " + j + " : " + inscrits + "/" + c[j] + " places occupees");
  }

    // Sortie au format CSV pour les scripts.
    var f = new IloOplOutputFile("affectation.csv");
    f.write("studentID", ",");
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
          	var value = A[i][j]       
            f.write(value);
            if (j != m) {          
	            f.write(",");
            }
        }
        f.writeln();
    }
    f.close();
}
