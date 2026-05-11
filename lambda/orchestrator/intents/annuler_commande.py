import logging
from .utils import get_slot, elicit_slot, close, delegate, is_french

logger = logging.getLogger()
logger.setLevel(logging.INFO)

call_microservice = None


def handle_annuler_commande(event):
    fr = is_french(event)

    order_id = get_slot(event, "OrderId")
    if order_id:
        order_id = order_id.strip()

    session_attrs = event.get("sessionState", {}).get("sessionAttributes", {}) or {}

    # ← confirmationState natif Lex
    confirmation_state = event.get("sessionState", {}) \
                              .get("intent", {}) \
                              .get("confirmationState", "None")

    # ── ÉTAPE 1 : Demander OrderId ────────────────────────────────
    if not order_id:
        msg = "Veuillez entrer le numéro de commande à annuler :" if fr \
              else "Please enter the order ID you want to cancel:"
        return elicit_slot(event, "OrderId", msg)

    # ── ÉTAPE 2 : Vérifier que la commande existe ─────────────────
    result = call_microservice("verify-order", {
        "action":   "check_order",
        "order_id": order_id,
    })

    if not result.get("found"):
        msg = (f"Aucune commande trouvée avec le numéro '{order_id}'. "
               f"Veuillez vérifier votre numéro.") if fr else \
              (f"No order found with ID '{order_id}'. "
               f"Please check your order ID.")
        return elicit_slot(event, "OrderId", msg)

    # ── ÉTAPE 3 : Vérifier le statut ─────────────────────────────
    status = result.get("status", "")

    if status == "CANCELLED":
        msg = f"La commande '{order_id}' est déjà annulée." if fr \
              else f"Order '{order_id}' is already cancelled."
        return close(event, msg, fulfilled=False)

    if status in ["SHIPPED", "DELIVERED"]:
        status_labels_fr = {"SHIPPED": "Expédiée", "DELIVERED": "Livrée"}
        status_label = status_labels_fr.get(status, status) if fr else status
        msg = (f"La commande '{order_id}' ne peut pas être annulée "
               f"car elle est déjà : {status_label}.") if fr else \
              (f"Order '{order_id}' cannot be cancelled "
               f"because it is already: {status_label}.")
        return close(event, msg, fulfilled=False)

    # ── ÉTAPE 4 : Confirmation ────────────────────────────────────
    product_ref = result.get("product_ref", "N/A")
    payment     = result.get("payment_method", "N/A")

    if confirmation_state == "Denied":
        msg = "Annulation abandonnée. Votre commande reste inchangée." if fr \
              else "Cancellation aborted. Your order remains unchanged."
        return close(event, msg, fulfilled=False)

    if confirmation_state == "Confirmed":
        return _cancel_order(event, order_id, fr)

    # ← Envoyer ConfirmIntent si None
    if confirmation_state == "None":
        if fr:
            msg = (f"⚠️ Voulez-vous vraiment annuler cette commande ?\n"
                   f"- Numéro : {order_id}\n"
                   f"- Produit : {product_ref}\n"
                   f"- Paiement : {payment}\n"
                   f"Cette action est irréversible.")
        else:
            msg = (f"⚠️ Are you sure you want to cancel this order?\n"
                   f"- Order ID: {order_id}\n"
                   f"- Product: {product_ref}\n"
                   f"- Payment: {payment}\n"
                   f"This action cannot be undone.")

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
                            {"text": "Oui ✅" if fr else "Yes ✅", "value": "yes"},
                            {"text": "Non ❌" if fr else "No ❌",  "value": "no"}
                        ]
                    }
                }
            ]
        }

    return delegate(event)


def _cancel_order(event, order_id, fr):
    try:
        result = call_microservice("order", {
            "action":   "cancel_order",
            "order_id": order_id,
        })

        if not result.get("success"):
            msg = "Erreur lors de l'annulation. Veuillez réessayer." if fr \
                  else "Error while cancelling. Please try again."
            return close(event, msg, fulfilled=False)

        msg = (f"✅ Commande '{order_id}' annulée avec succès. "
               f"Un remboursement sera effectué sous 5-7 jours ouvrés.") if fr else \
              (f"✅ Order '{order_id}' successfully cancelled. "
               f"A refund will be processed within 5-7 business days.")

        return close(event, msg)

    except Exception as e:
        logger.exception("Erreur annulation commande")
        msg = "Désolé, une erreur est survenue. Veuillez réessayer." if fr \
              else "Sorry, an error occurred. Please try again."
        return close(event, msg, fulfilled=False)
