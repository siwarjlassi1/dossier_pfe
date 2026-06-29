import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SENDER_EMAIL = os.environ["SENDER_EMAIL"]

# Client SES
ses_client = boto3.client('ses', region_name='us-east-1')


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

    # ✅ Envoi via Amazon SES
    try:
        _send_via_ses(recipient, subject, html_body)
        logger.info(f"✅ Email sent to {recipient} for complaint {complaint_id}")
        return _response(200, {"sent": True})
    except ClientError as e:
        logger.error(f"❌ SES error: {e.response['Error']['Message']}")
        return _response(500, {"error": f"Email sending failed: {e.response['Error']['Message']}"})


def _send_via_ses(to_email, subject, html_body):
    """Envoi via Amazon SES"""
    response = ses_client.send_email(
        Source=SENDER_EMAIL,
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': subject, 'Charset': 'UTF-8'},
            'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
        }
    )
    logger.info(f"📧 SES MessageId: {response['MessageId']}")
    return response


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }
