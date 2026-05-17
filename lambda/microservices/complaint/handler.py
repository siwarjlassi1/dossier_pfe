#Le microservice backend responsable de la gestion des réclamations
import uuid
import json
import logging
import boto3
import os
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
dynamodb         = boto3.resource("dynamodb")
complaints_table = dynamodb.Table(os.environ["COMPLAINTS_TABLE"])
products_table   = dynamodb.Table(os.environ["PRODUCTS_TABLE"])


def get_product(product_ref):
    try:
        response = products_table.get_item(Key={"productId": product_ref})
        return response.get("Item")
    except Exception as e:
        logger.error(f"get_product error: {e}")
        return None


def handler(event, context):
    try:
        body   = json.loads(event.get("body", "{}"))
        action = body.get("action")  #decide apres quoi faire

        # ── Action 1 : Valider la référence produit ───────────────
        if action == "validate_product":
            product_ref = body.get("product_ref", "").strip().lower()
            product = get_product(product_ref)
            if product:
                return _response(200, {"valid": True, "product": product})
            else:
                return _response(200, {"valid": False})

        # ── Action 2 : Enregistrer la réclamation ─────────────────
        elif action == "save_complaint":
            product_ref    = body.get("product_ref")
            customer_name  = body.get("customer_name")
            description    = body.get("description")
            under_warranty = body.get("under_warranty", False)
            ai_analysis    = body.get("ai_analysis", {})

            complaint_id = str(uuid.uuid4())
            created_at   = datetime.utcnow().isoformat()

            item = {
                "complaintId":    complaint_id,
                "createdAt":      created_at,
                "productRef":     product_ref,
                "customerName":   customer_name,
                "description":    description,
                "underWarranty":  under_warranty,
                "status":         "OPEN",

                 # ── IA Analysis ─────────────────────────────
                "solution":       ai_analysis.get("solution", ""),
                "sentiment":      ai_analysis.get("sentiment", "UNKNOWN"),

                # ✅ ML Classification
                "problemCategory": ai_analysis.get("problem_category", "unknown"),

                "sentimentScore": {
                    "positive": str(ai_analysis.get("sentiment_score", {}).get("Positive", 0)),
                    "negative": str(ai_analysis.get("sentiment_score", {}).get("Negative", 0)),
                    "neutral":  str(ai_analysis.get("sentiment_score", {}).get("Neutral", 0)),
                    "mixed":    str(ai_analysis.get("sentiment_score", {}).get("Mixed", 0)),
                    }
                    }

            complaints_table.put_item(Item=item)
            logger.info(f"Réclamation enregistrée : {complaint_id}")
            logger.info(f"Sentiment : {ai_analysis.get('sentiment', 'UNKNOWN')}")

            return _response(200, {
                "success":      True,
                "complaint_id": complaint_id
            })

        else:
            return _response(400, {"error": f"Unknown action: {action}"})

    except Exception as e:
        logger.exception("Erreur microservice complaint")
        return _response(500, {"error": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder)
    }
