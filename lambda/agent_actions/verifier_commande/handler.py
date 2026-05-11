import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_URL = os.environ.get("API_GATEWAY_URL", "")
ACTION_GROUP = "VerifierCommande"
FUNCTION_NAME = "verifier_commande"


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
    order_id = get_param(parameters, "order_id")

    if not order_id:
        return build_response(
            success=False,
            message="Informations manquantes : numéro de commande requis."
        )

    try:
        result = call_microservice("verify-order", {
            "action": "check_order",
            "order_id": order_id,
        })

        logger.info(f"Résultat vérification : {result}")

        if result.get("found"):
            status = result.get("status", "N/A")
            product_ref = result.get("product_ref", "N/A")
            created_at = result.get("created_at", "N/A")
            return build_response(
                success=True,
                message=(
                    f"Commande {order_id} trouvée ! "
                    f"Produit : {product_ref} | "
                    f"Statut : {status} | "
                    f"Date : {created_at}."
                )
            )
        else:
            return build_response(
                success=False,
                message=f"Aucune commande trouvée avec le numéro {order_id}."
            )

    except Exception as e:
        logger.error(f"Erreur lors de la vérification : {e}")
        return build_response(
            success=False,
            message="Une erreur est survenue lors de la vérification de votre commande."
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
