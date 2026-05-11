#Ce fichier va contenir la logique de commander_produit.py mais adapté pour être appelé via HTTP depuis l'orchestrateur
#c'est Le BACKEND réel (microservice “order”)
# Le microservice qui exécute les actions métier liées aux commandes
import uuid
import json
import logging
import boto3
import os
import re
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
    
# ── DynamoDB ──────────────────────────────────────────────────────
#Connexion à DynamoDB
dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ["ORDERS_TABLE"])
products_table = dynamodb.Table(os.environ["PRODUCTS_TABLE"])


# ── Helpers ───────────────────────────────────────────────────────
def get_product(product_ref):
    try:
        response = products_table.get_item(Key={"productId": product_ref})  # ← productId
        return response.get("Item")
    except Exception as e:
        logger.error(f"get_product error: {e}")
        return None


def validate_card_number(number):
    clean = number.replace(" ", "").replace("-", "")
    if not clean.isdigit() or not (13 <= len(clean) <= 19):
        return False
    total = 0
    reverse = clean[::-1]
    for i, digit in enumerate(reverse):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def get_card_type(number):
    clean = number.replace(" ", "")
    if clean.startswith("4"):
        return "Visa"
    elif clean[:2] in ["51","52","53","54","55"] or 2221 <= int(clean[:4]) <= 2720:
        return "Mastercard"
    elif clean[:2] in ["34","37"]:
        return "American Express"
    return "Unknown"


def handler(event, context):
    """
    Point d'entrée HTTP appelé par l'orchestrateur via API Gateway.
    Reçoit un body JSON avec les données du slot et retourne
    la réponse à renvoyer au client.
    """
    try:
        # Parser le body
        #lecture de l'action pour savoir quoi faire
        body = json.loads(event.get("body", "{}"))
        action = body.get("action")  # "validate_product", "save_order"

        # ── Action 1 : Valider la référence produit ───────────────
        if action == "validate_product":
            product_ref = body.get("product_ref", "").strip().lower()
            product = get_product(product_ref)
            if product:
                return _response(200, {"valid": True, "product": product})
            else:
                return _response(200, {"valid": False})

        # ── Action 2 : Valider le numéro de carte ─────────────────
        elif action == "validate_card":
            card_number = body.get("card_number", "")
            valid = validate_card_number(card_number)   #j'ai utlisé Luhn algorithm
            card_type = get_card_type(card_number) if valid else None
            return _response(200, {
                "valid": valid,
                "card_type": card_type
            })

        # ── Action 3 : Enregistrer la commande ────────────────────
        elif action == "save_order":
            product_ref   = body.get("product_ref")
            payment_method = body.get("payment_method")
            card_number   = body.get("card_number")
            card_cvv      = body.get("card_cvv")

            order_id   = str(uuid.uuid4())  #créer ID
            created_at = datetime.utcnow().isoformat()  #creer date
            #creer l'objet
            item = {
                "orderId":        order_id,
                "createdAt":      created_at,
                "productRef":     product_ref,
                "paymentMethod":  payment_method,
                "status":         "PENDING",
            }
            if card_number:
                item["cardType"]  = get_card_type(card_number)
                item["cardLast4"] = card_number.replace(" ", "")[-4:]
            #sauvegarder
            orders_table.put_item(Item=item)
            logger.info(f"Commande enregistrée : {order_id}")

            return _response(200, {
                "success":  True,
                "order_id": order_id
            })
        elif action == "cancel_order":
            order_id = body.get("order_id", "").strip()

    # ← Query pour récupérer createdAt (sort key obligatoire)
            from boto3.dynamodb.conditions import Key
            response = orders_table.query(
                KeyConditionExpression=Key("orderId").eq(order_id)
                )
            items = response.get("Items", [])

            if not items:
                return _response(200, {"success": False, "error": "Order not found"})

            created_at = items[0]["createdAt"]

            # ← Update statut → CANCELLED
            orders_table.update_item(
                Key={
                    "orderId":   order_id,
                    "createdAt": created_at
                    },
                UpdateExpression="SET #s = :s",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "CANCELLED"}
                )

            return _response(200, {"success": True})

            


        else:
            return _response(400, {"error": f"Unknown action: {action}"})

    except Exception as e:
        logger.exception("Erreur microservice order")
        return _response(500, {"error": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body,cls=DecimalEncoder)
    }