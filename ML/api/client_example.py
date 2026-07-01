import requests
import json

class SummarizerClient:
    """Client pour appeler l'API de résumé"""
    
    def __init__(self, api_url="http://localhost:5000"):
        self.api_url = api_url
    
    def summarize_conversation(self, dialogue):
        """
        Résume une conversation
        
        Args:
            dialogue (str): Conversation au format "Client: ...\nAgent: ..."
        
        Returns:
            dict: Résumé et détails
        """
        try:
            response = requests.post(
                f"{self.api_url}/summarize",
                json={"dialogue": dialogue},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'API returned status {response.status_code}'
                }
        
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Cannot connect to summarizer API. Is it running?'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_api_healthy(self):
        """Vérifie si l'API est en ligne"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🧪 TEST DU CLIENT SUMMARIZER")
    print("="*80 + "\n")
    
    # Créer le client
    client = SummarizerClient()
    
    # Vérifier que l'API est en ligne
    print("1. Vérification de l'API...")
    if client.is_api_healthy():
        print("   ✅ API en ligne\n")
    else:
        print("   ❌ API hors ligne")
        print("   💡 Lancez d'abord: python summarizer_api.py\n")
        exit(1)
    
    # Exemple de conversation
    dialogue = """Client: Bonjour, mon imprimante HP LaserJet Pro ne fonctionne plus
Agent: Bonjour, je vais vous aider
Client: Elle ne s'allume plus du tout
Agent: Je vais créer une demande de remplacement
Client: Merci beaucoup"""
    
    print("2. Résumé de la conversation...")
    print(f"   Dialogue: {dialogue[:50]}...\n")
    
    result = client.summarize_conversation(dialogue)
    
    if result['success']:
        print("   ✅ Résumé généré avec succès\n")
        print(f"   📄 Résumé: {result['summary']}\n")
        print(f"   📊 Détails:")
        print(f"      - Langue   : {result['details']['language']}")
        print(f"      - Produit  : {result['details']['product']}")
        print(f"      - Problème : {result['details']['problem']}")
        print(f"      - Solution : {result['details']['solution']}")
        print(f"      - Statut   : {result['details']['status']}")
    else:
        print(f"   ❌ Erreur: {result['error']}")
    
    print("\n" + "="*80)
    print("✅ TEST TERMINÉ")
    print("="*80)
