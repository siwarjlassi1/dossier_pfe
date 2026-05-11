import boto3
import json
import logging
import uuid

logger = logging.getLogger()

AGENT_ID       = "R604OPQQWY"
AGENT_ALIAS_ID = "77RNRLMRAS"

client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")


def invoke_agent(problem_desc: str, product_ref: str, session_id: str, sentiment: str = "NEUTRAL", fr: bool = True) -> dict:

    if fr:
        sentiment_context = {
            "NEGATIVE": "Le client est très frustré et mécontent. Sois empathique, rassurant et prioritaire. Commence par reconnaître sa frustration.",
            "POSITIVE": "Le client est calme et confiant. Sois professionnel et efficace.",
            "NEUTRAL":  "Le client est neutre. Sois clair, précis et structuré.",
            "MIXED":    "Le client a des sentiments mitigés. Sois attentif et compréhensif.",
        }.get(sentiment, "Sois professionnel et précis.")

        prompt = f"""
        Contexte émotionnel du client : {sentiment_context}
        Réponds OBLIGATOIREMENT en français.
        
        Le client a un problème avec son produit HP {product_ref}.
        Description du problème : {problem_desc}
        
        Analyse ce problème, consulte la base de connaissance HP 
        et propose une solution précise et adaptée à l'état émotionnel du client.
        """
    else:
        sentiment_context = {
            "NEGATIVE": "The client is very frustrated and unhappy. Be empathetic, reassuring and prioritize their issue. Start by acknowledging their frustration.",
            "POSITIVE": "The client is calm and confident. Be professional and efficient.",
            "NEUTRAL":  "The client is neutral. Be clear, precise and structured.",
            "MIXED":    "The client has mixed feelings. Be attentive and understanding.",
        }.get(sentiment, "Be professional and precise.")

        prompt = f"""
        Client emotional context : {sentiment_context}
        Reply ONLY in English.
        
        The client has a problem with their HP {product_ref}.
        Problem description : {problem_desc}
        
        Analyze this problem, consult the HP knowledge base 
        and propose a precise solution adapted to the client's emotional state.
        """

    try:
        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            memoryId=session_id,
            inputText=prompt,
            enableTrace=True,
        )

        full_response = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk = event["chunk"]["bytes"].decode("utf-8")
                full_response += chunk

        logger.info(f"Agent response: {full_response}")

        return {
            "solution":       full_response,
            "session_id":     session_id,
            "agent_response": True
        }

    except Exception as e:
        logger.error(f"Agent invocation error: {e}")
        return {
            "solution":       "",
            "agent_response": False,
            "error":          str(e)
        }



def get_session_id(event: dict) -> str:
    """
    Génère ou récupère un session_id unique par client.
    Stocké dans sessionAttributes pour persistance.
    """
    session_attrs = event.get("sessionState", {}) \
                         .get("sessionAttributes", {}) or {}
    
    # Si session_id existe déjà → on le réutilise (mémoire !)
    if "agent_session_id" in session_attrs:
        return session_attrs["agent_session_id"]
    
    # Sinon → on en crée un nouveau
    new_session_id = str(uuid.uuid4())
    return new_session_id
