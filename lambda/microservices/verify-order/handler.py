#Le microservice de vérification et suivi des commandes
import json
import logging
import boto3
import os
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ["ORDERS_TABLE"])


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        action = body.get("action")

        # ── Action : Vérifier une commande ────────────────────────
        if action == "check_order":
            order_id = body.get("order_id", "").strip()

            response = orders_table.query(   #chercher la commande
                KeyConditionExpression="orderId = :oid",
                ExpressionAttributeValues={":oid": str(order_id)}
            )
            items = response.get("Items")

            if not items:
                return _response(200, {"found": False})

            order = items[0]
            return _response(200, {
                "found":          True,
                "status":         order.get("status", "UNKNOWN"),
                "product_ref":    order.get("productRef", "N/A"),
                "payment_method": order.get("paymentMethod", "N/A"),
                "created_at":     str(order.get("createdAt", "N/A"))[:10],
            })

        else:
            return _response(400, {"error": f"Unknown action: {action}"})

    except Exception as e:
        logger.exception("Erreur microservice verify-order")
        return _response(500, {"error": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder)
    }