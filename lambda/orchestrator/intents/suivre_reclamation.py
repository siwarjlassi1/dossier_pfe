import logging
from .utils import get_slot, is_french

logger = logging.getLogger()
logger.setLevel(logging.INFO)

call_microservice = None

MAX_ATTEMPTS = 3


def handle_suivre_reclamation(event):
    """Tracks the status of a claim."""

    fr = is_french(event)
    invocation_source = event.get("invocationSource", "DialogCodeHook")

    # ── Récupérer les session attributes ─────────────────────────
    session_attributes = event.get("sessionState", {}) \
                              .get("sessionAttributes", {}) or {}

    reclamation_id = get_slot(event, "ReclamationId")
    if reclamation_id:
        reclamation_id = reclamation_id.strip()

    # ── ÉTAPE 1 : Demande le ReclamationId ───────────────────────
    if not reclamation_id:
        msg = "Veuillez entrer votre numéro de réclamation :" if fr \
              else "Please enter your claim ID:"
        return _elicit_slot(event, "ReclamationId", msg, session_attributes)

    # ── ÉTAPE 2 : Fulfillment ─────────────────────────────────────
    if invocation_source == "FulfillmentCodeHook":
        return _check_reclamation(event, reclamation_id, fr, session_attributes)

    return _delegate(event, session_attributes)


def _check_reclamation(event, reclamation_id, fr, session_attributes):
    try:
        logger.info(f"Tracking claim : {reclamation_id}")

        # ── Appel microservice ────────────────────────────────────
        result = call_microservice("track-claim", {
            "action":         "check_reclamation",
            "reclamation_id": reclamation_id,
        })

        if not result.get("found"):

            # ── Gestion des tentatives ────────────────────────────
            attempts = int(session_attributes.get("reclamation_attempts", 0)) + 1
            session_attributes["reclamation_attempts"] = str(attempts)

            if attempts >= MAX_ATTEMPTS:
                session_attributes["reclamation_attempts"] = "0"
                msg = (
                    "❌ Vous avez épuisé vos 3 tentatives.\n"
                    "Que souhaitez-vous faire ?"
                ) if fr else (
                    "❌ You have used all 3 attempts.\n"
                    "What would you like to do?"
                )

                buttons = [
                    {"text": "🛒 Commander",          "value": "Je veux commander un produit"},
                    {"text": "🔧 Signaler une panne",  "value": "Je veux signaler un problème"},
                    {"text": "📦 Vérifier commande",   "value": "Je veux vérifier ma commande"},
                    {"text": "❌ Annuler commande",    "value": "Je veux annuler ma commande"},
                ] if fr else [
                    {"text": "🛒 Order a product",    "value": "I want to order a product"},
                    {"text": "🔧 Report a problem",   "value": "I want to report a problem"},
                    {"text": "📦 Check an order",     "value": "I want to check my order"},
                    {"text": "❌ Cancel an order",    "value": "I want to cancel my order"},
                ]

                return _close_with_buttons(event, msg, buttons, session_attributes, fr)

            # ── Redemander le ReclamationId ───────────────────────
            remaining = MAX_ATTEMPTS - attempts
            msg = (
                f"❌ Aucune réclamation trouvée avec le numéro "
                f"'{reclamation_id}'.\n"
                f"Il vous reste {remaining} tentative(s).\n"
                f"Veuillez entrer votre numéro de réclamation :"
            ) if fr else (
                f"❌ No claim found with ID '{reclamation_id}'.\n"
                f"You have {remaining} attempt(s) remaining.\n"
                f"Please enter your claim ID:"
            )

            return _elicit_slot_with_session(
                event, "ReclamationId", msg, session_attributes
            )

        # ── Réinitialiser les tentatives si succès ────────────────
        session_attributes["reclamation_attempts"] = "0"

        # ── Récupérer les infos ───────────────────────────────────
        status           = result.get("status", "UNKNOWN")
        product_ref      = result.get("product_ref", "N/A")
        problem          = result.get("problem_description", "N/A")
        solution         = result.get("solution", "N/A")
        warranty         = result.get("under_warranty", False)
        created_at       = result.get("created_at", "N/A")
        problem_category = result.get("problem_category", "N/A")
        summary          = result.get("summary", "")  # 🆕 RÉSUMÉ

        # ── Labels de statut ──────────────────────────────────────
        status_messages_fr = {
            "OPEN":        "🔴 En cours de traitement",
            "IN_PROGRESS": "🟡 En cours de résolution",
            "CLOSED":      "🟢 Résolue",
        }
        status_messages_en = {
            "OPEN":        "🔴 Open - Being processed",
            "IN_PROGRESS": "🟡 In progress",
            "CLOSED":      "🟢 Resolved",
        }

        status_label  = status_messages_fr.get(status, status) if fr \
                        else status_messages_en.get(status, status)

        warranty_label = ("✅ Oui" if warranty else "❌ Non") if fr \
                         else ("✅ Yes" if warranty else "❌ No")

        # ── Message final avec résumé ─────────────────────────────
        if fr:
            msg = (
                f"📋 Voici les détails de votre réclamation :\n\n"
                f"🔖 Numéro   : {reclamation_id}\n"
                f"💻 Produit  : {product_ref}\n"
                f"🔧 Problème : {problem}\n"
                f"🧠 Catégorie : {problem_category}\n"
                f"💡 Solution : {solution}\n"
                f"📊 Statut   : {status_label}\n"
                f"🛡️ Garantie : {warranty_label}\n"
                f"📅 Date     : {created_at}"
            )
            
            # 🆕 Ajouter le résumé si disponible
            if summary:
                msg += f"\n\n📝 Résumé de la conversation :\n{summary}"
            else:
                logger.warning(f"⚠️ Aucun résumé disponible pour {reclamation_id}")
                
        else:
            msg = (
                f"📋 Here are your claim details:\n\n"
                f"🔖 Claim ID  : {reclamation_id}\n"
                f"💻 Product   : {product_ref}\n"
                f"🔧 Problem   : {problem}\n"
                f"🧠 Category  : {problem_category}\n"
                f"💡 Solution  : {solution}\n"
                f"📊 Status    : {status_label}\n"
                f"🛡️ Warranty  : {warranty_label}\n"
                f"📅 Date      : {created_at}"
            )
            
            # 🆕 Ajouter le résumé si disponible
            if summary:
                msg += f"\n\n📝 Conversation Summary:\n{summary}"
            else:
                logger.warning(f"⚠️ No summary available for {reclamation_id}")

        return _close_with_session(event, msg, session_attributes)

    except Exception as e:
        logger.exception("Error tracking claim")
        msg = "Désolé, une erreur est survenue. Veuillez réessayer." if fr \
              else "Sorry, an error occurred. Please try again."
        return _close_with_session(event, msg, session_attributes, fulfilled=False)


# ── Helpers privés (préfixés avec _) ─────────────────────────────

def _elicit_slot(event, slot_name, message, session_attributes):
    """ElicitSlot simple."""
    intent = event["sessionState"]["intent"]
    intent["state"] = "InProgress"
    return {
        "sessionState": {
            "dialogAction": {
                "type":         "ElicitSlot",
                "slotToElicit": slot_name,
            },
            "intent":            intent,
            "sessionAttributes": session_attributes,
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


def _elicit_slot_with_session(event, slot_name, message, session_attributes):
    """ElicitSlot en conservant les session attributes."""
    intent = event["sessionState"]["intent"]
    slots  = intent.get("slots", {})
    slots["ReclamationId"] = None
    intent["slots"] = slots
    intent["state"] = "InProgress"
    return {
        "sessionState": {
            "dialogAction": {
                "type":         "ElicitSlot",
                "slotToElicit": slot_name,
            },
            "intent":            intent,
            "sessionAttributes": session_attributes,
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


def _delegate(event, session_attributes):
    """Délègue à Lex."""
    return {
        "sessionState": {
            "dialogAction":      {"type": "Delegate"},
            "intent":            event["sessionState"]["intent"],
            "sessionAttributes": session_attributes,
        },
    }


def _close_with_buttons(event, message, buttons, session_attributes, fr=True):
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
                "content":     message,
            },
            {
                "contentType": "ImageResponseCard",
                "imageResponseCard": {
                    "title":   "Menu principal" if fr else "Main menu",
                    "buttons": buttons,
                },
            },
        ],
    }


def _close_with_session(event, message, session_attributes, fulfilled=True):
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
