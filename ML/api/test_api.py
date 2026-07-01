import requests
import json

print("="*80)
print("🧪 TEST DE L'API HP SUMMARIZER")
print("="*80 + "\n")

API_URL = "http://localhost:5000"

# ============================================================================
# TEST 1 : Health Check
# ============================================================================

print("TEST 1 : Health Check")
print("-" * 40)

try:
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
except Exception as e:
    print(f"❌ Erreur: {e}\n")

# ============================================================================
# TEST 2 : Résumé en FRANÇAIS
# ============================================================================

print("TEST 2 : Résumé en FRANÇAIS")
print("-" * 40)

dialogue_fr = """Client: Bonjour, mon imprimante HP LaserJet Pro ne fonctionne plus
Agent: Bonjour, je vais vous aider
Client: Elle ne s'allume plus du tout
Agent: Je vais créer une demande de remplacement
Client: Merci beaucoup"""

try:
    response = requests.post(
        f"{API_URL}/summarize",
        json={"dialogue": dialogue_fr},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")
except Exception as e:
    print(f"❌ Erreur: {e}\n")

# ============================================================================
# TEST 3 : Résumé en ANGLAIS
# ============================================================================

print("TEST 3 : Résumé en ANGLAIS")
print("-" * 40)

dialogue_en = """Customer: Hi, my HP DeskJet printer is not printing in color
Agent: Hello, I'll help you
Customer: It's an HP DeskJet 3755
Agent: Try running a print head cleaning cycle
Customer: It works now! Thank you!"""

try:
    response = requests.post(
        f"{API_URL}/summarize",
        json={"dialogue": dialogue_en},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
except Exception as e:
    print(f"❌ Erreur: {e}\n")

print("="*80)
print("✅ TESTS TERMINÉS")
print("="*80)
