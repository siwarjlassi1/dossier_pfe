def handle_fallback(event):
    """Répond quand Lex ne comprend pas la demande."""

    locale_id = event.get("bot", {}).get("localeId", "en_US")

    if locale_id == "fr_FR":
        return {
            "sessionState": {
                "dialogAction": {"type": "Close"},
                "intent": {
                    **event["sessionState"]["intent"],
                    "state": "Failed",
                },
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": (
                        "Je suis désolé, je n'ai pas compris. "
                        "Veuillez choisir un service :"
                    ),
                },
                {
                    "contentType": "ImageResponseCard",
                    "imageResponseCard": {
                        "title": "Que souhaitez-vous faire ?",
                        "buttons": [
                            {"text": "🛒 Commander un produit",  "value": "Je souhaite commander un produit"},
                            {"text": "🔧 Signaler une panne",    "value": "Je souhaite signaler un problème"},
                            {"text": "📦 Vérifier ma commande",  "value": "Je veux vérifier le statut de ma commande"},
                            {"text": "❌ Annuler ma commande",   "value": "Je veux annuler ma commande"},
                            {"text": "🔍 Suivre ma réclamation", "value": "Je veux suivre ma réclamation"},  # 🆕
                        ],
                    },
                },
            ],
        }
    else:
        return {
            "sessionState": {
                "dialogAction": {"type": "Close"},
                "intent": {
                    **event["sessionState"]["intent"],
                    "state": "Failed",
                },
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": (
                        "I'm sorry, I didn't understand that. "
                        "Please choose a service:"
                    ),
                },
                {
                    "contentType": "ImageResponseCard",
                    "imageResponseCard": {
                        "title": "What would you like to do?",
                        "buttons": [
                            {"text": "🛒 Order a product",   "value": "I would like to order a product"},
                            {"text": "🔧 Report a problem",  "value": "I would like to report a problem"},
                            {"text": "📦 Check my order",    "value": "I want to check my order status"},
                            {"text": "❌ Cancel my order",   "value": "I want to cancel my order"},
                            {"text": "🔍 Track my claim",    "value": "I want to track my claim"},  # 🆕
                        ],
                    },
                },
            ],
        }
