"""
model_normalizer.py
-------------------
Généré automatiquement à partir du fichier GRXML Nuance HP
(in8200_GetModelNumber_1.grxml).

Normalise les références produit saisies librement par l'utilisateur.

Exemples:
    "HP LaserJet Pro M twenty six"       → "m26"
    "one two"                             → "m12"
    "m 26 nw printer"                     → "m26"
    "HP LaserJet Pro M twelve w printer"  → "m12"
    "probook 450"                         → "probook450"
    "elitebook 840"                       → "elitebook840"
"""

import re
import json
import os

# ── Chargement du mapping GRXML ───────────────────────────────────
# Le fichier grxml_mapping.json est dans le même dossier que ce module
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MAP_FILE = os.path.join(_BASE_DIR, "grxml_mapping.json")

with open(_MAP_FILE, "r", encoding="utf-8") as _f:
    GRXML_MAP: dict = json.load(_f)

# ── Mots parasites à supprimer avant le lookup ───────────────────
# Inclut : marque, gamme, suffixes de modèle, types d'appareil
_NOISE = re.compile(
    r"\b(h[_\s]?p|laserjet|laser\s+jet|pro|enterprise|"
    r"managed|flow|never_stop|color|colour|"
    r"printer|multi\s+function\s+printer|multifunction|m_f_p|mfp|"
    r"all\s+in\s+one|"
    r"nw|dw|fw|dn|fn|fnw|fdw|fdh|fdn|cdw|"
    r"xh|xs|xm|se|tn|xi|le|gn|hn|hx|"
    r"\bw\b|\bn\b|\ba\b)\b",
    re.IGNORECASE,
)


def normalize_product_ref(user_input: str) -> str:
    """
    Normalise une référence produit saisie librement.

    Stratégie (dans l'ordre) :
    1. Lookup direct               "m26"           → "m26"
    2. Lookup sans espaces         "m 26"          → "m26"
    3. Après suppression du bruit  "m26 nw mfp"    → "m26"
    4. Idem(nettoyé)+ sans espaces
    5. Suppression du "m" isolé    "m twenty six"  → "twenty six" → "m26"
    6. Extraction "m + chiffres"   "m 26 ..."      → "m26"
    7. Chiffres seuls              "26"            → recherché dans map
    8. Retourne l'original si aucun match

    Args:
        user_input: texte brut saisi par l'utilisateur

    Returns:
        Référence canonique (ex: "m26") ou l'entrée d'origine si non trouvée
    """
    if not user_input:
        return user_input

    #key = user_input.strip().lower()
    #key = re.sub(r"([a-z])([0-9])", r"\1 \2", key)
    #key = re.sub(r"([0-9])([a-z])", r"\1 \2", key)


    key = user_input.strip()

    # séparer minuscules → MAJUSCULES
    key = re.sub(r'([a-z])([A-Z])', r'\1 \2', key)

    # séparer lettres → chiffres
    key = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', key)

    # séparer chiffres → lettres
    key = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', key)

    key = key.lower()

    # 1. Lookup direct
    if key in GRXML_MAP:
        return GRXML_MAP[key]

    # 2. Sans espaces (ex: "m 26" → "m26")
    no_space = key.replace(" ", "").replace("_", "")
    if no_space in GRXML_MAP:
        return GRXML_MAP[no_space]

    # 3. Après suppression du bruit
    cleaned = _NOISE.sub(" ", key)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned in GRXML_MAP:
        return GRXML_MAP[cleaned]

    # 4. Nettoyé + sans espaces
    cleaned_ns = cleaned.replace(" ", "")
    if cleaned_ns in GRXML_MAP:
        return GRXML_MAP[cleaned_ns]

    # 5. Supprimer le "m" isolé (ex: "m twenty six" → "twenty six")
    cleaned2 = re.sub(r"\bm\b", "", cleaned).strip()
    cleaned2 = re.sub(r"\s+", " ", cleaned2).strip()
    if cleaned2 in GRXML_MAP:
        return GRXML_MAP[cleaned2]

    # 6. Extraire "m + chiffres" (ex: "m 26 nw" → "m26")
    m_match = re.search(r"\bm\s*(\d+)\b", cleaned)
    if m_match:
        candidate = "m" + m_match.group(1)
        if candidate in GRXML_MAP:
            return GRXML_MAP[candidate]

    # 7. Chiffres seuls restants
    digits_only = re.sub(r"[^\d]", "", cleaned)
    if digits_only and digits_only in GRXML_MAP:
        return GRXML_MAP[digits_only]

    # 8. Aucun match
    return user_input
