#La logique complète de gestion des réclamations clients avec IA
call_microservice = None
import logging
import boto3

from .utils import (
    get_slot, elicit_slot, elicit_slot_with_buttons,
    close, delegate, is_french
)
from model_normalizer import normalize_product_ref
from .bedrock_agent import invoke_agent, get_session_id

comprehend = boto3.client("comprehend", region_name="us-east-1")

logger = logging.getLogger()


def detect_sentiment(text: str) -> dict:
    """Détecte l'émotion du client via AWS Comprehend."""
    try:
        response = comprehend.detect_sentiment(
            Text=text,
            LanguageCode="fr"
        )
        return {
            "sentiment":       response["Sentiment"],
            "sentiment_score": response["SentimentScore"]
        }
    except Exception as e:
        logger.error(f"Comprehend error: {e}")
        return {"sentiment": "UNKNOWN", "sentiment_score": {}}


def handle_reclamer_panne(event):
    fr = is_french(event)

    product_type   = get_slot(event, "ProductType")
    product_ref    = get_slot(event, "ProductReference")
    under_warranty = get_slot(event, "UnderWarranty")
    problem_desc   = get_slot(event, "ProblemDescription")
    customer_email = get_slot(event, "CustomerEmail")  # 🆕

    session_attrs = event.get("sessionState", {}).get("sessionAttributes", {}) or {}

    confirmation_state = event.get("sessionState", {}) \
                              .get("intent", {}) \
                              .get("confirmationState", "None")

    # ── ÉTAPE 1 : Type de produit ─────────────────────────────────
    if not product_type:
        msg = "Quel type de produit a le problème ? (imprimante, ordinateur, tablette...)" if fr \
              else "What type of product has the problem? (printer, laptop, tablet...)"
        return elicit_slot(event, "ProductType", msg)

    # ── ÉTAPE 2 : Référence produit ───────────────────────────────
    if not product_ref:
        msg = f"Quelle est la référence de votre {product_type} ?" if fr \
              else f"What is the reference of your {product_type}?"
        return elicit_slot(event, "ProductReference", msg)

    # ── ÉTAPE 2.5 : Normalisation + Validation ────────────────────
    product_ref = normalize_product_ref(product_ref)
    event["sessionState"]["intent"]["slots"]["ProductReference"] = {
        "value": {"interpretedValue": product_ref, "originalValue": product_ref}
    }

    result = call_microservice("complaint", {
        "action": "validate_product",
        "product_ref": product_ref
    })
    if not result.get("valid"):
        msg = f"Désolé, '{product_ref}' est introuvable. (ex: m12, m26, elitebook840)" if fr \
              else f"Sorry, '{product_ref}' was not found. (e.g. m12, m26, elitebook840)"
        return elicit_slot(event, "ProductReference", msg)

    # ── ÉTAPE 3 : Sous garantie ? ─────────────────────────────────
    if not under_warranty:
        return elicit_slot_with_buttons(
            event, "UnderWarranty",
            "Votre produit est-il sous garantie ?" if fr else "Is your product under warranty?",
            [
                {"text": "Oui ✅" if fr else "Yes ✅", "value": "yes"},
                {"text": "Non ❌" if fr else "No ❌",  "value": "no"},
            ]
        )

    # ── ÉTAPE 4 : Description du problème ────────────────────────
    if not problem_desc:
        msg = "Veuillez décrire le problème :" if fr \
              else "Please describe the problem:"
        return elicit_slot(event, "ProblemDescription", msg)


    # ── ÉTAPE 4.5 : Email du client ───────────────────────────────
    if not customer_email:
        msg = "Quel est votre adresse email pour recevoir la confirmation ?" if fr \
            else "What is your email address to receive the confirmation?"
        return elicit_slot(event, "CustomerEmail", msg)

        # ── Validation email 🆕 ───────────────────────────────────────
    if "@" not in customer_email or "." not in customer_email:
        msg = "Adresse email invalide. Veuillez réessayer (ex: nom@gmail.com) :" if fr \
            else "Invalid email address. Please try again (e.g. name@gmail.com):"
        return elicit_slot(event, "CustomerEmail", msg)

    

    # ── ÉTAPE 5 : Confirmation ────────────────────────────────────
    if confirmation_state == "Denied":
        msg = "Réclamation annulée. À bientôt !" if fr \
              else "Complaint cancelled. See you soon!"
        return close(event, msg, fulfilled=False)

    if confirmation_state == "Confirmed":
        return _save_complaint(event, product_ref, under_warranty, problem_desc, customer_email, fr)

    if confirmation_state == "None":
        warranty_label = ("Oui" if under_warranty == "yes" else "Non") if fr \
                         else ("Yes" if under_warranty == "yes" else "No")

        if fr:
            msg = (f"📋 Récapitulatif de votre réclamation :\n"
                   f"- Produit : {product_ref}\n"
                   f"- Sous garantie : {warranty_label}\n"
                   f"- Problème : {problem_desc}\n"
                   f"- Email : {customer_email}\n"
                   f"Confirmez-vous ?")
        else:
            msg = (f"📋 Complaint summary:\n"
                   f"- Product: {product_ref}\n"
                   f"- Under warranty: {warranty_label}\n"
                   f"- Problem: {problem_desc}\n"
                   f"- Email: {customer_email}\n"
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
                            {"text": "Oui ✅" if fr else "Yes ✅", "value": "yes"},
                            {"text": "Non ❌" if fr else "No ❌",  "value": "no"}
                        ]
                    }
                }
            ]
        }

    return delegate(event)


def _save_complaint(event, product_ref, under_warranty, problem_desc, customer_email, fr):

    session_id    = get_session_id(event)
    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    session_attrs["agent_session_id"] = session_id

    # ── Sentiment Analysis AVANT invoke_agent ─────────────────────
    sentiment_data = detect_sentiment(problem_desc)
    sentiment      = sentiment_data["sentiment"]
    logger.info(f"Sentiment détecté : {sentiment_data}")

    # ── Agent Bedrock avec sentiment ──────────────────────────────
    try:
        agent_result = invoke_agent(problem_desc, product_ref, session_id, sentiment, fr)
        solution     = agent_result.get("solution", "")
        logger.info(f"Agent result: {agent_result}")
    except Exception as e:
        logger.error(f"Agent error: {e}")
        solution = ""

    # ── Sauvegarde via microservice ───────────────────────────────
    try:
        save_result = call_microservice("complaint", {
            "action":         "save_complaint",
            "product_ref":    product_ref,
            "customer_name":  "LexUser",
            "description":    problem_desc,
            "under_warranty": under_warranty == "yes",
            "ai_analysis": {
                "solution":        solution,
                "sentiment":       sentiment_data["sentiment"],
                "sentiment_score": sentiment_data["sentiment_score"],
            }
        })
        complaint_id = save_result.get("complaint_id", "N/A")
        logger.info(f"Complaint saved: {complaint_id}")
    except Exception as e:
        logger.error(f"Save complaint error: {e}")
        complaint_id = "N/A"

    # ── Envoi Email 🆕 ────────────────────────────────────────────
    if customer_email and complaint_id != "N/A":
        try:
            call_microservice("send-email", {
                "action":               "send_confirmation",
                "email":                customer_email,
                "complaint_id":         complaint_id,
                "product_ref":          product_ref,
                "problem_description":  problem_desc,
                "language":             "fr" if fr else "en"
            })
            logger.info(f"Email envoyé à {customer_email}")
        except Exception as e:
            logger.error(f"Email error: {e}")

    # ── Réponse finale à Lex ──────────────────────────────────────
    if fr:
        msg = (
            f"✅ Réclamation confirmée ! Numéro : {complaint_id}.\n\n"
            f"🤖 Solution proposée par notre IA :\n{solution}\n\n"
            f"📧 Un email de confirmation a été envoyé à {customer_email}.\n\n"
            f"Notre équipe vous contactera sous 24h."
        )
    else:
        msg = (
            f"✅ Complaint confirmed! Number: {complaint_id}.\n\n"
            f"🤖 AI proposed solution:\n{solution}\n\n"
            f"📧 A confirmation email has been sent to {customer_email}.\n\n"
            f"Our team will contact you within 24h."
        )

    return close(event, msg, fulfilled=True)
