# lambda/microservices/send-email/handler.py

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
    """Handler principal"""
    try:
        # Gérer les deux formats d'event (API Gateway et direct)
        if isinstance(event, str):
            event = json.loads(event)
        
        body = event if "action" in event else json.loads(event.get("body", "{}"))
        action = body.get("action")

        logger.info(f"📥 Action reçue: {action}")

        if action == "send_confirmation":
            return send_confirmation(body)
        else:
            return _response(400, {"error": f"Unknown action: {action}"})

    except Exception as e:
        logger.exception("❌ Error in send-email microservice")
        return _response(500, {"error": str(e)})


def send_confirmation(body):
    """Envoie un email de confirmation après création d'une réclamation."""

    recipient    = body.get("email")
    complaint_id = body.get("complaint_id")
    product_ref  = body.get("product_ref")
    problem      = body.get("problem_description")
    solution     = body.get("solution", "")  # 🆕 Solution
    summary      = body.get("summary", "")   # 🆕 Résumé
    language     = body.get("language", "en")

    if not recipient:
        return _response(400, {"error": "Missing email"})

    logger.info(f"📧 Envoi email à {recipient} pour réclamation {complaint_id}")

    if language == "fr":
        subject = f"✅ Réclamation #{complaint_id} - Confirmation"
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #0096D6; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .info-table td {{ padding: 12px; border: 1px solid #ddd; }}
                .info-table tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .solution-box {{ background: #e8f4f8; border-left: 4px solid #0096D6; padding: 15px; margin: 20px 0; }}
                .summary-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🖨️ HP Support</h1>
                    <p>Confirmation de réclamation</p>
                </div>
                
                <div class="content">
                    <h2>Bonjour,</h2>
                    
                    <p>Votre réclamation a été enregistrée avec succès.</p>
                    
                    <table class="info-table">
                        <tr>
                            <td><b>🔖 Numéro de réclamation</b></td>
                            <td>{complaint_id}</td>
                        </tr>
                        <tr>
                            <td><b>💻 Produit</b></td>
                            <td>{product_ref}</td>
                        </tr>
                        <tr>
                            <td><b>🔧 Problème signalé</b></td>
                            <td>{problem}</td>
                        </tr>
                    </table>
                    
                    {f'''
                    <div class="solution-box">
                        <h3>🤖 Solution proposée par notre IA</h3>
                        <p>{solution}</p>
                    </div>
                    ''' if solution else ''}
                    
                    {f'''
                    <div class="summary-box">
                        <h3>📊 Résumé de votre conversation</h3>
                        <p>{summary}</p>
                    </div>
                    ''' if summary else ''}
                    
                    <p><strong>📞 Prochaines étapes :</strong></p>
                    <ul>
                        <li>Notre équipe technique vous contactera sous 24 heures</li>
                        <li>Vous pouvez suivre votre réclamation avec le numéro ci-dessus</li>
                        <li>Conservez ce numéro pour toute correspondance future</li>
                    </ul>
                    
                    <p>Cordialement,<br><strong>L'équipe HP Support</strong></p>
                </div>
                
                <div class="footer">
                    <p>© 2026 HP Inc. Tous droits réservés.</p>
                    <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        subject = f"✅ Claim #{complaint_id} - Confirmation"
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #0096D6; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .info-table td {{ padding: 12px; border: 1px solid #ddd; }}
                .info-table tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .solution-box {{ background: #e8f4f8; border-left: 4px solid #0096D6; padding: 15px; margin: 20px 0; }}
                .summary-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🖨️ HP Support</h1>
                    <p>Claim Confirmation</p>
                </div>
                
                <div class="content">
                    <h2>Hello,</h2>
                    
                    <p>Your claim has been successfully registered.</p>
                    
                    <table class="info-table">
                        <tr>
                            <td><b>🔖 Claim ID</b></td>
                            <td>{complaint_id}</td>
                        </tr>
                        <tr>
                            <td><b>💻 Product</b></td>
                            <td>{product_ref}</td>
                        </tr>
                        <tr>
                            <td><b>🔧 Reported Issue</b></td>
                            <td>{problem}</td>
                        </tr>
                    </table>
                    
                    {f'''
                    <div class="solution-box">
                        <h3>🤖 AI Proposed Solution</h3>
                        <p>{solution}</p>
                    </div>
                    ''' if solution else ''}
                    
                    {f'''
                    <div class="summary-box">
                        <h3>📊 Conversation Summary</h3>
                        <p>{summary}</p>
                    </div>
                    ''' if summary else ''}
                    
                    <p><strong>📞 Next Steps:</strong></p>
                    <ul>
                        <li>Our technical team will contact you within 24 hours</li>
                        <li>You can track your claim using the number above</li>
                        <li>Keep this number for future correspondence</li>
                    </ul>
                    
                    <p>Best regards,<br><strong>HP Support Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>© 2026 HP Inc. All rights reserved.</p>
                    <p>This email was sent automatically, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """

    # ✅ Envoi via Amazon SES
    try:
        _send_via_ses(recipient, subject, html_body)
        logger.info(f"✅ Email sent to {recipient} for complaint {complaint_id}")
        return _response(200, {"sent": True, "recipient": recipient})
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
