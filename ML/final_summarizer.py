import re
from typing import Dict

class FinalSummarizer:
    """Résumeur bilingue optimisé pour HP Support"""
    
    def __init__(self):
        print("✅ Résumeur HP initialisé")
    
    def detect_language(self, text):
        """Détecte français ou anglais"""
        text_lower = text.lower()
        
        french_words = ['bonjour', 'merci', 'je', 'tu', 'le', 'la', 'client', 'problème', 'imprimante', 'ordinateur']
        english_words = ['hello', 'hi', 'thank', 'customer', 'issue', 'problem', 'printer', 'computer']
        
        french_count = sum(1 for word in french_words if word in text_lower)
        english_count = sum(1 for word in english_words if word in text_lower)
        
        return "fr" if french_count > english_count else "en"
    
    def extract_product(self, text):
        """Extrait le produit HP"""
        patterns = [
            r'HP\s+\w+(?:\s+\w+)?(?:\s+\d+)?',
            r'imprimante\s+HP',
            r'ordinateur\s+HP',
            r'laptop\s+HP'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return ""
    
    def extract_problem(self, dialogue, lang):
        """Extrait le problème - VERSION AMÉLIORÉE"""
        lines = dialogue.split('\n')
        
        if lang == "fr":
            keywords = ['ne fonctionne', 'ne marche', 'ne s\'allume', 'ne démarre', 'problème', 'panne', 'erreur', 'ne print']
        else:
            keywords = ['not working', 'not printing', 'doesn\'t work', 'won\'t', 'problem', 'issue', 'error', 'failed', 'can\'t', 'unable']
        
        # Chercher dans TOUTES les lignes du client/customer
        for line in lines:
            line_lower = line.lower()
            if 'client' in line_lower or 'customer' in line_lower:
                for keyword in keywords:
                    if keyword in line_lower:
                        if ':' in line:
                            problem = line.split(':', 1)[1].strip()
                            return problem[:120]
        
        # Fallback: première ligne du client
        for line in lines:
            if 'client' in line.lower() or 'customer' in line.lower():
                if ':' in line:
                    return line.split(':', 1)[1].strip()[:120]
        
        return ""
    
    def extract_solution(self, dialogue, lang):
        """Extrait la solution - VERSION AMÉLIORÉE"""
        lines = dialogue.split('\n')
        
        if lang == "fr":
            keywords = ['remplacement', 'remplacer', 'réparation', 'réparer', 'ticket', 'technicien', 'garantie', 'créer', 'demande']
        else:
            keywords = ['replacement', 'replace', 'repair', 'fix', 'ticket', 'technician', 'warranty', 'try', 'running', 'cleaning']
        
        # Chercher dans les lignes de l'agent
        for line in lines:
            line_lower = line.lower()
            if 'agent' in line_lower:
                for keyword in keywords:
                    if keyword in line_lower:
                        if ':' in line:
                            solution = line.split(':', 1)[1].strip()
                            return solution[:120]
        
        return ""
    
    def extract_status(self, dialogue, lang):
        """Extrait le statut"""
        dialogue_lower = dialogue.lower()
        
        if lang == "fr":
            if any(word in dialogue_lower for word in ['fonctionne maintenant', 'marche maintenant', 'résolu', 'merci beaucoup']):
                return "Résolu"
            elif any(word in dialogue_lower for word in ['ticket', 'technicien', 'contactera']):
                return "En cours"
            elif 'remplacement' in dialogue_lower:
                return "Remplacement en cours"
            else:
                return "Traité"
        else:
            if any(word in dialogue_lower for word in ['works now', 'working now', 'resolved', 'thank you', 'thanks']):
                return "Resolved"
            elif any(word in dialogue_lower for word in ['ticket', 'technician', 'contact']):
                return "In progress"
            elif 'replacement' in dialogue_lower:
                return "Replacement in progress"
            else:
                return "Processed"
        
        return ""
    
    def summarize(self, dialogue):
        """Génère le résumé structuré"""
        try:
            lang = self.detect_language(dialogue)
            product = self.extract_product(dialogue)
            problem = self.extract_problem(dialogue, lang)
            solution = self.extract_solution(dialogue, lang)
            status = self.extract_status(dialogue, lang)
            
            # Construction du résumé
            if lang == "fr":
                parts = []
                if product:
                    parts.append(f"Produit: {product}")
                if problem:
                    parts.append(f"Problème: {problem}")
                if solution:
                    parts.append(f"Solution: {solution}")
                if status:
                    parts.append(f"Statut: {status}")
                summary = " | ".join(parts) if parts else "Conversation HP Support"
            else:
                parts = []
                if product:
                    parts.append(f"Product: {product}")
                if problem:
                    parts.append(f"Issue: {problem}")
                if solution:
                    parts.append(f"Solution: {solution}")
                if status:
                    parts.append(f"Status: {status}")
                summary = " | ".join(parts) if parts else "HP Support Conversation"
            
            return {
                'summary': summary,
                'language': 'Français' if lang == 'fr' else 'English',
                'product': product,
                'problem': problem,
                'solution': solution,
                'status': status
            }
        
        except Exception as e:
            return {
                'summary': f'Erreur: {str(e)}',
                'language': 'Unknown',
                'product': '',
                'problem': '',
                'solution': '',
                'status': ''
            }

# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🧪 TEST DU RÉSUMEUR FINAL")
    print("="*80 + "\n")
    
    summarizer = FinalSummarizer()
    
    # TEST 1 : FRANÇAIS
    print("="*80)
    print("TEST 1 : FRANÇAIS - Imprimante ne s'allume plus")
    print("="*80)
    
    dialogue_fr_1 = """Client: Bonjour, mon imprimante HP LaserJet Pro ne fonctionne plus
Agent: Bonjour, je vais vous aider
Client: Elle ne s'allume plus du tout
Agent: Je vais créer une demande de remplacement
Client: Merci beaucoup"""
    
    result = summarizer.summarize(dialogue_fr_1)
    print(f"\n📄 Résumé: {result['summary']}\n")
    
    # TEST 2 : ANGLAIS - Problème couleur
    print("="*80)
    print("TEST 2 : ENGLISH - Color printing issue")
    print("="*80)
    
    dialogue_en_1 = """Customer: Hi, my HP DeskJet printer is not printing in color
Agent: Hello, I'll help you
Customer: It's an HP DeskJet 3755
Agent: Try running a print head cleaning cycle
Customer: It works now! Thank you!"""
    
    result = summarizer.summarize(dialogue_en_1)
    print(f"\n📄 Résumé: {result['summary']}\n")
    
    # TEST 3 : FRANÇAIS - Ordinateur
    print("="*80)
    print("TEST 3 : FRANÇAIS - Ordinateur ne démarre plus")
    print("="*80)
    
    dialogue_fr_2 = """Client: Bonjour, mon ordinateur HP Pavilion ne démarre plus
Agent: Bonjour, quel est le problème?
Client: L'écran reste noir
Agent: Je vais créer un ticket de réparation. Un technicien vous contactera sous 24h
Client: Merci"""
    
    result = summarizer.summarize(dialogue_fr_2)
    print(f"\n📄 Résumé: {result['summary']}\n")
    
    # TEST 4 : ANGLAIS - Installation
    print("="*80)
    print("TEST 4 : ENGLISH - Software installation")
    print("="*80)
    
    dialogue_en_2 = """Customer: I can't install the HP Smart app
Agent: What operating system are you using?
Customer: Windows 11
Agent: Try running the installer as administrator
Customer: It's installing now! Thank you!"""
    
    result = summarizer.summarize(dialogue_en_2)
    print(f"\n📄 Résumé: {result['summary']}\n")
    
    print("="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80)
    print("\n🎯 Résumeur prêt pour l'API Flask !\n")
