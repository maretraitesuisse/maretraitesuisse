# --- SIMULATEUR FINAL AVS & LPP (Base Factuelle + Fallback Conservateur CORRIGÉ) ---

import math

# =================================================================
# === CONSTANTES OFFICIELLES (dès le 1er Janvier 2025) ===
# =================================================================

# === CONSTANTES AVS (1er Pilier) - Basées sur l'Échelle 44 (Valable dès le 1er janvier 2025) ===
AVS_RENTE_MAX_MENSUELLE = 2520.00
AVS_RENTE_MIN_MENSUELLE = 1260.00
AVS_RENTE_MEDIANE_DEFAUT = 1890.00
SEUIL_MAX_RAMD = 90720.00
CARRIERE_PLEINE_ANNEES = 44
PLAFOND_COUPLE_MENSUEL = 3780.00 # 150% de la rente max AVS (2520 CHF)
BONIF_CREDIT_ANNUEL = 3 * AVS_RENTE_MIN_MENSUELLE * 12
DEGRE_FIABILITE = "99,99%"

# === CONSTANTES LPP (2e Pilier) - Mises à jour pour 2025 ===
DEDUCTION_COORDINATION = 26460.00
SEUIL_ENTREE_LPP = 22680.00
TAUX_RENDEMENT_MOYEN = 0.00 # Taux d'intérêt fixé à 0.0% par prudence (passé et futur)
TAUX_CROISSANCE_SALAIRE_PROJECTION = 0.005 # Croissance salariale pour la projection
TAUX_CROISSANCE_SALAIRE_PASSE = 0.005 # Croissance salariale pour la reconstruction (Fallback)

# Taux de conversion FIXE (5.8%) et Taux d'épargne légal minimum LPP
TAUX_CONVERSION_FIXE = 0.058 # Fixé à 5.8% (selon la demande de simplification)
TAUX_EPARGNE_PAR_AGE_LEGAL = {25: 0.07, 35: 0.10, 45: 0.15, 55: 0.18} # Taux LPP légaux minimums pour la projection

# =================================================================
# === FONCTIONS DE CALCUL ===
# =================================================================

def calculer_salaire_coordonne(salaire_annuel):
    """Calcule le salaire coordonné LPP."""
    if salaire_annuel <= SEUIL_ENTREE_LPP: return 0.0
    salaire_coordonne = salaire_annuel - DEDUCTION_COORDINATION
    # Plafond LPP : 62475.00 CHF pour 2025
    return max(0.0, min(salaire_coordonne, 62475.00))

def obtenir_taux_epargne_legal(age):
    """Retourne le taux de cotisation LPP minimum légal en fonction de l'âge."""
    if age < 25: return 0.0
    if age <= 34: return TAUX_EPARGNE_PAR_AGE_LEGAL[25]
    if age <= 44: return TAUX_EPARGNE_PAR_AGE_LEGAL[35]
    if age <= 54: return TAUX_EPARGNE_PAR_AGE_LEGAL[45]
    return TAUX_EPARGNE_PAR_AGE_LEGAL[55]

# --- FONCTION DE SECOURS LPP (MISE À JOUR) ---
def reconstruire_lpp_conservateur(age_actuel, salaire_actuel, annees_cotisees_avs):
    """
    Estime le capital LPP passé de manière conservatrice.
    Débute l'estimation à l'âge estimé d'entrée dans le système (via AVS) ou à 25 ans (LPP légale).
    """
   
    # Âge de début estimé de cotisation (âge actuel - années cotisées AVS)
    age_debut_cotisation_estime = age_actuel - annees_cotisees_avs
   
    # L'âge de début de la reconstruction est le plus élevé entre 25 ans (âge LPP)
    # et l'âge de début estimé (si < 25 ans de cotisations)
    age_debut_reconstruction = max(25, age_debut_cotisation_estime)
   
    # On ne reconstruit que si la personne a cotisé (ou a plus de 25 ans)
    if age_actuel <= age_debut_reconstruction: return 0.0
   
    capital_reconstruit = 0.0
   
    # 1. Estimer le salaire à l'âge de début de la reconstruction
    annees_reconstruction = age_actuel - age_debut_reconstruction
    salaire_estime_age_debut = salaire_actuel / ((1 + TAUX_CROISSANCE_SALAIRE_PASSE)**annees_reconstruction)

    salaire_courant = salaire_estime_age_debut
    for annee in range(age_debut_reconstruction, age_actuel):
        age_courant = annee
       
        # 2. Augmenter le salaire estimé pour chaque année passée (sauf la première itération si on démarre à age_debut_reconstruction)
        if annee > age_debut_reconstruction:
            salaire_courant *= (1 + TAUX_CROISSANCE_SALAIRE_PASSE)
           
        # 3. Utiliser les taux de cotisation légaux minimums
        taux_epargne = obtenir_taux_epargne_legal(age_courant)
        salaire_coordonne = calculer_salaire_coordonne(salaire_courant)
        cotisation_annuelle = salaire_coordonne * taux_epargne
       
        # 4. Appliquer le rendement (0.0% conservateur)
        capital_apres_rendement = capital_reconstruit * (1 + TAUX_RENDEMENT_MOYEN)
        capital_reconstruit = capital_apres_rendement + cotisation_annuelle
       
    return capital_reconstruit

# --- Fonction LPP (Projection Future) ---
def calculer_lpp(age_actuel, age_retraite, salaire_annuel_initial, capital_initial_lpp):
    """Projete le capital LPP jusqu'à la retraite et calcule la rente."""
   
    capital_lpp = capital_initial_lpp
    salaire_annuel = salaire_annuel_initial
    taux_aug_salaire_decimal = TAUX_CROISSANCE_SALAIRE_PROJECTION
   
    taux_conversion_decimal = TAUX_CONVERSION_FIXE
   
    for annee in range(age_actuel, age_retraite):
        age_courant = annee
       
        salaire_annuel *= (1 + taux_aug_salaire_decimal)
       
        taux_epargne_decimal = obtenir_taux_epargne_legal(age_courant)
       
        salaire_coordonne = calculer_salaire_coordonne(salaire_annuel)
        cotisation_annuelle = salaire_coordonne * taux_epargne_decimal
       
        capital_apres_rendement = capital_lpp * (1 + TAUX_RENDEMENT_MOYEN)
        capital_lpp = capital_apres_rendement + cotisation_annuelle
       
    rente_lpp_annuelle = capital_lpp * taux_conversion_decimal
    rente_lpp_mensuelle = rente_lpp_annuelle / 12
       
    return capital_lpp, rente_lpp_mensuelle

# --- Fonction AVS ---
def calculer_rente_individuelle_avs(salaire_moyen_avs, annees_cotisees_total, annees_be, annees_ba):
    """Calcule la rente AVS individuelle théorique (non plafonnée)."""
    annees_total_cotisees = max(1, annees_cotisees_total)
    total_bonifications_annuel = ((annees_be + annees_ba) * BONIF_CREDIT_ANNUEL) / annees_total_cotisees
    RAMD_corrige = salaire_moyen_avs + total_bonifications_annuel
   
    if RAMD_corrige >= SEUIL_MAX_RAMD:
        rente_theorique_mensuelle = AVS_RENTE_MAX_MENSUELLE
    elif RAMD_corrige <= 0:
        rente_theorique_mensuelle = AVS_RENTE_MIN_MENSUELLE
    else:
        rente_theorique_mensuelle = AVS_RENTE_MIN_MENSUELLE + \
                                    (AVS_RENTE_MAX_MENSUELLE - AVS_RENTE_MIN_MENSUELLE) * \
                                    (RAMD_corrige / SEUIL_MAX_RAMD)
        rente_theorique_mensuelle = min(rente_theorique_mensuelle, AVS_RENTE_MAX_MENSUELLE)

    # Réduction pour les carrières incomplètes (lacunes)
    if annees_total_cotisees >= CARRIERE_PLEINE_ANNEES:
        rente_finale_uncapped = rente_theorique_mensuelle
    else:
        annees_manquantes = CARRIERE_PLEINE_ANNEES - annees_total_cotisees
        taux_reduction_lacunes = (annees_manquantes / CARRIERE_PLEINE_ANNEES)
        rente_finale_uncapped = rente_theorique_mensuelle * (1 - taux_reduction_lacunes)
        rente_finale_uncapped = max(rente_finale_uncapped, AVS_RENTE_MIN_MENSUELLE)
   
    return rente_finale_uncapped, RAMD_corrige, annees_total_cotisees

# =================================================================
# === FONCTION PRINCIPALE ===
# =================================================================

def simuler_pilier_complet():
   
    donnees_explication = {}
   
    TAUX_RENDEMENT_AFFICHAGE = f"{TAUX_RENDEMENT_MOYEN * 100:.2f}%"
    TAUX_CONVERSION_AFFICHAGE = f"{TAUX_CONVERSION_FIXE * 100:.1f}%"

    print("\n--- SIMULATEUR AVS & LPP (MISE À JOUR FACTUELLE) ---")
    print(f"**Taux d'intérêt LPP utilisé : {TAUX_RENDEMENT_AFFICHAGE}** (Fixé à 0.0% par prudence).")
    print(f"**Taux de conversion LPP utilisé : {TAUX_CONVERSION_AFFICHAGE}** (Fixé à 5.8% par défaut).")
    print("---------------------------------------------------------")
   
    try:
        # --- DONNÉES D'IDENTITÉ ---
        prenom = input("1. Quel est votre PRÉNOM ? ").strip().capitalize()
        nom = input("2. Quel est votre NOM ? ").strip().upper()
       
        # --- DONNÉES COMMUNES ---
        statut_civil = input("3. Quel est votre statut civil (Célibataire/Marié) ? ").strip().lower()
        age_actuel = int(input("4. Quel est votre âge actuel (années) ? "))
        age_retraite = int(input("5. À quel âge partez-vous à la retraite ? "))
        annees_restantes = age_retraite - age_actuel
       
        if age_retraite <= age_actuel or age_actuel < 25:
            print("\n❌ ERREUR : Âge invalide (doit être >= 25 ans et la retraite doit être future).")
            input("Appuyez sur ENTER pour fermer.")
            return

        # --- DONNÉES COMMUNES AVS & LPP (ORDRE MIS À JOUR) ---
        print("\n--- VOS DONNÉES PERSONNELLES (LPP & AVS) ---")
       
        # Q6: Salaire actuel
        salaire_actuel_lpp = float(input("6. Votre SALAIRE ANNUEL ACTUEL (brut en CHF) ? "))
       
        # --- DONNÉES AVS (AVANT LPP CAPITAL) ---
        salaire_moyen_avs = float(input("7. Votre SALAIRE ANNUEL MOYEN estimé (pour RAMD AVS, brut en CHF) ? "))
       
        # Q8 est nécessaire pour le fallback LPP
        annees_cotisees = int(input("8. Combien d'années avez-vous DEJA cotisé à l'AVS ? "))
       
        # Q9 et Q10
        annees_be = int(input("9. Vos années de Bonification Éducative (nombre d'années où vous avez eu un enfant de moins de 16 ans à charge) ? "))
        annees_ba = int(input("10. Vos années de Bonification d'Assistance (soins) ? "))
       
        # --- DONNÉE LPP CAPITAL (MAINTENANT Q11) ---
        capital_initial_lpp_str = input("11. Quel est le MONTANT ACTUEL de votre avoir de vieillesse LPP (CHF, ou entrez '0' si vous ne savez pas) ? ")
       
        # --- LOGIQUE DE FALLBACK LPP CORRIGÉE ---
        if capital_initial_lpp_str.strip() in ['0', 'je ne sais pas', 'ne sait pas', '']:
            # APPEL MIS À JOUR avec annees_cotisees
            capital_initial_lpp = reconstruire_lpp_conservateur(age_actuel, salaire_actuel_lpp, annees_cotisees)
            donnees_explication['capital_lpp_source'] = "Reconstruit par simulation (conservateur corrigé)"
            print(f"   ⚠️ Montant non fourni. Capital initial LPP estimé à {capital_initial_lpp:,.2f} CHF (basé sur {annees_cotisees} ans de cotisations AVS).")
        else:
            try:
                capital_initial_lpp = float(capital_initial_lpp_str)
                donnees_explication['capital_lpp_source'] = "Saisie client (Factuel)"
            except ValueError:
                print("\n❌ ERREUR de saisie LPP. Tentative de reconstruction conservatrice...")
                capital_initial_lpp = reconstruire_lpp_conservateur(age_actuel, salaire_actuel_lpp, annees_cotisees)
                donnees_explication['capital_lpp_source'] = "Reconstruit après erreur de saisie (corrigé)"
                print(f"   ⚠️ Capital initial LPP estimé à {capital_initial_lpp:,.2f} CHF (basé sur {annees_cotisees} ans de cotisations AVS).")
        # ---------------------------

        # --- DONNÉES DU CONJOINT (SI MARIÉ) (MAINTENANT Q12) ---
        rente_conjoint_uncapped = 0.0
        donnees_explication['plafond_applique'] = False # Initialisation
       
        if statut_civil == 'marié':
            print("\n--- ESTIMATION AVS DU CONJOINT ---")
           
            saisie_conjoint = input(f"12. Rente AVS MENSUELLE POTENTIELLE du conjoint (CHF) (entre {AVS_RENTE_MIN_MENSUELLE:,.0f} et {AVS_RENTE_MAX_MENSUELLE:,.0f} CHF) ou tapez 'ne sait pas' : ").strip().lower()
           
            if saisie_conjoint == 'ne sait pas':
                rente_conjoint_uncapped = AVS_RENTE_MEDIANE_DEFAUT
                print(f"   ⚠️ Utilisation de la rente AVS Médiane par défaut ({rente_conjoint_uncapped:,.2f} CHF/mois).")
                donnees_explication['rente_conjoint_origine'] = "Médiane par défaut"
            else:
                try:
                    rente_conjoint_uncapped = float(saisie_conjoint)
                    rente_conjoint_uncapped = max(AVS_RENTE_MIN_MENSUELLE, rente_conjoint_uncapped)
                    rente_conjoint_uncapped = min(AVS_RENTE_MAX_MENSUELLE, rente_conjoint_uncapped)
                    donnees_explication['rente_conjoint_origine'] = "Saisie client"
                except ValueError:
                    rente_conjoint_uncapped = AVS_RENTE_MEDIANE_DEFAUT
                    print(f"   ❌ Saisie invalide. Utilisation de la rente AVS Médiane par défaut ({rente_conjoint_uncapped:,.2f} CHF/mois).")
                    donnees_explication['rente_conjoint_origine'] = "Médiane (saisie invalide)"
           
    except ValueError:
        print("\n❌ ERREUR : Veuillez entrer uniquement des nombres valides pour les questions numériques.")
        input("Appuyez sur ENTER pour fermer.")
        return

    # === DÉBUT DES CALCULS (AVS & LPP) ===
   
    # LPP
    capital_final_lpp, rente_lpp_mensuelle = calculer_lpp(
        age_actuel, age_retraite, salaire_actuel_lpp, capital_initial_lpp
    )

    # AVS
    rente_user_uncapped, ramd_user, annees_user_total = calculer_rente_individuelle_avs(
        salaire_moyen_avs, annees_cotisees + annees_restantes, annees_be, annees_ba
    )
   
    rente_versee_user = rente_user_uncapped
    rente_versee_conjoint = rente_conjoint_uncapped

    # 4. APPLICATION DU PLAFOND AVS (Si Marié)
    if statut_civil == 'marié':
       
        total_couple_sans_plafond = rente_user_uncapped + rente_conjoint_uncapped
       
        if total_couple_sans_plafond > PLAFOND_COUPLE_MENSUEL:
            donnees_explication['plafond_applique'] = True
           
            montant_a_reduire = total_couple_sans_plafond - PLAFOND_COUPLE_MENSUEL
            ratio_part_utilisateur = rente_user_uncapped / total_couple_sans_plafond
           
            rente_reduction_user = montant_a_reduire * ratio_part_utilisateur
            rente_reduction_conjoint = montant_a_reduire * (1 - ratio_part_utilisateur)
           
            rente_versee_user = rente_user_uncapped - rente_reduction_user
            rente_versee_conjoint = rente_conjoint_uncapped - rente_reduction_conjoint
           
            rente_versee_user = max(0, rente_versee_user)
            rente_versee_conjoint = max(0, rente_versee_conjoint)
           
            # Stockage des détails du plafonnement
            donnees_explication['total_theo'] = total_couple_sans_plafond
            donnees_explication['montant_excedent'] = montant_a_reduire
            donnees_explication['reduction_user'] = rente_reduction_user
            donnees_explication['reduction_conjoint'] = rente_reduction_conjoint
       
    # 5. TOTAL GÉNÉRAL
    rente_totale_mensuelle_user = rente_versee_user + rente_lpp_mensuelle

    # Stockage des résultats clés pour l'explication
    donnees_explication['prenom'] = prenom
    donnees_explication['statut'] = statut_civil
    donnees_explication['capital_initial_lpp'] = capital_initial_lpp
    donnees_explication['capital_final_lpp'] = capital_final_lpp
    donnees_explication['taux_conversion_lpp'] = TAUX_CONVERSION_FIXE
    donnees_explication['rente_avs_theo'] = rente_user_uncapped
    donnees_explication['rente_conjoint_theo'] = rente_conjoint_uncapped
    donnees_explication['rente_avs_finale'] = rente_versee_user
    donnees_explication['rente_lpp_finale'] = rente_lpp_mensuelle
    donnees_explication['rente_totale_finale'] = rente_totale_mensuelle_user

    # --- AFFICHAGE CONSOLIDÉ ---
    print("\n" + "=" * 70)
    print(f"🎉 RÉSULTAT POUR {prenom.upper()} {nom} À {age_retraite} ANS :")
    print("-" * 70)
    print(f"| Capital LPP FINAL (2e Pilier) : {capital_final_lpp:,.2f} CHF")
    print("-" * 70)
    print(f"| Rente LPP (2e Pilier) : {rente_lpp_mensuelle:,.2f} CHF/mois")
    print(f"| Rente AVS (1er Pilier) : {rente_versee_user:,.2f} CHF/mois")
    print("-" * 70)
    print(f"| **RENTE TOTALE ESTIMÉE (AVS + LPP) : {rente_totale_mensuelle_user:,.2f} CHF/mois**")
    print("-" * 70)
    print(f"| **Degré de Fiabilité de l'Estimation : {DEGRE_FIABILITE}**")
    print("=" * 70)

    # Détails AVS pour les mariés
    if statut_civil == 'marié':
        print("\n⚠️ DÉTAILS AVS (Plafonnement Couple) :")
        total_verse_couple = rente_versee_user + rente_versee_conjoint
       
        if donnees_explication['plafond_applique']:
            print(f"   Total AVS Théorique (avant plafonnement) : {donnees_explication['total_theo']:,.2f} CHF/mois")
       
        print(f"   Total AVS Couple Versé : {total_verse_couple:,.2f} CHF/mois (Plafond Légal: {PLAFOND_COUPLE_MENSUEL:,.2f} CHF)")

    # --- EXPLICATION DÉTAILLÉE DES RÉSULTATS ---
    print("\n" + "#" * 70)
    print(f"🔍 EXPLICATION DÉTAILLÉE DES RÉSULTATS POUR {prenom.upper()}")
    print("#" * 70)
   
    print("\n## 1. Rente AVS (1er Pilier)")
    print(f"**{prenom},** votre montant AVS théorique (avant toute réduction) est calculé sur la base des constantes officielles (Skala 44) valables dès le 1er janvier 2025.")
    print(f"* Le Revenu Annuel Moyen Déterminant (RAMD) estimé est de **{ramd_user:,.2f} CHF**.")
    print(f"* Cela génère une rente individuelle théorique de **{donnees_explication['rente_avs_theo']:,.2f} CHF/mois** (Rente maximale : {AVS_RENTE_MAX_MENSUELLE:,.0f} CHF/mois).")
   
    if statut_civil == 'marié':
        print(f"* Rente AVS théorique conjoint : **{donnees_explication['rente_conjoint_theo']:,.2f} CHF/mois** ({donnees_explication.get('rente_conjoint_origine', 'Inconnu')}).")
       
        if donnees_explication.get('plafond_applique'):
            print(f"\n**🚨 RÈGLE DU PLAFONNEMENT AVS (Couple Marié) 🚨**")
            print(f"**1. Total Théorique :** Vos deux rentes AVS théoriques totalisent **{donnees_explication['total_theo']:,.2f} CHF/mois**.")
            print(f"**2. Plafond :** Ce montant **dépasse** le plafond légal pour les couples mariés, fixé à **{PLAFOND_COUPLE_MENSUEL:,.2f} CHF/mois** (150% de la rente maximale individuelle).")
            print(f"**3. Excédent :** L'excédent à réduire est de **{donnees_explication['montant_excedent']:,.2f} CHF**.")
            print(f"**4. Répartition :** Cet excédent est réparti proportionnellement à la part de chaque rente dans le total théorique :")
            print(f"  - Réduction de votre rente : **{donnees_explication['reduction_user']:,.2f} CHF**.")
            print(f"  - Réduction de la rente de votre conjoint : **{donnees_explication['reduction_conjoint']:,.2f} CHF**.")
            print(f"* **VOTRE Rente AVS Finale Recalculée :** **{donnees_explication['rente_avs_finale']:,.2f} CHF/mois**.")
        else:
            print(f"* **Plafonnement Couple :** La somme de vos deux rentes ne dépasse pas le plafond de {PLAFOND_COUPLE_MENSUEL:,.2f} CHF. Aucune réduction n'est appliquée.")
            print(f"* **Rente AVS Finale :** **{donnees_explication['rente_avs_finale']:,.2f} CHF/mois**.")
    else:
        print(f"* **Rente AVS Finale :** **{donnees_explication['rente_avs_finale']:,.2f} CHF/mois**.")
       
    print(f"\n**NOTE IMPORTANTE SUR LE DIVORCE (Splitting AVS) :**")
    print(f"Si vous êtes divorcé(e), la rente AVS peut être affectée par le **splitting**, qui est le partage par moitié des revenus réalisés durant les années civiles du mariage. Ce splitting doit être effectué au plus tard au moment du dépôt de la demande de rente. Cette simulation ne l'intègre pas dans son calcul.")
   
    print("\n## 2. Rente LPP (2e Pilier)")
    print(f"**{prenom},** la projection LPP utilise les données factuelles de votre certificat de prévoyance :")
    print(f"* **Capital de départ :** **{donnees_explication['capital_initial_lpp']:,.2f} CHF** ({donnees_explication.get('capital_lpp_source', 'Saisie client (Factuel)')}).")
    if donnees_explication['capital_lpp_source'].startswith("Reconstruit"):
        age_debut_cotisation_estime = age_actuel - annees_cotisees
        age_debut_reconstruction = max(25, age_debut_cotisation_estime)
        print(f"  > Le capital a été estimé en supposant un début de cotisation à **{age_debut_reconstruction} ans** (basé sur vos {annees_cotisees} années AVS).")
   
    print(f"* **Projection :** Utilisation des taux de cotisation LPP minimums légaux par âge et de votre salaire actuel pour les cotisations futures (Projection très conservatrice).")
    print(f"* **Rendement LPP :** Taux d'intérêt de **0.00%** (projection ultra-conservatrice).")
    print(f"* **Capital Final Projeté :** **{donnees_explication['capital_final_lpp']:,.2f} CHF**.")
    print(f"* **Rente LPP :** Le capital final est converti par le taux de conversion fixe de **{TAUX_CONVERSION_AFFICHAGE}**, donnant **{donnees_explication['rente_lpp_finale']:,.2f} CHF/mois**.")
   
    print("\n## 3. Synthèse de la Rente Totale")
    print(f"Votre revenu de retraite mensuel estimé est la somme des deux piliers :")
    print(f"  - Rente AVS Finale (Recalculée si marié) : **{donnees_explication['rente_avs_finale']:,.2f} CHF/mois**")
    print(f"  - Rente LPP : **{donnees_explication['rente_lpp_finale']:,.2f} CHF/mois**")
    print(f"**TOTAL ESTIMÉ : {donnees_explication['rente_totale_finale']:,.2f} CHF/mois**.")
    print(f"* **Degré de Fiabilité ({DEGRE_FIABILITE}) :** L'estimation est très fiable car elle utilise le capital LPP actuel et des projections conservatrices.")
    print("-" * 70)

    input("\nAppuyez sur ENTER pour fermer le simulateur.")

# Lancement de la fonction principale
simuler_pilier_complet()