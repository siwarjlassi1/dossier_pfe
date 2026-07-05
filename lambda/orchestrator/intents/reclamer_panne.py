# lambda/orchestrator/intents/reclamer_panne.py

import logging
import boto3
import requests
import json
from .utils import (
    get_slot, elicit_slot, elicit_slot_with_buttons,
    close, delegate, is_french
)
from model_normalizer import normalize_product_ref
from .bedrock_agent import invoke_agent, get_session_id

comprehend = boto3.client("comprehend", region_name="us-east-1")
lambda_client = boto3.client('lambda')

logger = logging.getLogger()

# Variable globale pour appeler les microservices
call_microservice = None


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


def predict_problem_category(text: str) -> str:
    """Prédit la catégorie du problème via ML API."""
    try:
        response = requests.post(
            "http://52.205.197.203:5000/predict",
            json={"text": text},
            timeout=10
        )
        prediction = response.json()["prediction"]
        logger.info(f"ML prediction: {prediction}")
        return prediction
    except Exception as e:
        logger.error(f"ML API error: {e}")
        return "unknown"


def handle_reclamer_panne(event):
    """
    Point d'entrée principal pour l'intent ReclamarPanne
    """
    fr = is_french(event)

    product_type   = get_slot(event, "ProductType")
    product_ref    = get_slot(event, "ProductReference")
    under_warranty = get_slot(event, "UnderWarranty")
    problem_desc   = get_slot(event, "ProblemDescription")
    customer_email = get_slot(event, "CustomerEmail")

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

    # ── Validation email ──────────────────────────────────────────
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
    """
    Sauvegarde la réclamation et génère le résumé
    """
    
    session_id    = get_session_id(event)
    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    session_attrs["agent_session_id"] = session_id

    # ── Sentiment Analysis ────────────────────────────────────────
    sentiment_data = detect_sentiment(problem_desc)
    sentiment      = sentiment_data["sentiment"]
    problem_category = predict_problem_category(problem_desc)
    logger.info(f"Sentiment détecté : {sentiment_data}")

    # ── Agent Bedrock ─────────────────────────────────────────────
    try:
        agent_result = invoke_agent(problem_desc, product_ref, session_id, sentiment, fr)
        solution     = agent_result.get("solution", "")
        logger.info(f"Agent result: {agent_result}")
    except Exception as e:
        logger.error(f"Agent error: {e}")
        solution = ""

    # ── 🆕 GÉNÉRATION DU RÉSUMÉ (AVANT LA SAUVEGARDE) ─────────────
    conversation_summary = ""
    try:
        logger.info(f"🔍 DEBUG - product_ref: {product_ref}")
        logger.info(f"🔍 DEBUG - problem_desc: {problem_desc}")
        logger.info(f"🔍 DEBUG - solution: {solution[:100] if solution else 'VIDE'}")
        logger.info(f"🔍 DEBUG - under_warranty: {under_warranty}")
        logger.info(f"🔍 DEBUG - fr: {fr}")
        
        # Construire le dialogue
        dialogue = _build_conversation_dialogue(
            product_ref, problem_desc, solution, under_warranty, fr
        )
        
        logger.info(f"🔍 DEBUG - dialogue length: {len(dialogue)}")
        logger.info(f"📝 Dialogue construit:\n{dialogue}")
        
        logger.info("🔄 Génération du résumé de conversation...")
        
        # Appeler le microservice de résumé
        payload = {
            'dialogue': dialogue,
            'conversation_id': 'temp-id'  # ID temporaire
        }
        
        logger.info(f"🔍 DEBUG - Payload envoyé: {json.dumps(payload)[:200]}")
        
        response = lambda_client.invoke(
            FunctionName='hp-chatbot-summarize',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info(f"📥 Réponse Lambda summarize: {json.dumps(result)}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            if body.get('success'):
                conversation_summary = body['summary']
                logger.info(f"✅ Résumé généré: {conversation_summary}")
            else:
                logger.warning(f"⚠️ Summarize returned success=False: {body}")
        else:
            logger.warning(f"⚠️ Summarize returned status {result.get('statusCode')}")
        
    except Exception as e:
        logger.error(f"❌ Erreur génération résumé: {e}")
        import traceback
        traceback.print_exc()
        conversation_summary = ""

    # ── 🆕 SAUVEGARDE AVEC RÉSUMÉ (APRÈS LA GÉNÉRATION) ───────────
    try:
        save_result = call_microservice("complaint", {
            "action":         "save_complaint",
            "product_ref":    product_ref,
            "customer_name":  "LexUser",
            "description":    problem_desc,
            "under_warranty": under_warranty == "yes",
            "summary":        conversation_summary,  # 🆕 RÉSUMÉ
            "ai_analysis": {
                "solution":        solution,
                "sentiment":       sentiment_data["sentiment"],
                "sentiment_score": sentiment_data["sentiment_score"],
                "problem_category": problem_category,
            }
        })
        complaint_id = save_result.get("complaint_id", "N/A")
        logger.info(f"Complaint saved: {complaint_id}")
        logger.info(f"📝 Résumé sauvegardé: {conversation_summary[:100] if conversation_summary else 'VIDE'}")
    except Exception as e:
        logger.error(f"Save complaint error: {e}")
        complaint_id = "N/A"

    # ── Envoi Email avec résumé ───────────────────────────────────
    if customer_email and complaint_id != "N/A":
        try:
            email_payload = {
                "action":               "send_confirmation",
                "email":                customer_email,
                "complaint_id":         complaint_id,
                "product_ref":          product_ref,
                "problem_description":  problem_desc,
                "solution":             solution,
                "summary":              conversation_summary,
                "language":             "fr" if fr else "en"
            }
            
            logger.info(f"🔍 DEBUG - Email payload summary: {email_payload.get('summary', 'VIDE')}")
            
            call_microservice("send-email", email_payload)
            logger.info(f"📧 Email avec résumé envoyé à {customer_email}")
        except Exception as e:
            logger.error(f"Email error: {e}")

    # ── Réponse finale à Lex ──────────────────────────────────────
    if fr:
        msg = (
            f"✅ Réclamation confirmée ! Numéro : {complaint_id}.\n\n"
            f"📊 Catégorie détectée : {problem_category}\n\n"
            f"🤖 Solution proposée par notre IA :\n{solution}\n\n"
        )
        
        if conversation_summary:
            msg += f"📋 Résumé de votre conversation :\n{conversation_summary}\n\n"
        else:
            logger.warning("⚠️ Aucun résumé à afficher dans la réponse Lex")
        
        msg += (
            f"📧 Un email de confirmation avec le résumé complet a été envoyé à {customer_email}.\n\n"
            f"Notre équipe vous contactera sous 24h."
        )
    else:
        msg = (
            f"✅ Complaint confirmed! Number: {complaint_id}.\n\n"
            f"📊 Detected problem category: {problem_category}\n\n"
            f"🤖 AI proposed solution:\n{solution}\n\n"
        )
        
        if conversation_summary:
            msg += f"📋 Conversation summary:\n{conversation_summary}\n\n"
        else:
            logger.warning("⚠️ No summary to display in Lex response")
        
        msg += (
            f"📧 A confirmation email with the full summary has been sent to {customer_email}.\n\n"
            f"Our team will contact you within 24h."
        )

    return close(event, msg, fulfilled=True)




def _build_conversation_dialogue(product_ref, problem_desc, solution, under_warranty, fr):
    """
    Construit un dialogue formaté pour le résumeur
    """
    warranty_status = "sous garantie" if under_warranty == "yes" else "hors garantie"
    
    if fr:
        dialogue = f"""Client: Bonjour, j'ai un problème avec mon {product_ref}
Agent: Bonjour, je vais vous aider. Quel est le problème exactement ?
Client: {problem_desc}
Agent: Je comprends. Votre produit est-il sous garantie ?
Client: Oui, il est {warranty_status}
Agent: Très bien. Voici la solution : {solution if solution else "Notre équipe technique va vous contacter sous 24h"}
Client: Merci pour votre aide"""
    else:
        warranty_status = "under warranty" if under_warranty == "yes" else "out of warranty"
        dialogue = f"""Customer: Hello, I have a problem with my {product_ref}
Agent: Hello, I'll help you. What is the exact problem?
Customer: {problem_desc}
Agent: I understand. Is your product under warranty?
Customer: Yes, it is {warranty_status}
Agent: Very well. Here is the solution: {solution if solution else "Our technical team will contact you within 24h"}
Customer: Thank you for your help"""
    
    return dialogue

