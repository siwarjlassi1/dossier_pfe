import json
import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_client = boto3.client(
    "bedrock-agent-runtime",
    region_name="us-east-1"   # ← KB est dans us-east-1
)

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
MODEL_ARN = os.environ.get(
    "BEDROCK_MODEL_ARN",
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
)


def get_depannage_response(user_message: str) -> str:
    """Interroge Bedrock Knowledge Base et retourne une réponse."""
    try:
        response = bedrock_client.retrieve_and_generate(
            input={"text": user_message},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": KNOWLEDGE_BASE_ID,
                    "modelArn": MODEL_ARN,
                },
            },
        )
        return response["output"]["text"]
    except Exception as e:
        logger.error(f"Erreur Bedrock KB : {e}")
        return "Je suis désolé, je ne peux pas accéder à la base de connaissances pour le moment."


def close(intent_name: str, message: str) -> dict:
    """Retourne une réponse de fermeture à Lex."""
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {
                "name": intent_name,
                "state": "Fulfilled",
            },
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message,
            }
        ],
    }


def handle_demander_depannage(event: dict) -> dict:
    """Handler principal pour l'intention DemanderDepannage."""
    logger.info(f"DemanderDepannage event : {json.dumps(event)}")

    intent_name = event["sessionState"]["intent"]["name"]

    # Récupérer le message de l'utilisateur
    user_message = event.get("inputTranscript", "")

    if not user_message:
        user_message = "J'ai besoin d'aide pour dépanner mon produit HP"

    logger.info(f"Message utilisateur : {user_message}")

    # Interroger Bedrock KB
    response_text = get_depannage_response(user_message)

    logger.info(f"Réponse Bedrock : {response_text}")

    return close(intent_name, response_text)
