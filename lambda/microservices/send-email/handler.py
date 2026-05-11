#Le microservice de notification qui envoie un email de confirmation au client
import json
import logging
import os
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SENDER_EMAIL     = os.environ["SENDER_EMAIL"]
SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]


def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        action = body.get("action")

        if action == "send_confirmation":
            return send_confirmation(body)
        else:
            return _response(400, {"error": f"Unknown action: {action}"})

    except Exception as e:
        logger.exception("Error in send-email microservice")
        return _response(500, {"error": str(e)})


def send_confirmation(body):
    """Envoie un email de confirmation après création d'une réclamation."""

    recipient    = body.get("email")
    complaint_id = body.get("complaint_id")
    product_ref  = body.get("product_ref")
    problem      = body.get("problem_description")
    language     = body.get("language", "en")

    if not recipient:
        return _response(400, {"error": "Missing email"})

    if language == "fr":
        subject = "✅ Votre réclamation a bien été enregistrée"
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #e87722;">📋 Confirmation de réclamation</h2>
            <p>Bonjour,</p>
            <p>Votre réclamation a bien été enregistrée. Voici le récapitulatif :</p>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><b>🔖 Numéro</b></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{complaint_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><b>💻 Produit</b></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{product_ref}</td>
                </tr>
                <tr style="background-color: #f2f2f2;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><b>🔧 Problème</b></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{problem}</td>
                </tr>
            </table>
            <br>
            <p>Vous pouvez suivre votre réclamation en utilisant votre numéro.</p>
            <p style="color: #888;">HP Support</p>
        </body>
        </html>
        """
    else:
        subject = "✅ Your claim has been registered"
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #e87722;">📋 Claim Confirmation</h2>
            <p>Hello,</p>
            <p>Your claim has been successfully registered. Here is a summary:</p>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><b>🔖 Claim ID</b></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{complaint_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><b>💻 Product</b></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{product_ref}</td>
                </tr>
                <tr style="background-color: #f2f2f2;">
                    <td style="padding: 8px; border: 1px solid #ddd;"><b>🔧 Problem</b></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{problem}</td>
                </tr>
            </table>
            <br>
            <p>You can track your claim using your claim ID.</p>
            <p style="color: #888;">HP Support</p>
        </body>
        </html>
        """

    # ✅ Envoi via SendGrid API (sans dépendances)
    _send_via_sendgrid(recipient, subject, html_body)

    logger.info(f"Email sent to {recipient} for complaint {complaint_id}")
    return _response(200, {"sent": True})


def _send_via_sendgrid(to_email, subject, html_body):
    """Appel direct à l'API SendGrid sans librairie externe."""
    payload = json.dumps({
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": SENDER_EMAIL},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}]
    }).encode("utf-8")

    req = urllib.request.Request(
        #Appel API SendGrid
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type":  "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        logger.info(f"SendGrid response status: {resp.status}")


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
