# lambda/orchestrator/intents/voice_adapter.py  ← nouveau fichier

import re

def adapt_for_voice(message: str, is_voice: bool = False) -> str:
    """
    Adapte un message texte pour la synthèse vocale.
    Supprime emojis, markdown, caractères spéciaux.
    """
    if not is_voice:
        return message  # ← texte normal pour chatbot/WhatsApp

    # ── Supprimer les emojis ──────────────────────────────────────
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symboles
        "\U0001F680-\U0001F6FF"  # transport
        "\U0001F1E0-\U0001F1FF"  # drapeaux
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "✅❌🔴🟡🟢📋🔖💻🔧💡📊🛡️📅🛒"
        "]+",
        flags=re.UNICODE
    )
    message = emoji_pattern.sub("", message)

    # ── Supprimer markdown ────────────────────────────────────────
    message = re.sub(r"\*\*(.*?)\*\*", r"\1", message)  # **bold**
    message = re.sub(r"\*(.*?)\*",     r"\1", message)  # *italic*
    message = re.sub(r"#{1,6}\s",      "",    message)  # # titres

    # ── Remplacer tirets de liste par virgules ────────────────────
    message = re.sub(r"\n-\s",  ", ", message)
    message = re.sub(r"\n•\s",  ", ", message)

    # ── Nettoyer les sauts de ligne multiples ─────────────────────
    message = re.sub(r"\n+", ". ", message)

    # ── Nettoyer espaces multiples ────────────────────────────────
    message = re.sub(r"\s+", " ", message).strip()

    return message


def is_voice_call(event: dict) -> bool:
    """
    Détecte si l'appel vient d'Amazon Connect (voix)
    ou du chatbot/WhatsApp (texte).
    """
    # Amazon Connect ajoute ce champ dans le requestAttributes
    request_attrs = event.get("requestAttributes", {}) or {}
    channel = event.get("inputMode", "")

    return (
        "x-amz-lex:channels:platform" in str(request_attrs) or
        channel in ["Speech", "DTMF"] or
        request_attrs.get("x-amz-lex:accept-content-types", "") == "Audio"
    )
