"""
Calculateur de Retraite Suisse (AVS/LPP) 2025
Reproduction exacte des calculs de l'application React
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json


# ============================================================================
# CONSTANTES AVS/LPP 2025
# ============================================================================

@dataclass
class ConfigAVS:
    """Configuration AVS 2025"""
    RENTE_MAX: float = 2520.0
    RENTE_MIN: float = 1260.0
    RENTE_MEDIANE: float = 1890.0
    RAMD_MAX: float = 90720.0
    CARRIERE_PLEINE: int = 44
    PLAFOND_COUPLE: float = 3780.0
    BONIF_CREDIT_ANNUEL: float = 45360.0
    REDUCTION_PAR_ANNEE: float = 0.0227


@dataclass
class ConfigLPP:
    """Configuration LPP 2025"""
    DEDUCTION_COORD: float = 26460.0
    SALAIRE_MAX: float = 88200.0
    SALAIRE_MIN: float = 22680.0
    TAUX_CONVERSION: float = 0.068
    TAUX_INTERET: float = 0.01
    TAUX_EPARGNE: Dict[int, float] = field(default_factory=lambda: {
        25: 0.07,
        35: 0.10,
        45: 0.15,
        55: 0.18
    })


# Instances globales
AVS = ConfigAVS()
LPP = ConfigLPP()


# ============================================================================
# CLASSES DE RÉSULTATS
# ============================================================================

@dataclass
class ResultatAVS:
    """Résultat du calcul AVS"""
    rente: float
    rente_complete: float
    ramd: float
    annees_manquantes: int
    taux_reduction: float
    bonifications: float


@dataclass
class ProjectionAnnuelle:
    """Projection LPP pour une année"""
    age: int
    salaire: float
    salaire_coordonne: float
    taux_epargne: float
    cotisation: float
    interets: float
    capital_debut: float
    capital_fin: float


@dataclass
class ResultatLPP:
    """Résultat du calcul LPP"""
    capital_initial: float
    capital_final: float
    rente_mensuelle: float
    salaire_coordonne: float
    projection: List[ProjectionAnnuelle]
    total_cotisations: float
    total_interets: float


@dataclass
class PlafonnementCouple:
    """Résultat du plafonnement couple"""
    rente_personne: float
    rente_conjoint: float
    plafonne: bool
    excedent: float
    total_theorique: float
    total_final: float


@dataclass
class ScenarioRachat:
    """Scénario de rachat"""
    nom: str
    description: str
    cout_total: float
    gain_mensuel: float
    gain_annuel: float
    gain_20_ans: float
    rente_totale: float
    recommande: bool
    cout_net: Optional[float] = None
    economie_impot: Optional[float] = None


# ============================================================================
# FONCTIONS DE CALCUL LPP
# ============================================================================

def get_taux_epargne(age: int) -> float:
    """
    Obtient le taux d'épargne LPP selon l'âge
    
    Args:
        age: Âge de la personne
        
    Returns:
        Taux d'épargne applicable (entre 0 et 0.18)
    """
    if age < 25:
        return 0.0
    if age <= 34:
        return LPP.TAUX_EPARGNE[25]
    if age <= 44:
        return LPP.TAUX_EPARGNE[35]
    if age <= 54:
        return LPP.TAUX_EPARGNE[45]
    return LPP.TAUX_EPARGNE[55]


def calculer_salaire_coordonne(salaire_brut: float) -> float:
    """
    Calcule le salaire coordonné (base de calcul LPP)
    
    Args:
        salaire_brut: Salaire annuel brut
        
    Returns:
        Salaire coordonné (salaire assuré - déduction de coordination)
    """
    if salaire_brut < LPP.SALAIRE_MIN:
        return 0.0
    
    salaire_assure = min(salaire_brut, LPP.SALAIRE_MAX)
    return max(0.0, salaire_assure - LPP.DEDUCTION_COORD)


def calculer_lpp(
    age_actuel: int,
    age_retraite: int,
    salaire_actuel: float,
    capital_initial: float,
    progression_salariale: float = 0.005
) -> ResultatLPP:
    """
    Calcule la projection LPP complète avec accumulation année par année
    
    Args:
        age_actuel: Âge actuel
        age_retraite: Âge de départ à la retraite
        salaire_actuel: Salaire annuel actuel
        capital_initial: Capital LPP actuel
        progression_salariale: Taux de progression salariale annuel (défaut: 0.5%)
        
    Returns:
        ResultatLPP avec capital final, rente et projection détaillée
    """
    capital = capital_initial
    salaire = salaire_actuel
    projection_annuelle = []
    
    for age in range(age_actuel, age_retraite):
        taux_epargne = get_taux_epargne(age)
        salaire_coordonne = calculer_salaire_coordonne(salaire)
        cotisation_annuelle = salaire_coordonne * taux_epargne
        interets = capital * LPP.TAUX_INTERET
        
        projection_annuelle.append(ProjectionAnnuelle(
            age=age,
            salaire=round(salaire),
            salaire_coordonne=round(salaire_coordonne),
            taux_epargne=round(taux_epargne * 100, 2),
            cotisation=round(cotisation_annuelle),
            interets=round(interets),
            capital_debut=round(capital),
            capital_fin=round(capital + cotisation_annuelle + interets)
        ))
        
        capital += cotisation_annuelle + interets
        salaire *= (1 + progression_salariale)
    
    rente_mensuelle = (capital * LPP.TAUX_CONVERSION) / 12
    total_cotisations = sum(p.cotisation for p in projection_annuelle)
    total_interets = sum(p.interets for p in projection_annuelle)
    
    return ResultatLPP(
        capital_initial=capital_initial,
        capital_final=round(capital),
        rente_mensuelle=round(rente_mensuelle, 2),
        salaire_coordonne=calculer_salaire_coordonne(salaire_actuel),
        projection=projection_annuelle,
        total_cotisations=total_cotisations,
        total_interets=total_interets
    )


# ============================================================================
# FONCTIONS DE CALCUL AVS
# ============================================================================

def calculer_avs(
    salaire_moyen: float,
    annees_cotisees: int,
    annees_bonif_education: int = 0,
    annees_bonif_assistance: int = 0
) -> ResultatAVS:
    """
    Calcule la rente AVS selon les formules officielles 2025
    
    Formule: rente = 1260 + (ramd / 90720) × 1260
    avec plafonnement et réduction pour années manquantes
    
    Args:
        salaire_moyen: Revenu annuel moyen de carrière
        annees_cotisees: Nombre d'années cotisées (incluant projection)
        annees_bonif_education: Années de bonification éducative
        annees_bonif_assistance: Années de bonification pour tâches d'assistance
        
    Returns:
        ResultatAVS avec rente finale et détails de calcul
    """
    # Calcul des bonifications (créditées sur le RAMD)
    if annees_cotisees > 0:
        total_bonifications = (
            (annees_bonif_education + annees_bonif_assistance) 
            * AVS.BONIF_CREDIT_ANNUEL
        ) / annees_cotisees
    else:
        total_bonifications = 0.0
    
    # Revenu annuel moyen déterminant (RAMD)
    ramd = min(salaire_moyen + total_bonifications, AVS.RAMD_MAX * 1.5)
    
    # Calcul de la rente selon l'échelle 44
    if ramd >= AVS.RAMD_MAX:
        rente_complete = AVS.RENTE_MAX
    elif ramd <= AVS.RAMD_MAX / 3:
        # Formule pour les bas revenus (rente minimale garantie)
        rente_complete = AVS.RENTE_MIN
    else:
        # Formule linéaire entre min et max
        ratio = ramd / AVS.RAMD_MAX
        rente_complete = AVS.RENTE_MIN + (AVS.RENTE_MAX - AVS.RENTE_MIN) * ratio
    
    # Réduction pour années manquantes
    annees_manquantes = max(0, AVS.CARRIERE_PLEINE - annees_cotisees)
    taux_reduction = annees_manquantes * AVS.REDUCTION_PAR_ANNEE
    rente_finale_brute = rente_complete * (1 - min(taux_reduction, 1.0))
    
    # La rente ne peut pas être inférieure à la rente minimale proportionnelle
    if annees_cotisees > 0:
        rente_min_proportionnelle = AVS.RENTE_MIN * (annees_cotisees / AVS.CARRIERE_PLEINE)
        rente_finale = max(rente_finale_brute, rente_min_proportionnelle)
    else:
        rente_finale = 0.0
    
    return ResultatAVS(
        rente=round(rente_finale, 2),
        rente_complete=round(rente_complete, 2),
        ramd=round(ramd),
        annees_manquantes=annees_manquantes,
        taux_reduction=round(taux_reduction * 100, 1),
        bonifications=round(total_bonifications)
    )


def appliquer_plafonnement_couple(
    rente_personne: float,
    rente_conjoint: float
) -> PlafonnementCouple:
    """
    Applique le plafonnement couple (150% de la rente max)
    
    Args:
        rente_personne: Rente AVS de la personne
        rente_conjoint: Rente AVS du conjoint
        
    Returns:
        PlafonnementCouple avec rentes ajustées si nécessaire
    """
    total_theorique = rente_personne + rente_conjoint
    
    if total_theorique <= AVS.PLAFOND_COUPLE:
        return PlafonnementCouple(
            rente_personne=rente_personne,
            rente_conjoint=rente_conjoint,
            plafonne=False,
            excedent=0.0,
            total_theorique=total_theorique,
            total_final=total_theorique
        )
    
    # Plafonnement proportionnel
    excedent = total_theorique - AVS.PLAFOND_COUPLE
    ratio_personne = rente_personne / total_theorique
    
    return PlafonnementCouple(
        rente_personne=round((rente_personne - excedent * ratio_personne), 2),
        rente_conjoint=round((rente_conjoint - excedent * (1 - ratio_personne)), 2),
        plafonne=True,
        excedent=round(excedent, 2),
        total_theorique=round(total_theorique, 2),
        total_final=AVS.PLAFOND_COUPLE
    )


# ============================================================================
# FONCTIONS DE SCÉNARIOS DE RACHAT
# ============================================================================

def calculer_scenarios_rachats(
    resultat_avs: ResultatAVS,
    resultat_lpp: ResultatLPP,
    annees_restantes: int
) -> List[ScenarioRachat]:
    """
    Calcule les différents scénarios de rachat possibles
    
    Args:
        resultat_avs: Résultat du calcul AVS
        resultat_lpp: Résultat du calcul LPP
        annees_restantes: Années restantes jusqu'à la retraite
        
    Returns:
        Liste des scénarios de rachat avec coûts et gains
    """
    scenarios = []
    
    # Scénario 1: Sans rachat (baseline)
    scenarios.append(ScenarioRachat(
        nom="Sans rachat",
        description="Situation actuelle projetée",
        cout_total=0.0,
        gain_mensuel=0.0,
        gain_annuel=0.0,
        gain_20_ans=0.0,
        rente_totale=resultat_avs.rente + resultat_lpp.rente_mensuelle,
        recommande=False
    ))
    
    # Scénario 2: Rachat LPP optimisé (si éligible)
    if resultat_lpp.salaire_coordonne > 0 and annees_restantes >= 3:
        potentiel_rachat = (
            resultat_lpp.salaire_coordonne 
            * 0.18 
            * min(annees_restantes, 10)
        )
        gain_capital = potentiel_rachat
        gain_rente_mensuelle = (gain_capital * LPP.TAUX_CONVERSION) / 12
        economie_impot = potentiel_rachat * 0.25  # Estimation 25% d'économie fiscale
        
        scenarios.append(ScenarioRachat(
            nom="Rachat LPP optimisé",
            description=f"Rachat étalé sur {min(annees_restantes, 5)} ans",
            cout_total=round(potentiel_rachat),
            cout_net=round(potentiel_rachat - economie_impot),
            economie_impot=round(economie_impot),
            gain_mensuel=round(gain_rente_mensuelle),
            gain_annuel=round(gain_rente_mensuelle * 12),
            gain_20_ans=round(gain_rente_mensuelle * 12 * 20),
            rente_totale=resultat_avs.rente + resultat_lpp.rente_mensuelle + gain_rente_mensuelle,
            recommande=True
        ))
    
    # Scénario 3: Comblement lacunes AVS (si applicable)
    if 0 < resultat_avs.annees_manquantes <= 5:
        cout_rachat_avs = resultat_avs.annees_manquantes * 10500  # Estimation
        gain_par_annee = AVS.RENTE_MAX * AVS.REDUCTION_PAR_ANNEE
        gain_mensuel = gain_par_annee * resultat_avs.annees_manquantes
        
        scenarios.append(ScenarioRachat(
            nom="Comblement lacunes AVS",
            description=f"Rachat de {resultat_avs.annees_manquantes} année(s) manquante(s)",
            cout_total=round(cout_rachat_avs),
            gain_mensuel=round(gain_mensuel),
            gain_annuel=round(gain_mensuel * 12),
            gain_20_ans=round(gain_mensuel * 12 * 20),
            rente_totale=resultat_avs.rente_complete + resultat_lpp.rente_mensuelle,
            recommande=resultat_avs.annees_manquantes >= 3
        ))
    
    return scenarios


# ============================================================================
# FONCTION PRINCIPALE DE CALCUL COMPLET
# ============================================================================

def calculer_retraite_complete(
    # Informations personnelles
    age_actuel: int,
    age_retraite: int,
    statut_civil: str,  # 'celibataire' ou 'marie'
    
    # Revenus
    salaire_actuel: float,
    salaire_moyen: float,
    
    # AVS
    annees_cotisees: int,
    annees_bonif_education: int = 0,
    annees_bonif_assistance: int = 0,
    
    # LPP
    capital_lpp: float = 0.0,
    
    # Conjoint (si marié)
    situation_conjoint: Optional[str] = None,  # 'sait', 'ne_sait_pas', 'jamais_travaille'
    rente_conjoint: Optional[float] = None
) -> Dict:
    """
    Calcule la projection de retraite complète
    
    Args:
        age_actuel: Âge actuel
        age_retraite: Âge de départ à la retraite souhaité
        statut_civil: 'celibataire' ou 'marie'
        salaire_actuel: Salaire annuel brut actuel
        salaire_moyen: Salaire annuel moyen de carrière
        annees_cotisees: Années déjà cotisées à l'AVS
        annees_bonif_education: Années de bonification éducative
        annees_bonif_assistance: Années de bonification pour assistance
        capital_lpp: Capital LPP actuel
        situation_conjoint: Situation du conjoint si marié
        rente_conjoint: Rente AVS du conjoint si connue
        
    Returns:
        Dictionnaire avec tous les résultats de calcul
    """
    # Projection des années totales
    annees_restantes = age_retraite - age_actuel
    annees_totales = annees_cotisees + annees_restantes
    
    # Calculs AVS et LPP
    avs = calculer_avs(
        salaire_moyen=salaire_moyen,
        annees_cotisees=annees_totales,
        annees_bonif_education=annees_bonif_education,
        annees_bonif_assistance=annees_bonif_assistance
    )
    
    lpp = calculer_lpp(
        age_actuel=age_actuel,
        age_retraite=age_retraite,
        salaire_actuel=salaire_actuel,
        capital_initial=capital_lpp
    )
    
    # Gestion du conjoint (si marié)
    avs_ajuste = avs
    conjoint_info = None
    
    if statut_civil == 'marie':
        # Déterminer la rente du conjoint
        if situation_conjoint == 'sait' and rente_conjoint is not None:
            rente_conj = rente_conjoint
            source_conjoint = "Montant saisi"
        elif situation_conjoint == 'jamais_travaille':
            rente_conj = AVS.RENTE_MIN
            source_conjoint = "Rente minimale estimée"
        else:
            rente_conj = AVS.RENTE_MEDIANE
            source_conjoint = "Estimation médiane"
        
        # Appliquer le plafonnement couple
        plafonnement = appliquer_plafonnement_couple(avs.rente, rente_conj)
        
        if plafonnement.plafonne:
            # Créer une copie modifiée du résultat AVS
            avs_ajuste = ResultatAVS(
                rente=plafonnement.rente_personne,
                rente_complete=avs.rente_complete,
                ramd=avs.ramd,
                annees_manquantes=avs.annees_manquantes,
                taux_reduction=avs.taux_reduction,
                bonifications=avs.bonifications
            )
        
        conjoint_info = {
            'rente': plafonnement.rente_conjoint if plafonnement.plafonne else rente_conj,
            'source': source_conjoint,
            'plafonnement': {
                'plafonne': plafonnement.plafonne,
                'rente_personne': plafonnement.rente_personne,
                'rente_conjoint': plafonnement.rente_conjoint,
                'excedent': plafonnement.excedent,
                'total_theorique': plafonnement.total_theorique,
                'total_final': plafonnement.total_final
            }
        }
    
    # Scénarios de rachat
    scenarios = calculer_scenarios_rachats(avs_ajuste, lpp, annees_restantes)
    
    # Total
    total = avs_ajuste.rente + lpp.rente_mensuelle
    
    return {
        'avs': {
            'rente': avs_ajuste.rente,
            'rente_complete': avs_ajuste.rente_complete,
            'ramd': avs_ajuste.ramd,
            'annees_manquantes': avs_ajuste.annees_manquantes,
            'taux_reduction': avs_ajuste.taux_reduction,
            'bonifications': avs_ajuste.bonifications
        },
        'lpp': {
            'capital_initial': lpp.capital_initial,
            'capital_final': lpp.capital_final,
            'rente_mensuelle': lpp.rente_mensuelle,
            'salaire_coordonne': lpp.salaire_coordonne,
            'total_cotisations': lpp.total_cotisations,
            'total_interets': lpp.total_interets,
            'projection': [
                {
                    'age': p.age,
                    'salaire': p.salaire,
                    'salaire_coordonne': p.salaire_coordonne,
                    'taux_epargne': p.taux_epargne,
                    'cotisation': p.cotisation,
                    'interets': p.interets,
                    'capital_debut': p.capital_debut,
                    'capital_fin': p.capital_fin
                }
                for p in lpp.projection
            ]
        },
        'conjoint': conjoint_info,
        'scenarios': [
            {
                'nom': s.nom,
                'description': s.description,
                'cout_total': s.cout_total,
                'cout_net': s.cout_net,
                'economie_impot': s.economie_impot,
                'gain_mensuel': s.gain_mensuel,
                'gain_annuel': s.gain_annuel,
                'gain_20_ans': s.gain_20_ans,
                'rente_totale': s.rente_totale,
                'recommande': s.recommande
            }
            for s in scenarios
        ],
        'total': total,
        'annees_totales': annees_totales,
        'annees_restantes': annees_restantes
    }


# ============================================================================
# EXEMPLES D'UTILISATION
# ============================================================================

def exemple_calcul_simple():
    """Exemple de calcul simple pour une personne célibataire"""
    print("=" * 80)
    print("EXEMPLE 1: Personne célibataire")
    print("=" * 80)
    
    resultat = calculer_retraite_complete(
        age_actuel=45,
        age_retraite=65,
        statut_civil='celibataire',
        salaire_actuel=85000,
        salaire_moyen=75000,
        annees_cotisees=20,
        annees_bonif_education=0,
        annees_bonif_assistance=0,
        capital_lpp=150000
    )
    
    print(f"\n📊 RÉSULTATS:")
    print(f"  • Rente AVS mensuelle: {resultat['avs']['rente']:,.2f} CHF")
    print(f"  • Rente LPP mensuelle: {resultat['lpp']['rente_mensuelle']:,.2f} CHF")
    print(f"  • TOTAL mensuel: {resultat['total']:,.2f} CHF")
    print(f"  • TOTAL annuel: {resultat['total'] * 12:,.2f} CHF")
    
    print(f"\n⚠️  LACUNES AVS:")
    print(f"  • Années manquantes: {resultat['avs']['annees_manquantes']}")
    print(f"  • Réduction appliquée: {resultat['avs']['taux_reduction']}%")
    
    print(f"\n💰 CAPITAL LPP:")
    print(f"  • Capital actuel: {resultat['lpp']['capital_initial']:,.0f} CHF")
    print(f"  • Capital projeté: {resultat['lpp']['capital_final']:,.0f} CHF")
    
    print(f"\n🎯 SCÉNARIOS DE RACHAT:")
    for scenario in resultat['scenarios']:
        if scenario['recommande']:
            print(f"  ⭐ {scenario['nom']}")
        else:
            print(f"  • {scenario['nom']}")
        print(f"     - Coût: {scenario['cout_total']:,.0f} CHF")
        print(f"     - Gain mensuel: +{scenario['gain_mensuel']:,.0f} CHF")
        print(f"     - Gain sur 20 ans: +{scenario['gain_20_ans']:,.0f} CHF")
    
    return resultat


def exemple_calcul_couple():
    """Exemple de calcul pour un couple marié"""
    print("\n\n" + "=" * 80)
    print("EXEMPLE 2: Couple marié avec plafonnement")
    print("=" * 80)
    
    resultat = calculer_retraite_complete(
        age_actuel=50,
        age_retraite=65,
        statut_civil='marie',
        salaire_actuel=95000,
        salaire_moyen=88000,
        annees_cotisees=28,
        annees_bonif_education=5,
        annees_bonif_assistance=0,
        capital_lpp=250000,
        situation_conjoint='sait',
        rente_conjoint=2100
    )
    
    print(f"\n📊 RÉSULTATS:")
    print(f"  • Rente AVS personne: {resultat['avs']['rente']:,.2f} CHF")
    print(f"  • Rente LPP mensuelle: {resultat['lpp']['rente_mensuelle']:,.2f} CHF")
    print(f"  • TOTAL mensuel: {resultat['total']:,.2f} CHF")
    
    if resultat['conjoint']:
        print(f"\n👫 CONJOINT:")
        print(f"  • Rente conjoint: {resultat['conjoint']['rente']:,.2f} CHF")
        print(f"  • Source: {resultat['conjoint']['source']}")
        
        if resultat['conjoint']['plafonnement']['plafonne']:
            print(f"\n⚠️  PLAFONNEMENT COUPLE APPLIQUÉ:")
            plaf = resultat['conjoint']['plafonnement']
            print(f"  • Total théorique: {plaf['total_theorique']:,.2f} CHF")
            print(f"  • Excédent: -{plaf['excedent']:,.2f} CHF")
            print(f"  • Total après plafonnement: {plaf['total_final']:,.2f} CHF")
    
    return resultat


def exemple_export_json():
    """Exemple d'export en JSON pour Shopify"""
    print("\n\n" + "=" * 80)
    print("EXEMPLE 3: Export JSON pour Shopify")
    print("=" * 80)
    
    resultat = calculer_retraite_complete(
        age_actuel=40,
        age_retraite=64,
        statut_civil='celibataire',
        salaire_actuel=75000,
        salaire_moyen=68000,
        annees_cotisees=15,
        capital_lpp=80000
    )
    
    # Export en JSON
    json_output = json.dumps(resultat, indent=2, ensure_ascii=False)
    print("\n📄 JSON OUTPUT:")
    print(json_output[:500] + "...\n")  # Afficher les 500 premiers caractères
    
    return json_output


# ============================================================================
# FONCTION POUR SHOPIFY (API-FRIENDLY)
# ============================================================================

def calculer_retraite_shopify(parametres: Dict) -> str:
    """
    Fonction wrapper pour intégration Shopify
    
    Args:
        parametres: Dictionnaire avec tous les paramètres
        
    Returns:
        JSON string avec tous les résultats
        
    Exemple d'utilisation:
        params = {
            'age_actuel': 45,
            'age_retraite': 65,
            'statut_civil': 'celibataire',
            'salaire_actuel': 85000,
            'salaire_moyen': 75000,
            'annees_cotisees': 20,
            'capital_lpp': 150000
        }
        resultat_json = calculer_retraite_shopify(params)
    """
    try:
        resultat = calculer_retraite_complete(**parametres)
        return json.dumps({
            'success': True,
            'data': resultat
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        }, ensure_ascii=False, indent=2)


# ============================================================================
# TESTS UNITAIRES
# ============================================================================

def test_calculs():
    """Tests de validation des calculs"""
    print("\n\n" + "=" * 80)
    print("TESTS DE VALIDATION")
    print("=" * 80)
    
    # Test 1: Salaire coordonné
    print("\n✓ Test 1: Salaire coordonné LPP")
    assert calculer_salaire_coordonne(50000) == 50000 - 26460
    assert calculer_salaire_coordonne(20000) == 0  # En dessous du minimum
    print("  PASSED")
    
    # Test 2: Taux d'épargne
    print("\n✓ Test 2: Taux d'épargne par âge")
    assert get_taux_epargne(20) == 0.0
    assert get_taux_epargne(30) == 0.07
    assert get_taux_epargne(40) == 0.10
    assert get_taux_epargne(50) == 0.15
    assert get_taux_epargne(60) == 0.18
    print("  PASSED")
    
    # Test 3: AVS carrière complète
    print("\n✓ Test 3: AVS carrière complète")
    avs = calculer_avs(90720, 44, 0, 0)
    assert avs.rente == 2520.0  # Rente maximale
    assert avs.annees_manquantes == 0
    print(f"  PASSED - Rente: {avs.rente} CHF")
    
    # Test 4: AVS avec lacunes
    print("\n✓ Test 4: AVS avec lacunes")
    avs = calculer_avs(75000, 40, 0, 0)
    assert avs.annees_manquantes == 4
    assert avs.taux_reduction > 0
    print(f"  PASSED - Réduction: {avs.taux_reduction}%")
    
    # Test 5: Plafonnement couple
    print("\n✓ Test 5: Plafonnement couple")
    plaf = appliquer_plafonnement_couple(2520, 2520)
    assert plaf.plafonne == True
    assert plaf.total_final == 3780
    print(f"  PASSED - Plafonnement appliqué: {plaf.total_final} CHF")
    
    print("\n✅ Tous les tests sont passés!")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🇨🇭 CALCULATEUR DE RETRAITE SUISSE 2025")
    print("=" * 80)
    print("Script Python avec calculs identiques à l'application React\n")
    
    # Exécuter les exemples
    exemple_calcul_simple()
    exemple_calcul_couple()
    exemple_export_json()
    
    # Exécuter les tests
    test_calculs()
    
    print("\n" + "=" * 80)
    print("✅ Script prêt pour intégration Shopify!")
    print("=" * 80)
    print("\nUtilisation pour Shopify:")
    print("  from calculateur_retraite import calculer_retraite_shopify")
    print("  resultat_json = calculer_retraite_shopify(parametres)")
