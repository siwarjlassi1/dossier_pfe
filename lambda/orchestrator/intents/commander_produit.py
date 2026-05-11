# La logique métier de la commande produit
call_microservice = None
import logging
from .utils import (
    get_slot, elicit_slot, elicit_slot_with_buttons,
    close, delegate, is_french, get_card_type
)
from model_normalizer import normalize_product_ref

logger = logging.getLogger()

MAX_CARD_ATTEMPTS = 3

CARD_KEYWORDS = [
    "card", "carte", "credit card", "creditcard",
    "credit", "carte bancaire", "cb", "bank card",
    "debit card", "debitcard", "visa", "mastercard"
]
CASH_KEYWORDS = [
    "cash", "espèces", "especes",
    "liquide", "en liquide", "en espèces"
]


def handle_commander_produit(event):
    fr = is_french(event)
    invocation_source = event.get("invocationSource", "DialogCodeHook")

    # ── Récupérer les slots ───────────────────────────────────────
    product_type   = get_slot(event, "ProductType")
    product_ref    = get_slot(event, "ProductReference")
    payment_method = get_slot(event, "PaymentMethod")
    card_number    = get_slot(event, "CardNumber")
    card_cvv       = get_slot(event, "CardCVV")

    session_attrs = event.get("sessionState", {}) \
                        .get("sessionAttributes", {}) or {}

    confirmation_state = event.get("sessionState", {}) \
                              .get("intent", {}) \
                              .get("confirmationState", "None")

    # ── ÉTAPE 1 : Type de produit ─────────────────────────────────
    if not product_type:       #Si user n’a rien dit
        msg = "Quel produit souhaitez-vous commander ? (imprimante, ordinateur, tablette...)" if fr \
              else "What product would you like to order? (printer, laptop, tablet...)"
        return elicit_slot(event, "ProductType", msg)

    # ── ÉTAPE 2 : Référence ───────────────────────────────────────
    if not product_ref:    #meme chose
        msg = f"Quelle est la référence de votre {product_type} ? (ex: m12, m26, elitebook840)" if fr \
              else f"What is the reference of the {product_type}? (e.g. m12, m26, elitebook840)"
        return elicit_slot(event, "ProductReference", msg)

    # ── ÉTAPE 2.5 : Normalisation ─────────────────────────────────
    # ici pour corriger erreurs utilisateur
    product_ref = normalize_product_ref(product_ref)
    event["sessionState"]["intent"]["slots"]["ProductReference"] = {
        "value": {"interpretedValue": product_ref, "originalValue": product_ref}
    }

    # ── ÉTAPE 3 : Validation produit ──────────────────────────────
    #appeler backend pour vérifier produit
    result = call_microservice("order", {
        "action": "validate_product",
        "product_ref": product_ref
    })
    if not result.get("valid"):
        msg = f"Désolé, '{product_ref}' est introuvable. Références : m12, m26, elitebook840, probook450, elitepad1000." if fr \
              else f"Sorry, '{product_ref}' was not found. Valid references: m12, m26, elitebook840, probook450, elitepad1000."
        return elicit_slot(event, "ProductReference", msg)

    # ── ÉTAPE 4 : Méthode de paiement ────────────────────────────
    if not payment_method:
        return elicit_slot_with_buttons(
            event, "PaymentMethod",
            "Comment souhaitez-vous payer ?" if fr
            else "How would you like to pay?",
            [
                {"text": "Cash", "value": "Cash"},
                {"text": "Carte bancaire" if fr else "Credit Card",
                 "value": "Carte" if fr else "Card"},
            ]
        )

    # ── Normalisation de la méthode de paiement ──────────────────
    payment_lower = payment_method.lower()

    if any(kw in payment_lower for kw in CARD_KEYWORDS):
        payment_method = "Card"
    elif any(kw in payment_lower for kw in CASH_KEYWORDS):
        payment_method = "Cash"
    else:
        # ── Méthode non reconnue → redemander ─────────────────────
        msg = (
            "❌ Méthode de paiement non reconnue.\n"
            "Veuillez choisir Cash ou Carte bancaire :"
        ) if fr else (
            "❌ Payment method not recognized.\n"
            "Please choose Cash or Credit Card:"
        )
        return elicit_slot_with_buttons(
            event, "PaymentMethod",
            msg,
            [
                {"text": "Cash", "value": "Cash"},
                {"text": "Carte bancaire" if fr else "Credit Card",
                 "value": "Carte" if fr else "Card"},
            ]
        )

    # ── Mettre à jour le slot normalisé ──────────────────────────
    event["sessionState"]["intent"]["slots"]["PaymentMethod"] = {
        "value": {
            "interpretedValue": payment_method,
            "originalValue": payment_method
        }
    }

    # ── ÉTAPE 5 : Carte → numéro + CVV ───────────────────────────
    if payment_method == "Card":

        if not card_number:
            msg = "Veuillez entrer votre numéro de carte bancaire :" if fr \
                  else "Please enter your credit card number:"
            return elicit_slot(event, "CardNumber", msg)

        # ── Validation carte avec comptage des tentatives ─────────
        card_result = call_microservice("order", {
            "action": "validate_card",
            "card_number": card_number
        })

        if not card_result.get("valid"):

            # ── Incrémenter les tentatives ────────────────────────
            card_attempts = int(
                session_attrs.get("card_attempts", 0)
            ) + 1
            session_attrs["card_attempts"] = str(card_attempts)

            # ── Blocage après MAX tentatives ──────────────────────
            if card_attempts >= MAX_CARD_ATTEMPTS:
                session_attrs["card_attempts"] = "0"

                msg = (
                    "🔒 Votre accès est bloqué pour des raisons de sécurité.\n"
                    "Vous avez effectué 3 tentatives incorrectes.\n"
                    "Que souhaitez-vous faire ?"
                ) if fr else (
                    "🔒 Your access has been blocked for security reasons.\n"
                    "You have made 3 incorrect attempts.\n"
                    "What would you like to do?"
                )

                buttons = [
                    {"text": "🛒 Order a product",
                     "value": "I want to order a product"},
                    {"text": "🔧 Report a problem",
                     "value": "I want to report a problem"},
                    {"text": "📦 Check an order",
                     "value": "I want to check my order"},
                    {"text": "❌ Cancel an order",
                     "value": "I want to cancel my order"},
                ] if not fr else [
                    {"text": "🛒 Commander",
                     "value": "Je veux commander un produit"},
                    {"text": "🔧 Signaler une panne",
                     "value": "Je veux signaler un problème"},
                    {"text": "📦 Vérifier commande",
                     "value": "Je veux vérifier ma commande"},
                    {"text": "❌ Annuler commande",
                     "value": "Je veux annuler ma commande"},
                ]

                return _close_with_buttons(
                    event, msg, buttons, session_attrs
                )

            # ── Redemander le numéro de carte ─────────────────────
            remaining = MAX_CARD_ATTEMPTS - card_attempts
            msg = (
                f"❌ Numéro de carte invalide.\n"
                f"Il vous reste {remaining} tentative(s).\n"
                f"Veuillez entrer votre numéro de carte :"
            ) if fr else (
                f"❌ Invalid card number.\n"
                f"You have {remaining} attempt(s) remaining.\n"
                f"Please enter your credit card number:"
            )

            return _elicit_slot_with_session(
                event, "CardNumber", msg, session_attrs
            )

        # ── Carte valide : réinitialiser les tentatives ───────────
        session_attrs["card_attempts"] = "0"

        if not card_cvv:
            card_type = get_card_type(card_number)
            msg = f"Carte {card_type} détectée. Code CVV/CVC :" if fr \
                  else f"{card_type} detected. Enter CVV/CVC:"
            return elicit_slot(event, "CardCVV", msg)

    # ── ÉTAPE 6 : Confirmation ────────────────────────────────────
    if confirmation_state == "Denied":
        msg = "Commande annulée. À bientôt !" if fr \
              else "Order cancelled. See you soon!"
        return close(event, msg, fulfilled=False)

    if confirmation_state == "Confirmed":
        return _save_order(event, product_ref, payment_method,
                           card_number, card_cvv, fr, session_attrs)

    if confirmation_state == "None":
        if fr:
            msg = (f"📋 Récapitulatif de votre commande :\n"
                   f"- Produit : {product_ref}\n"
                   f"- Paiement : {payment_method}\n"
                   f"Confirmez-vous ?")
        else:
            msg = (f"📋 Order summary:\n"
                   f"- Product: {product_ref}\n"
                   f"- Payment: {payment_method}\n"
                   f"Do you confirm?")

        return {
            "sessionState": {
                "sessionAttributes": session_attrs,
                "dialogAction": {"type": "ConfirmIntent"},
                "intent": {
                    "name": event["sessionState"]["intent"]["name"],
                    "slots": event["sessionState"]["intent"]["slots"],
                    "state": "InProgress"
                }
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": msg
                },
                {
                    "contentType": "ImageResponseCard",
                    "imageResponseCard": {
                        "title": "Confirmation",
                        "buttons": [
                            {"text": "Oui ✅" if fr else "Yes ✅",
                             "value": "yes"},
                            {"text": "Non ❌" if fr else "No ❌",
                             "value": "no"}
                        ]
                    }
                }
            ]
        }

    return delegate(event)


def _save_order(event, product_ref, payment_method,
                card_number, card_cvv, fr, session_attrs):
    """Enregistre la commande via le microservice."""
    try:
        result = call_microservice("order", {
            "action":         "save_order",
            "product_ref":    product_ref,
            "payment_method": payment_method,
            "card_number":    card_number or None,
            "card_cvv":       card_cvv or None,
        })
        order_id = result.get("order_id")    #enregistrer dans DynamoDB

        # ── Réinitialiser les tentatives ──────────────────────────
        session_attrs["card_attempts"] = "0"

        msg = f"✅ Commande confirmée ! Numéro : {order_id}. Merci de choisir HP !" if fr \
              else f"✅ Order confirmed! ID: {order_id}. Thank you for choosing HP!"

        return close(event, msg)

    except Exception as e:
        logger.error(f"Erreur save_order: {e}")
        msg = "Erreur lors de l'enregistrement. Veuillez réessayer." if fr \
              else "Error while placing order. Please try again."
        return close(event, msg, fulfilled=False)


# ── Helpers avec session attributes ──────────────────────────────

def _elicit_slot_with_session(event, slot_name, message, session_attrs):
    """ElicitSlot en réinitialisant le slot et gardant les session attrs."""
    intent = event["sessionState"]["intent"]
    slots = intent.get("slots", {})

    # ── Réinitialiser le slot CardNumber ─────────────────────────
    slots["CardNumber"] = None
    intent["slots"] = slots
    intent["state"] = "InProgress"

    return {
        "sessionState": {
            "dialogAction": {
                "type": "ElicitSlot",
                "slotToElicit": slot_name,
            },
            "intent": intent,
            "sessionAttributes": session_attrs,
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


def _close_with_buttons(event, message, buttons, session_attrs):
    """Close avec boutons de menu pour sécurité."""
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {
                **event["sessionState"]["intent"],
                "state": "Failed",
            },
            "sessionAttributes": session_attrs,
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message
            },
            {
                "contentType": "ImageResponseCard",
                "imageResponseCard": {
                    "title": "Main menu",
                    "buttons": buttons,
                },
            }
        ],
    }
