def handle_salutation(event):
    """Répond à un message de salutation avec liste des services."""

    locale_id = event.get("bot", {}).get("localeId", "en_US")

    if locale_id == "fr_FR":
        return {
            "sessionState": {
                "dialogAction": {"type": "Close"},
                "intent": {
                    **event["sessionState"]["intent"],
                    "state": "Fulfilled",
                },
            },
            "messages": [
                {
                    "contentType": "ImageResponseCard",
                    "imageResponseCard": {
                        "title": "Bonjour ya hmema! Comment puis-je vous aider aujourd'hui ?",
                        "subtitle": "Veuillez choisir un service :",
                        "buttons": [
                            {"text": "🛒 Commander un produit",  "value": "Je souhaite commander un produit"},
                            {"text": "🔧 Signaler une panne",    "value": "Je souhaite signaler un problème"},
                            {"text": "📦 Vérifier ma commande",  "value": "Je veux vérifier le statut de ma commande"},
                            {"text": "❌ Annuler ma commande",   "value": "Je veux annuler ma commande"},
                            {"text": "🔍 Suivre ma réclamation", "value": "Je veux suivre ma réclamation"},  # 🆕
                        ],
                    },
                }
            ],
        }
    else:
        return {
            "sessionState": {
                "dialogAction": {"type": "Close"},
                "intent": {
                    **event["sessionState"]["intent"],
                    "state": "Fulfilled",
                },
            },
            "messages": [
                {
                    "contentType": "ImageResponseCard",
                    "imageResponseCard": {
                        "title": "Hello! How can I help you today?",
                        "subtitle": "Please choose a service:",
                        "buttons": [
                            {"text": "🛒 Order a product",   "value": "I would like to order a product"},
                            {"text": "🔧 Report a problem",  "value": "I would like to report a problem"},
                            {"text": "📦 Check my order",    "value": "I want to check my order status"},
                            {"text": "❌ Cancel my order",   "value": "I want to cancel my order"},
                            {"text": "🔍 Track my claim",    "value": "I want to track my claim"},  # 🆕
                        ],
                    },
                }
            ],
        }
