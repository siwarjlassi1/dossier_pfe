import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_URL = os.environ.get("API_GATEWAY_URL", "")
ACTION_GROUP = "ReclamerPanne"
FUNCTION_NAME = "reclamer_panne"


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
    probleme = get_param(parameters, "probleme")

    if not modele or not probleme:
        return build_response(
            success=False,
            message="Informations manquantes : modèle et description du problème requis."
        )

    try:
        result = call_microservice("complaint", {
            "action": "save_complaint",
            "product_ref": modele.lower().replace(" ", "-"),
            "description": probleme,
            "customer_name": "Client HP",
            "under_warranty": False,
        })

        logger.info(f"Résultat réclamation : {result}")

        if result.get("success"):
            complaint_id = result.get("complaint_id", "N/A")
            return build_response(
                success=True,
                message=(
                    f"Réclamation enregistrée avec succès ! "
                    f"Votre numéro de réclamation est : {complaint_id}. "
                    f"Notre équipe va traiter votre problème "
                    f"avec le produit {modele} dans les plus brefs délais."
                )
            )
        else:
            return build_response(
                success=False,
                message="La réclamation n'a pas pu être enregistrée. Veuillez réessayer."
            )

    except Exception as e:
        logger.error(f"Erreur lors de la réclamation : {e}")
        return build_response(
            success=False,
            message="Une erreur est survenue lors de l'enregistrement de votre réclamation."
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
