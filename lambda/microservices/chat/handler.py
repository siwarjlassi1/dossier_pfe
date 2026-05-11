#Le point d’entrée principal des messages utilisateur (frontend → IA)
import json
import boto3
import os
import uuid
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
#communiquer avec mon bot Lex
lex_client = boto3.client("lexv2-runtime", region_name="us-east-1")

BOT_ID       = os.environ.get("LEX_BOT_ID", "")
BOT_ALIAS_ID = os.environ.get("LEX_BOT_ALIAS_ID", "")
LOCALE_ID    = os.environ.get("LEX_LOCALE_ID", "fr_FR")

def handler(event, context):
    logger.info(f"Event reçu : {json.dumps(event)}")

    body = json.loads(event.get("body", "{}"))
    user_message = body.get("message", "")  #reception du msg du user 
    session_id   = body.get("sessionId", str(uuid.uuid4()))  #reception de la session pour le contexte et la memoire
    locale       = body.get("locale", LOCALE_ID)

    if not user_message:
        return {
            "statusCode": 400,
            "headers": cors_headers(),
            "body": json.dumps({"message": "Message vide."})
        }

    try:
        response = lex_client.recognize_text(   #appel a lex
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=locale,
            sessionId=session_id,
            text=user_message,
        )

        logger.info(f"Réponse Lex : {json.dumps(response, default=str)}")

        messages = response.get("messages", [])
        if messages:
            reply = " ".join([m.get("content", "") for m in messages])
        else:
            reply = "Je n'ai pas compris. Pouvez-vous reformuler ?"

        # ── Récupère le sessionId retourné par Lex ────────────────
        lex_session_id = response.get("sessionId", session_id)  #pour garder la continuité

        #React affiche réponse
        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps({
                "message": reply,
                "sessionId": lex_session_id  # ← renvoie le même sessionId à React
            })
        }

    except Exception as e:
        logger.error(f"Erreur Lex : {e}")
        return {
            "statusCode": 500,
            "headers": cors_headers(),
            "body": json.dumps({"message": "❌ Service indisponible."})
        }

def cors_headers():  #frontend
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }
