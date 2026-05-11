#Le microservice de consultation et suivi des réclamations
import json
import logging
import boto3
import os
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb         = boto3.resource("dynamodb")
complaints_table = dynamodb.Table(os.environ["COMPLAINTS_TABLE"])


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def handler(event, context):
    try:
        body   = json.loads(event.get("body", "{}"))
        action = body.get("action")

        # ── Action : Suivre une réclamation ───────────────────────
        if action == "check_reclamation":
            reclamation_id = body.get("reclamation_id", "").strip()

            if not reclamation_id:
                return _response(400, {"error": "reclamation_id manquant."})

            response = complaints_table.query(
                KeyConditionExpression="complaintId = :cid",
                ExpressionAttributeValues={":cid": str(reclamation_id)}
            )
            items = response.get("Items", [])

            if not items:
                return _response(200, {"found": False})

            complaint = items[0]
            return _response(200, {
                "found":               True,
                "complaint_id":        complaint.get("complaintId", "N/A"),
                "status":              complaint.get("status", "UNKNOWN"),
                "product_ref":         complaint.get("productRef", "N/A"),
                "problem_description": complaint.get("description", "N/A"),
                "solution":            complaint.get("solution", "N/A"),
                "sentiment":           complaint.get("sentiment", "N/A"),
                "under_warranty":      complaint.get("underWarranty", False),
                "created_at":          str(complaint.get("createdAt", "N/A"))[:10],
            })

        # ── Action : Lister toutes les réclamations ───────────────
        elif action == "list_complaints":
            response = complaints_table.scan()
            items    = response.get("Items", [])

            # ── Pagination DynamoDB ───────────────────────────────
            while "LastEvaluatedKey" in response:
                response = complaints_table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items.extend(response.get("Items", []))

            complaints = [
                {
                    "complaint_id":        c.get("complaintId", "N/A"),
                    "status":              c.get("status", "UNKNOWN"),
                    "product_ref":         c.get("productRef", "N/A"),
                    "description":         c.get("description", "N/A"),
                    "solution":            c.get("solution", "N/A"),
                    "sentiment":           c.get("sentiment", "N/A"),
                    "under_warranty":      c.get("underWarranty", False),
                    "created_at":          str(c.get("createdAt", "N/A")),
                }
                for c in items
            ]

            # ── Tri par date décroissante ─────────────────────────
            complaints.sort(
                key=lambda x: x["created_at"],
                reverse=True
            )

            return _response(200, {
                "found":      True,
                "total":      len(complaints),
                "complaints": complaints,
            })

        else:
            return _response(400, {"error": f"Action inconnue : {action}"})

    except Exception as e:
        logger.exception("Erreur dans track-claim")
        return _response(500, {"error": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",   #React d’appeler l’API
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }
