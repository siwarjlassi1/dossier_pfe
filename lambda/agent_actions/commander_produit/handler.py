import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_URL = os.environ.get("API_GATEWAY_URL", "")
ACTION_GROUP = "CommanderProduit"
FUNCTION_NAME = "commander_produit"


def call_microservice(path, payload):
    url = f"{API_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.error(f"HTTPError {e.code} sur {url}: {e.read()}")
        raise
    except Exception as e:
        logger.error(f"Erreur appel microservice {url}: {e}")
        raise


def get_param(parameters, name):
    for p in parameters:
        if p["name"] == name:
            return p["value"]
    return None


def handler(event, context):
    logger.info(f"Event reçu : {json.dumps(event)}")

    parameters = event.get("parameters", [])
    modele = get_param(parameters, "modele")
    quantite = get_param(parameters, "quantite")

    if not quantite:
        quantite = "1"

    if not modele:
        return build_response(
            success=False,
            message="Informations manquantes : modèle du produit requis."
        )

    try:
        result = call_microservice("order", {
            "action": "save_order",
            "product_ref": modele.lower().replace(" ", "-"),
            "payment_method": "chatbot",
            "card_number": None,
            "card_cvv": None,
        })

        logger.info(f"Résultat commande : {result}")

        if result.get("success"):
            order_id = result.get("order_id", "N/A")
            return build_response(
                success=True,
                message=(
                    f"Commande créée avec succès ! "
                    f"Votre numéro de commande est : {order_id}. "
                    f"Produit : {modele} | Quantité : {quantite}."
                )
            )
        else:
            return build_response(
                success=False,
                message="La commande n'a pas pu être créée. Veuillez réessayer."
            )

    except Exception as e:
        logger.error(f"Erreur lors de la commande : {e}")
        return build_response(
            success=False,
            message="Une erreur est survenue lors de la création de votre commande."
        )


def build_response(success: bool, message: str) -> dict:
    return {
        "messageVersion": "1.0",                    # ← Ajout
        "response": {
            "actionGroup": ACTION_GROUP,
            "function": FUNCTION_NAME,
            "functionResponse": {
                "responseState": (                   # ← Ajout
                    "FULFILLMENT" if success else "REPROMPT"
                ),
                "responseBody": {
                    "TEXT": {"body": message}
                }
            }
        }
    }
