import boto3
import json
import urllib.parse
import base64
import re
import os

lex_client = boto3.client("lexv2-runtime", region_name="us-east-1")
secretsmanager = boto3.client("secretsmanager", region_name="us-east-1")

# ✅ Récupérer les IDs depuis les variables d'environnement
LEX_BOT_ID = os.environ.get("LEX_BOT_ID")
LEX_BOT_ALIAS_ID = os.environ.get("LEX_BOT_ALIAS_ID")

# Stocker la langue par utilisateur (persiste entre les appels)
user_locales = {}


def detect_language(text, user_id):
    """
    Détecte la langue avec priorité FORTE à la langue précédente
    """
    # Si l'utilisateur a déjà une langue, on la garde SAUF si le texte contient des mots-clés clairs
    if user_id in user_locales:
        previous_locale = user_locales[user_id]
        
        # Si le texte est un UUID, un nombre, ou très court, on garde TOUJOURS la langue précédente
        if len(text) < 10 or re.match(r'^[a-f0-9\-]+$', text.lower()) or text.isdigit():
            print(f"🔄 Texte court/technique, on garde la langue : {previous_locale}")
            return previous_locale
    
    # Mots-clés français FORTS
    french_keywords = [
        'bonjour', 'merci', 'oui', 'non', 'je', 'veux', 'commander', 
        'produit', 'problème', 'panne', 'commande', 'réclamation',
        'suivre', 'annuler', 'vérifier', 'ordinateur', 'imprimante',
        'signaler', 'veuillez', 'choisir', 'service', 'espèces',
        'carte', 'crédit', 'tablette', 'portable'
    ]
    
    # Mots-clés anglais FORTS
    english_keywords = [
        'hello', 'hi', 'thank', 'yes', 'no', 'want', 'order', 
        'product', 'problem', 'issue', 'claim', 'track', 'cancel',
        'check', 'laptop', 'printer', 'report', 'please', 'choose',
        'service', 'cash', 'card', 'credit', 'tablet'
    ]
    
    text_lower = text.lower()
    
    # Compter les mots français et anglais
    french_count = sum(1 for word in french_keywords if word in text_lower)
    english_count = sum(1 for word in english_keywords if word in text_lower)
    
    # Si on a déjà une langue et qu'il n'y a pas de mot-clé fort dans l'autre langue, on garde
    if user_id in user_locales:
        previous_locale = user_locales[user_id]
        
        if previous_locale == "fr_FR" and english_count == 0:
            print(f"🔄 Pas de mot anglais détecté, on garde le français")
            return "fr_FR"
        
        if previous_locale == "en_US" and french_count == 0:
            print(f"🔄 Pas de mot français détecté, on garde l'anglais")
            return "en_US"
    
    # Sinon, on compare les scores
    if french_count > english_count:
        locale = "fr_FR"
    elif english_count > french_count:
        locale = "en_US"
    else:
        # Par défaut, garder la langue précédente ou français
        locale = user_locales.get(user_id, "fr_FR")
    
    # Sauvegarder la langue de l'utilisateur
    user_locales[user_id] = locale
    print(f"💾 Langue sauvegardée pour {user_id} : {locale}")
    
    return locale


def reset_session(user_id, locale="fr_FR"):
    """Reset la session Lex dans la bonne langue"""
    print(f"🔄 Reset session Lex en {locale}")
    try:
        # Reset dans les DEUX langues pour être sûr
        for loc in ["fr_FR", "en_US"]:
            try:
                lex_client.delete_session(
                    botId=LEX_BOT_ID,
                    botAliasId=LEX_BOT_ALIAS_ID,
                    localeId=loc,
                    sessionId=user_id
                )
                print(f"✅ Session {loc} supprimée")
            except Exception as e:
                print(f"⚠️ Pas de session {loc} à supprimer : {e}")
    except Exception as e:
        print(f"⚠️ Erreur lors du reset de session : {e}")
    
    # Sauvegarder la nouvelle langue
    user_locales[user_id] = locale
    print(f"💾 Langue réinitialisée à : {locale}")


def get_twilio_credentials():
    """Récupère les credentials Twilio depuis Secrets Manager"""
    try:
        response = secretsmanager.get_secret_value(SecretId="twilio/credentials")
        secret = json.loads(response["SecretString"])
        return secret
    except Exception as e:
        print(f"❌ Erreur récupération credentials Twilio : {e}")
        raise


def send_whatsapp_message(to, body, account_sid, auth_token):
    """Envoie un message WhatsApp via Twilio"""
    import http.client
    
    # Préparer les données
    params = urllib.parse.urlencode({
        "From": "whatsapp:+14155238886",
        "To": f"whatsapp:{to}",
        "Body": body
    })
    
    # Authentification Basic
    credentials = f"{account_sid}:{auth_token}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    # Envoi de la requête
    conn = http.client.HTTPSConnection("api.twilio.com")
    
    url = f"/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    print(f"📤 Envoi vers : whatsapp:{to}")
    print(f"📤 Depuis : whatsapp:+14155238886")
    print(f"📤 Message : {body[:100]}...")
    print(f"📤 URL Twilio : https://api.twilio.com{url}")
    
    conn.request("POST", url, params, headers)
    response = conn.getresponse()
    data = response.read().decode()
    
    print(f"✅ Réponse Twilio complète : {data}")
    
    response_json = json.loads(data)
    print(f"✅ Message SID : {response_json.get('sid')}")
    print(f"✅ Status : {response_json.get('status')}")
    
    conn.close()


def handler(event, context):
    try:
        # Parser le body
        body = urllib.parse.parse_qs(
            urllib.parse.unquote_plus(event.get("body", ""))
        )

        user_message = body.get("Body", [""])[0]
        from_number = body.get("From", [""])[0].replace("whatsapp:", "").strip()

        print(f"📩 Message reçu de {from_number} : {user_message}")

        # Détection de langue améliorée
        locale = detect_language(user_message, from_number)
        print(f"🌍 Locale détectée : {locale}")

        # Reset si "bonjour", "hello", "hi", "salut"
        reset_keywords = ["bonjour", "hello", "hi", "salut", "hey"]
        if any(user_message.lower().startswith(keyword) for keyword in reset_keywords):
            reset_session(from_number, locale)

        # Appel à Lex
        lex_response = lex_client.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_BOT_ALIAS_ID,
            localeId=locale,
            sessionId=from_number,
            text=user_message
        )

        # Extraire les messages
        messages = lex_response.get("messages", [])
        print(f"📨 Messages Lex bruts : {messages}")

        if not messages:
            final_response = "Désolé, je n'ai pas compris." if locale == "fr_FR" else "Sorry, I didn't understand."
        else:
            first_message = messages[0]
            print(f"📨 Premier message : {first_message}")

            # Gérer les différents types de messages
            if first_message.get("contentType") == "PlainText":
                final_response = first_message.get("content", "")
            elif first_message.get("contentType") == "ImageResponseCard":
                card = first_message.get("imageResponseCard", {})
                title = card.get("title", "")
                subtitle = card.get("subtitle", "")
                buttons = card.get("buttons", [])

                # Construire le message avec les boutons
                final_response = f"{title}\n"
                if subtitle:
                    final_response += f"{subtitle}\n"
                
                final_response += "\n"
                for i, btn in enumerate(buttons, 1):
                    final_response += f"{i}. {btn.get('text', '')}\n"
            else:
                final_response = "Message non supporté."

        print(f"🤖 Réponse finale : {final_response}")

        # Récupérer les credentials Twilio
        creds = get_twilio_credentials()

        # Envoyer la réponse via WhatsApp
        send_whatsapp_message(
            to=from_number,
            body=final_response,
            account_sid=creds["TWILIO_ACCOUNT_SID"],
            auth_token=creds["TWILIO_AUTH_TOKEN"]
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"status": "ok"})
        }

    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
