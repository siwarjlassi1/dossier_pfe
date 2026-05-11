import boto3
import json
import logging

logger = logging.getLogger()

# ── Deux clients séparés ──────────────────────────────────────────
bedrock_agent = boto3.client(
    "bedrock-agent-runtime", region_name="us-east-1"
)
bedrock_model = boto3.client(
    "bedrock-runtime", region_name="us-east-1"
)

KNOWLEDGE_BASE_ID = "8DOMZOCGC2"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


# ════════════════════════════════════════════════════════════════════
# ANALYSE DE SENTIMENT
# ════════════════════════════════════════════════════════════════════

def analyze_sentiment(complaint_text: str, locale_id: str = "en_US") -> dict:
    """
    Analyse le sentiment du message client.
    Retourne : sentiment + score + ton de réponse recommandé
    """

    if locale_id == "fr_FR":
        prompt = f"""Analyse le sentiment de ce message client :
"{complaint_text}"

Retourne UNIQUEMENT ce JSON :
{{
    "sentiment": "positif" ou "neutre" ou "negatif" ou "tres_negatif",
    "score": nombre entre 0 et 10 (0=très calme, 10=très énervé),
    "emotions": ["frustration", "colere", "inquietude", "impatience"],
    "ton_recommande": "empathique" ou "professionnel" ou "urgent",
    "phrase_empathie": "phrase d'empathie adaptée au sentiment en français"
}}"""
    else:
        prompt = f"""Analyze the sentiment of this customer message:
"{complaint_text}"

Return ONLY this JSON:
{{
    "sentiment": "positive" or "neutral" or "negative" or "very_negative",
    "score": number between 0 and 10 (0=very calm, 10=very angry),
    "emotions": ["frustration", "anger", "worry", "impatience"],
    "recommended_tone": "empathetic" or "professional" or "urgent",
    "empathy_phrase": "adapted empathy phrase in English"
}}"""

    try:
        model_response = bedrock_model.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 256,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "system": (
                    "Tu es un expert en analyse de sentiment. "
                    "Tu réponds TOUJOURS et UNIQUEMENT en JSON valide. "
                    "Jamais de texte avant ou après le JSON. "
                    "Commence par { et termine par }."
                )
            }),
        )

        raw_text = json.loads(
            model_response["body"].read()
        )["content"][0]["text"]

        logger.info(f"Sentiment brut : {raw_text}")

        # ── Nettoyage markdown ────────────────────────────────────
        cleaned = raw_text.strip()
        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        # ── Extraction JSON ───────────────────────────────────────
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            sentiment_data = json.loads(cleaned[start:end])
            logger.info(f"✅ Sentiment extrait : {sentiment_data}")
            return sentiment_data

    except Exception as e:
        logger.error(f"Erreur analyze_sentiment : {e}")

    # ── Fallback sentiment ────────────────────────────────────────
    if locale_id == "fr_FR":
        return {
            "sentiment": "neutre",
            "score": 5,
            "emotions": [],
            "ton_recommande": "professionnel",
            "phrase_empathie": "Nous comprenons votre situation et allons faire notre maximum pour vous aider."
        }
    else:
        return {
            "sentiment": "neutral",
            "score": 5,
            "emotions": [],
            "recommended_tone": "professional",
            "empathy_phrase": "We understand your situation and will do our best to help you."
        }


# ════════════════════════════════════════════════════════════════════
# AJUSTEMENT URGENCE SELON SENTIMENT
# ════════════════════════════════════════════════════════════════════

def _adjust_urgency(urgency: str, sentiment_score: int, locale_id: str) -> str:
    """
    Ajuste l'urgence selon le sentiment détecté.
    Score >= 8 → urgence élevée automatiquement
    Score >= 6 → urgence minimum moyenne
    """
    if locale_id == "fr_FR":
        if sentiment_score >= 8:
            return "eleve"
        elif sentiment_score >= 6 and urgency == "faible":
            return "moyen"
        return urgency
    else:
        if sentiment_score >= 8:
            return "high"
        elif sentiment_score >= 6 and urgency == "low":
            return "medium"
        return urgency


# ════════════════════════════════════════════════════════════════════
# ANALYSE COMPLAINT ENRICHIE
# ════════════════════════════════════════════════════════════════════

def analyze_complaint(complaint_text: str, locale_id: str = "en_US") -> dict:
    """
    Étape 1 : Analyse de sentiment
    Étape 2 : Retrieve → cherche dans la KB
    Étape 3 : invoke_model → Claude génère le JSON enrichi
    """

    # ── Étape 1 : Analyse de sentiment ───────────────────────────
    logger.info("Étape 1 : Analyse de sentiment...")
    sentiment = analyze_sentiment(complaint_text, locale_id)
    sentiment_score = sentiment.get("score", 5)
    logger.info(f"Sentiment score : {sentiment_score}")

    # ── Étape 2 : Retrieve depuis la KB ──────────────────────────
    logger.info("Étape 2 : Retrieve KB...")
    try:
        retrieve_response = bedrock_agent.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": complaint_text},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,
                }
            },
        )

        results = retrieve_response.get("retrievalResults", [])
        kb_context = "\n\n".join([
            r["content"]["text"]
            for r in results
            if r.get("content", {}).get("text")
        ])

        logger.info(f"KB context trouvé : {len(results)} résultats")

    except Exception as e:
        logger.error(f"Erreur retrieve KB : {e}")
        kb_context = ""

    # ── Étape 3 : Claude génère le JSON enrichi ───────────────────
    logger.info("Étape 3 : Génération JSON enrichi...")

    if locale_id == "fr_FR":
        prompt = f"""Voici la documentation HP pertinente :
{kb_context}

Problème client : "{complaint_text}"

Sentiment détecté : {sentiment.get('sentiment')} (score: {sentiment_score}/10)
Émotions : {sentiment.get('emotions', [])}
Ton recommandé : {sentiment.get('ton_recommande')}

Retourne UNIQUEMENT ce JSON :
{{
    "categorie": "hardware" ou "software" ou "reseau" ou "autre",
    "urgence": "faible" ou "moyen" ou "eleve",
    "resume": "résumé en 1 phrase",
    "solution": "solution en 2-3 phrases basée sur la documentation HP",
    "message_client": "message complet adapté au sentiment : commence par la phrase d'empathie puis donne la solution"
}}"""
    else:
        prompt = f"""Here is the relevant HP documentation:
{kb_context}

Customer problem: "{complaint_text}"

Detected sentiment: {sentiment.get('sentiment')} (score: {sentiment_score}/10)
Emotions: {sentiment.get('emotions', [])}
Recommended tone: {sentiment.get('recommended_tone')}

Return ONLY this JSON:
{{
    "category": "hardware" or "software" or "network" or "other",
    "urgency": "low" or "medium" or "high",
    "summary": "summary in 1 sentence",
    "solution": "solution in 2-3 sentences based on HP documentation",
    "customer_message": "full message adapted to sentiment: start with empathy phrase then give solution"
}}"""

    try:
        model_response = bedrock_model.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "system": (
                    "Tu es un expert technique HP avec une grande empathie. "
                    "Tu réponds TOUJOURS et UNIQUEMENT en JSON valide. "
                    "Jamais de texte avant ou après le JSON. "
                    "Jamais d'explication. "
                    "Commence par { et termine par }."
                )
            }),
        )

        raw_text = json.loads(
            model_response["body"].read()
        )["content"][0]["text"]

        logger.info(f"Réponse Claude : {raw_text}")

        # ── Nettoyage markdown ────────────────────────────────────
        cleaned = raw_text.strip()
        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        # ── Extraction JSON ───────────────────────────────────────
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            analysis = json.loads(cleaned[start:end])

            # ── Ajustement urgence selon sentiment ────────────────
            urgency_key = "urgence" if locale_id == "fr_FR" else "urgency"
            analysis[urgency_key] = _adjust_urgency(
                analysis.get(urgency_key, "moyen" if locale_id == "fr_FR" else "medium"),
                sentiment_score,
                locale_id
            )

            # ── Ajout données sentiment dans le résultat ──────────
            analysis["sentiment"] = sentiment

            logger.info(f"✅ Analyse complète : {analysis}")
            return analysis

        else:
            raise ValueError("Pas de JSON trouvé")

    except json.JSONDecodeError as e:
        logger.error(f"Erreur parsing JSON : {e}")
        return _fallback_from_text(kb_context, complaint_text, locale_id, sentiment)

    except Exception as e:
        logger.error(f"Erreur invoke_model : {e}")
        return _fallback_default(complaint_text, locale_id, sentiment)


# ════════════════════════════════════════════════════════════════════
# FALLBACKS
# ════════════════════════════════════════════════════════════════════

def _fallback_from_text(kb_text: str, complaint_text: str,
                        locale_id: str, sentiment: dict = None) -> dict:
    """Fallback intelligent avec texte KB"""
    logger.info("Fallback intelligent → texte KB utilisé")
    solution = kb_text.strip()[:300] if kb_text else None
    sentiment = sentiment or {}

    if locale_id == "fr_FR":
        return {
            "categorie": "autre",
            "urgence": "moyen",
            "resume": complaint_text[:100],
            "solution": solution or (
                "Notre équipe technique va analyser votre problème "
                "et vous contacter dans les plus brefs délais."
            ),
            "message_client": (
                f"{sentiment.get('phrase_empathie', 'Nous comprenons votre situation.')} "
                "Notre équipe technique va analyser votre problème "
                "et vous contacter dans les plus brefs délais."
            ),
            "sentiment": sentiment,
        }
    else:
        return {
            "category": "other",
            "urgency": "medium",
            "summary": complaint_text[:100],
            "solution": solution or (
                "Our technical team will analyze your issue "
                "and contact you as soon as possible."
            ),
            "customer_message": (
                f"{sentiment.get('empathy_phrase', 'We understand your situation.')} "
                "Our technical team will analyze your issue "
                "and contact you as soon as possible."
            ),
            "sentiment": sentiment,
        }


def _fallback_default(complaint_text: str,
                      locale_id: str, sentiment: dict = None) -> dict:
    """Fallback par défaut"""
    logger.info("Fallback par défaut activé")
    sentiment = sentiment or {}

    if locale_id == "fr_FR":
        return {
            "categorie": "autre",
            "urgence": "moyen",
            "resume": complaint_text[:100],
            "solution": (
                "Notre équipe technique va analyser votre problème "
                "et vous contacter dans les plus brefs délais."
            ),
            "message_client": (
                f"{sentiment.get('phrase_empathie', 'Nous comprenons votre situation.')} "
                "Notre équipe technique va analyser votre problème "
                "et vous contacter dans les plus brefs délais."
            ),
            "sentiment": sentiment,
        }
    else:
        return {
            "category": "other",
            "urgency": "medium",
            "summary": complaint_text[:100],
            "solution": (
                "Our technical team will analyze your issue "
                "and contact you as soon as possible."
            ),
            "customer_message": (
                f"{sentiment.get('empathy_phrase', 'We understand your situation.')} "
                "Our technical team will analyze your issue "
                "and contact you as soon as possible."
            ),
            "sentiment": sentiment,
        }
