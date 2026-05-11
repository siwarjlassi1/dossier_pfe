import json    #manipuler données
import logging  #logs (important en cloud)
import os   #récupérer variables d’environnement
import urllib.request
import urllib.error

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from intents.salutation import handle_salutation
from intents.fallback import handle_fallback

# ── Variables d'environnement ─────────────────────────────────────
#connecter ton orchestrator avec :
#API Gateway
#Bedrock
#Knowledge Base

API_URL              = os.environ.get("API_GATEWAY_URL", "")
KNOWLEDGE_BASE_ID    = os.environ.get("KNOWLEDGE_BASE_ID", "")
BEDROCK_MODEL_ARN    = os.environ.get("BEDROCK_MODEL_ARN", "")
BEDROCK_AGENT_ID     = os.environ.get("BEDROCK_AGENT_ID", "")
BEDROCK_AGENT_ALIAS  = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "")

#c'est la fonction clé qui appel les microservices via API Gateway
#evoie requete POST et recoit reponse JSON
def call_microservice(path, payload):
    url = f"{API_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.error(f"HTTPError {e.code} sur {url}: {e.read()}")
        raise
    except Exception as e:
        logger.error(f"Erreur appel microservice {url}: {e}")
        raise


# ── Handlers ──────────────────────────────────────────────────────

def handle_commander_produit(event):
    from intents.commander_produit import handle_commander_produit as _local
    import intents.commander_produit as mod
    mod.call_microservice = call_microservice  #ca veut dire que l’intent peut appeler un microservice
    return _local(event)


def handle_reclamer_panne(event):
    from intents.reclamer_panne import handle_reclamer_panne as _local
    import intents.reclamer_panne as mod
    mod.call_microservice = call_microservice
    return _local(event)


def handle_verifier_commande(event):
    from intents.verifier_commande import handle_verifier_commande as _local
    import intents.verifier_commande as mod
    mod.call_microservice = call_microservice
    return _local(event)


def handle_annuler_commande(event):
    from intents.annuler_commande import handle_annuler_commande as _local
    import intents.annuler_commande as mod
    mod.call_microservice = call_microservice
    return _local(event)


def handle_demander_depannage(event):
    from intents.demander_depannage import handle_demander_depannage as _local
    return _local(event)

def handle_suivre_reclamation(event):
    from intents.suivre_reclamation import handle_suivre_reclamation as _local
    import intents.suivre_reclamation as mod
    mod.call_microservice = call_microservice
    return _local(event)



# ── Routing ───────────────────────────────────────────────────────
#mapper :intent → fonction
INTENT_HANDLERS = {
    "Salutation":        handle_salutation,
    "CommanderProduit":  handle_commander_produit,
    "ReclamerPanne":     handle_reclamer_panne,
    "VerifierCommande":  handle_verifier_commande,
    "AnnulerCommande":   handle_annuler_commande,
    "DemanderDepannage": handle_demander_depannage,
    "SuivreReclamation":   handle_suivre_reclamation,  
    "FallbackIntent":    handle_fallback,
}

#la fonction principale :c’est le point d’entrée AWS Lambda
def handler(event, context):  #recoit la requete
    logger.info(f"Event reçu : {json.dumps(event)}")
    intent_name = event["sessionState"]["intent"]["name"]  #récupérer intent:lex fournit ca automatiquement
    logger.info(f"Intent détecté : {intent_name}")
    intent_handler = INTENT_HANDLERS.get(intent_name, handle_fallback) #choisir handler
    return intent_handler(event)
