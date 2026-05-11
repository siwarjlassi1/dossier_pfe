#La logique conversationnelle pour vérifier une commande
import logging
from .utils import get_slot, close, elicit_slot, delegate, is_french

logger = logging.getLogger()
logger.setLevel(logging.INFO)

call_microservice = None

MAX_ATTEMPTS = 3


def handle_verifier_commande(event):
    """Vérifie le statut d'une commande."""

    fr = is_french(event)
    invocation_source = event.get("invocationSource", "DialogCodeHook")

    # ── Récupérer les session attributes ─────────────────────────
    session_attributes = event.get("sessionState", {}) \
                              .get("sessionAttributes", {}) or {}

    order_id = get_slot(event, "OrderId")
    if order_id:
        order_id = order_id.strip()

    # ── ÉTAPE 1 : Demande l'order ID ─────────────────────────────
    if not order_id:
        msg = "Veuillez entrer votre numéro de commande :" if fr \
              else "Please enter your order ID:"
        return elicit_slot(event, "OrderId", msg)

    # ── ÉTAPE 2 : Fulfillment ─────────────────────────────────────
    if invocation_source == "FulfillmentCodeHook":
        return _check_order(event, order_id, fr, session_attributes)

    return delegate(event)


def _check_order(event, order_id, fr, session_attributes):
    try:
        logger.info(f"Vérification commande : {order_id}")

        # ── Appel microservice ────────────────────────────────────
        result = call_microservice("verify-order", {
            "action":   "check_order",
            "order_id": order_id,
        })

        if not result.get("found"):

            # ── Gestion des tentatives ────────────────────────────
            attempts = int(session_attributes.get("order_attempts", 0)) + 1
            session_attributes["order_attempts"] = str(attempts)

            if attempts >= MAX_ATTEMPTS:
                session_attributes["order_attempts"] = "0"
                msg = (
                    "❌ Vous avez épuisé vos 3 tentatives.\n"
                    "Que souhaitez-vous faire ?"
                    ) if fr else (
                        "❌ You have used all 3 attempts.\n"
                        "What would you like to do?"
                        )

                # ── Afficher des boutons de menu ──────────────────────────
                buttons = [
                    {"text": "🛒 Order a product",   "value": "I want to order a product"},
                    {"text": "🔧 Report a problem",  "value": "I want to report a problem"},
                    {"text": "📦 Check an order",    "value": "I want to check my order"},
                    {"text": "❌ Cancel an order",   "value": "I want to cancel my order"},
                    ] if not fr else [
                        {"text": "🛒 Commander",         "value": "Je veux commander un produit"},
                        {"text": "🔧 Signaler une panne","value": "Je veux signaler un problème"},
                        {"text": "📦 Vérifier commande", "value": "Je veux vérifier ma commande"},
                        {"text": "❌ Annuler commande",  "value": "Je veux annuler ma commande"},
                        ]

                return close_with_buttons(event, msg, buttons, session_attributes)


            # ── Redemander l'OrderId ──────────────────────────────
            remaining = MAX_ATTEMPTS - attempts
            msg = (
                f"❌ Aucune commande trouvée avec le numéro "
                f"'{order_id}'.\n"
                f"Il vous reste {remaining} tentative(s).\n"
                f"Veuillez entrer votre numéro de commande :"
            ) if fr else (
                f"❌ No order found with ID '{order_id}'.\n"
                f"You have {remaining} attempt(s) remaining.\n"
                f"Please enter your order ID:"
            )

            return elicit_slot_with_session(
                event, "OrderId", msg, session_attributes
            )

        # ── Réinitialiser les tentatives si succès ────────────────
        session_attributes["order_attempts"] = "0"

        # ── Récupérer les infos ───────────────────────────────────
        status      = result.get("status", "UNKNOWN")
        product_ref = result.get("product_ref", "N/A")
        payment     = result.get("payment_method", "N/A")
        created_at  = result.get("created_at", "N/A")

        status_messages_fr = {
            "PENDING":   "En attente de traitement",
            "CONFIRMED": "Confirmée",
            "SHIPPED":   "Expédiée",
            "DELIVERED": "Livrée",
            "CANCELLED": "Annulée",
        }
        status_messages_en = {
            "PENDING":   "Pending processing",
            "CONFIRMED": "Confirmed",
            "SHIPPED":   "Shipped",
            "DELIVERED": "Delivered",
            "CANCELLED": "Cancelled",
        }

        status_label = status_messages_fr.get(status, status) if fr \
                       else status_messages_en.get(status, status)

        msg = (
            f"✅ Voici les détails de votre commande :\n"
            f"- Numéro : {order_id}\n"
            f"- Produit : {product_ref}\n"
            f"- Paiement : {payment}\n"
            f"- Date : {created_at}\n"
            f"- Statut : {status_label}"
        ) if fr else (
            f"✅ Here are your order details:\n"
            f"- Order ID: {order_id}\n"
            f"- Product: {product_ref}\n"
            f"- Payment: {payment}\n"
            f"- Date: {created_at}\n"
            f"- Status: {status_label}"
        )

        return close_with_session(event, msg, session_attributes)

    except Exception as e:
        logger.exception("Erreur vérification commande")
        msg = "Désolé, une erreur est survenue. Veuillez réessayer." if fr \
              else "Sorry, an error occurred. Please try again."
        return close_with_session(event, msg, 
                                  session_attributes, 
                                  fulfilled=False)


# ── Helpers avec session attributes ──────────────────────────────

def elicit_slot_with_session(event, slot_name, message, session_attributes):
    """ElicitSlot en conservant les session attributes."""

    intent = event["sessionState"]["intent"]
    slots = intent.get("slots", {})
    slots["OrderId"] = None
    intent["slots"] = slots

    # ── ✅ Fix : forcer l'état à "InProgress" ─────────────────────
    intent["state"] = "InProgress"

    return {
        "sessionState": {
            "dialogAction": {
                "type": "ElicitSlot",
                "slotToElicit": slot_name,
            },
            "intent": intent,
            "sessionAttributes": session_attributes,
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


def close_with_buttons(event, message, buttons, session_attributes):
    """Close avec boutons de menu."""
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {
                **event["sessionState"]["intent"],
                "state": "Failed",
            },
            "sessionAttributes": session_attributes,
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message
            },
            {
                "contentType": "ImageResponseCard",
                "imageResponseCard": {
                    "title": "Menu principal" if False else "Main menu",
                    "buttons": buttons,
                },
            }
        ],
    }




def close_with_session(event, message, session_attributes, fulfilled=True):
    """Close en conservant les session attributes."""
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {
                **event["sessionState"]["intent"],
                "state": "Fulfilled" if fulfilled else "Failed",
            },
            "sessionAttributes": session_attributes,
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }

