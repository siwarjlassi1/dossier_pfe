import boto3
import logging
from decimal import Decimal
from .voice_adapter import adapt_for_voice, is_voice_call

logger = logging.getLogger()
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# ── Tables ───────────────────────────────────────────────────────
products_table   = dynamodb.Table('hp-products')
orders_table     = dynamodb.Table('hp-orders')
complaints_table = dynamodb.Table('hp-complaints')


# ── Détection langue ─────────────────────────────────────────────
def get_locale(event):
    return event.get("bot", {}).get("localeId", "en_US")

def is_french(event):
    return get_locale(event) == "fr_FR"


# ── Helpers Lex response ─────────────────────────────────────────
def elicit_slot(event, slot_to_elicit, message):
    """Demande à Lex de collecter un slot spécifique."""
    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,  # ✅ ajouté
            "dialogAction": {
                "type": "ElicitSlot",
                "slotToElicit": slot_to_elicit,
            },
            "intent": event["sessionState"]["intent"],
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


def elicit_slot_with_buttons(event, slot_to_elicit, message, buttons):
    """Demande un slot avec des boutons de choix."""
    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,  # ✅ ajouté
            "dialogAction": {
                "type": "ElicitSlot",
                "slotToElicit": slot_to_elicit,
            },
            "intent": event["sessionState"]["intent"],
        },
        "messages": [
            {
                "contentType": "PlainText",       # ✅ ajouté
                "content": message                # ✅ message visible
            },
            {
                "contentType": "ImageResponseCard",
                "imageResponseCard": {
                    "title": message,
                    "buttons": buttons,
                },
            }
        ],
    }


def delegate(event):
    """Délègue le contrôle à Lex pour continuer la collecte des slots."""
    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,  # ✅ ajouté
            "dialogAction": {"type": "Delegate"},
            "intent": event["sessionState"]["intent"],
        },
    }


def close(event, message, fulfilled=True):
    """Termine la conversation avec un message final."""
    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,  # ✅ ajouté
            "dialogAction": {"type": "Close"},
            "intent": {
                **event["sessionState"]["intent"],
                "state": "Fulfilled" if fulfilled else "Failed",
            },
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


# ── Helpers DynamoDB ─────────────────────────────────────────────
def get_slot(event, slot_name):
    """Récupère la valeur d'un slot depuis l'event Lex."""
    slots = event["sessionState"]["intent"].get("slots", {})
    slot  = slots.get(slot_name)
    if slot and slot.get("value"):
        return slot["value"].get("interpretedValue")
    return None


def get_product(product_id):
    """Vérifie si un produit existe dans DynamoDB."""
    try:
        response = products_table.get_item(
            Key={"productId": product_id.lower()}
        )
        return response.get("Item")
    except Exception as e:
        logger.error(f"Erreur DynamoDB get_product : {e}")
        return None


def validate_card_number(card_number):
    """Valide le numéro de carte bancaire avec l'algorithme de Luhn."""
    card_number = card_number.replace(" ", "").replace("-", "")
    if not card_number.isdigit():
        return False
    if len(card_number) < 13 or len(card_number) > 19:
        return False
    # Algorithme de Luhn
    total   = 0
    reverse = card_number[::-1]
    for i, digit in enumerate(reverse):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def get_card_type(card_number):
    """Détecte le type de carte bancaire."""
    card_number = card_number.replace(" ", "").replace("-", "")
    if card_number.startswith("4"):
        return "Visa"
    elif card_number[:2] in ["51", "52", "53", "54", "55"]:
        return "Mastercard"
    elif card_number[:2] in ["34", "37"]:
        return "American Express"
    return "Unknown"


def decimal_to_float(obj):
    """Convertit Decimal en float pour la sérialisation JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError



def elicit_slot_voice(event, slot_to_elicit, message):
    """
    ElicitSlot adapté pour la voix :
    - Pas de boutons (impossible à l'oral)
    - Message court et naturel
    """
    voice = is_voice_call(event)
    clean_message = adapt_for_voice(message, voice)

    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,
            "dialogAction": {
                "type":         "ElicitSlot",
                "slotToElicit": slot_to_elicit,
            },
            "intent": event["sessionState"]["intent"],
        },
        "messages": [
            {"contentType": "PlainText", "content": clean_message}
        ],
    }


def close_voice(event, message, fulfilled=True):
    """
    Close adapté pour la voix.
    """
    voice = is_voice_call(event)
    clean_message = adapt_for_voice(message, voice)

    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,
            "dialogAction": {"type": "Close"},
            "intent": {
                **event["sessionState"]["intent"],
                "state": "Fulfilled" if fulfilled else "Failed",
            },
        },
        "messages": [
            {"contentType": "PlainText", "content": clean_message}
        ],
    }
