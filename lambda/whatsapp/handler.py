import json
import boto3
import os
import urllib.request
import urllib.parse
import base64

# Clients AWS
lex_client = boto3.client("lexv2-runtime", region_name="us-east-1")
secrets_client = boto3.client("secretsmanager", region_name="us-east-1")

def get_twilio_credentials():
    """Récupère les credentials Twilio depuis Secrets Manager"""
    secret = secrets_client.get_secret_value(
        SecretId="twilio/credentials"
    )
    return json.loads(secret["SecretString"])

def detect_locale(message):
    """Détecte la langue du message"""
    french_words = [
        # Salutations
        "bonjour", "salut", "bonsoir", "coucou",
        # Pronoms
        "je", "tu", "nous", "vous", "ils",
        "mon", "ma", "mes", "ton", "ta", "votre",
        # Verbes courants
        "veux", "voudrais", "souhaite", "vouloir",
        "commander", "commande", "annuler", "vérifier",
        "signaler", "avoir", "faire", "aller",
        # Mots clés métier
        "produit", "ordinateur", "problème", "panne",
        "statut", "référence", "livraison", "aide",
        "merci", "oui", "non", "svp", "stp", "cash",
        "carte", "carte bancaire",
        # Articles
        "le", "la", "les", "un", "une", "des",
        "du", "de", "ce", "cette", "ces", "par"
    ]

    message_lower = message.lower()
    
    # ✅ Vérifier les mots entiers uniquement
    words = message_lower.split()
    for word in french_words:
        if word in words:
            return "fr_FR"
    return "en_US"


def send_whatsapp_message(to, body, account_sid, auth_token):
    """Envoie un message WhatsApp via Twilio"""
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        print(f"📤 Envoi vers : whatsapp:{to}")
        print(f"📤 Depuis : whatsapp:+14155238886")
        print(f"📤 Message : {body[:100]}...")  # Premiers 100 caractères

        data = urllib.parse.urlencode({
            "From": "whatsapp:+14155238886",
            "To": f"whatsapp:{to}",
            "Body": body
        }).encode("utf-8")

        credentials = base64.b64encode(
            f"{account_sid}:{auth_token}".encode("utf-8")
        ).decode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {credentials}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        print(f"📤 URL Twilio : {url}")

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"✅ Réponse Twilio complète : {json.dumps(result, indent=2)}")
            print(f"✅ Message SID : {result.get('sid')}")
            print(f"✅ Status : {result.get('status')}")
            return result
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Erreur HTTP Twilio : {e.code}")
        print(f"❌ Détails : {error_body}")
        raise
    except Exception as e:
        print(f"❌ Erreur générale Twilio : {str(e)}")
        import traceback
        traceback.print_exc()
        raise

    

def reset_lex_session(from_number, locale):
    """Réinitialise la session Lex"""
    try:
        lex_client.delete_session(
            botId=os.environ["LEX_BOT_ID"],
            botAliasId=os.environ["LEX_BOT_ALIAS_ID"],
            localeId=locale,
            sessionId=from_number.replace("+", "").replace(" ", "").strip()
        )
    except Exception:
        pass  # Session inexistante, pas grave


def handler(event, context):
    try:
        body = urllib.parse.parse_qs(
            urllib.parse.unquote_plus(event.get("body", ""))
        )

        user_message = body.get("Body", [""])[0]
        from_number = body.get("From", [""])[0].replace("whatsapp:", "").strip()

        print(f"📩 Message reçu de {from_number} : {user_message}")

        locale = detect_locale(user_message)
        print(f"🌍 Locale détectée : {locale}")

        # ✅ Reset si salutation
        GREETINGS = ["bonjour", "salut", "hello", "hi", "hey", "start"]
        if any(word in user_message.lower() for word in GREETINGS):
            print("🔄 Reset session Lex")
            reset_lex_session(from_number, locale)

        # Envoyer à Lex
        lex_response = lex_client.recognize_text(
            botId=os.environ["LEX_BOT_ID"],
            botAliasId=os.environ["LEX_BOT_ALIAS_ID"],
            localeId=locale,
            sessionId=from_number.replace("+", "").replace(" ", "").strip(),
            text=user_message
        )

        messages = lex_response.get("messages", [])
        print(f"📨 Messages Lex bruts : {messages}")

        if messages:
            first_message = messages[0]
            print(f"📨 Premier message : {first_message}")
            
            # ✅ Gérer ImageResponseCard
            if first_message.get("contentType") == "ImageResponseCard":
                card = first_message.get("imageResponseCard", {})
                title = card.get("title", "")
                subtitle = card.get("subtitle", "")
                buttons = card.get("buttons", [])
                
                # Construire le message texte avec les options
                reply = f"{title}\n\n{subtitle}\n\n"
                for i, btn in enumerate(buttons, 1):
                    reply += f"{i}. {btn['text']}\n"
            else:
                # Message texte simple
                reply = first_message.get("content", "Désolé, je n'ai pas compris.")
        else:
            reply = "Désolé, je n'ai pas compris. / Sorry, I didn't understand."

        print(f"🤖 Réponse finale : {reply}")

        # ✅ Envoyer le message WhatsApp
        creds = get_twilio_credentials()
        send_whatsapp_message(
            to=from_number,
            body=reply,
            account_sid=creds["TWILIO_ACCOUNT_SID"],
            auth_token=creds["TWILIO_AUTH_TOKEN"]
        )

        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

    except Exception as e:
        print(f"❌ Erreur globale : {str(e)}")
        import traceback
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
