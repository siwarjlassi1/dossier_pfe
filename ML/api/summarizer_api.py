from flask import Flask, request, jsonify
from flask_cors import CORS
import re
from typing import Dict
from datetime import datetime

# ============================================================================
# RÉSUMEUR (copie de final_summarizer.py)
# ============================================================================

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
        """Extrait le problème"""
        lines = dialogue.split('\n')
        
        if lang == "fr":
            keywords = ['ne fonctionne', 'ne marche', 'ne s\'allume', 'ne démarre', 'problème', 'panne', 'erreur', 'ne print']
        else:
            keywords = ['not working', 'not printing', 'doesn\'t work', 'won\'t', 'problem', 'issue', 'error', 'failed', 'can\'t', 'unable']
        
        for line in lines:
            line_lower = line.lower()
            if 'client' in line_lower or 'customer' in line_lower:
                for keyword in keywords:
                    if keyword in line_lower:
                        if ':' in line:
                            problem = line.split(':', 1)[1].strip()
                            return problem[:120]
        
        for line in lines:
            if 'client' in line.lower() or 'customer' in line.lower():
                if ':' in line:
                    return line.split(':', 1)[1].strip()[:120]
        
        return ""
    
    def extract_solution(self, dialogue, lang):
        """Extrait la solution"""
        lines = dialogue.split('\n')
        
        if lang == "fr":
            keywords = ['remplacement', 'remplacer', 'réparation', 'réparer', 'ticket', 'technicien', 'garantie', 'créer', 'demande']
        else:
            keywords = ['replacement', 'replace', 'repair', 'fix', 'ticket', 'technician', 'warranty', 'try', 'running', 'cleaning']
        
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
    
    def summarize(self, dialogue):
        """Génère le résumé structuré"""
        try:
            lang = self.detect_language(dialogue)
            product = self.extract_product(dialogue)
            problem = self.extract_problem(dialogue, lang)
            solution = self.extract_solution(dialogue, lang)
            status = self.extract_status(dialogue, lang)
            
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
# API FLASK
# ============================================================================

app = Flask(__name__)
CORS(app)  # Permet les requêtes depuis votre chatbot

# Initialiser le résumeur
summarizer = FinalSummarizer()

@app.route('/', methods=['GET'])
def home():
    """Page d'accueil de l'API"""
    return jsonify({
        'service': 'HP Conversation Summarizer API',
        'version': '1.0',
        'status': 'running',
        'endpoints': {
            '/': 'GET - API info',
            '/health': 'GET - Health check',
            '/summarize': 'POST - Summarize conversation'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Vérification de santé de l'API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/summarize', methods=['POST'])
def summarize():
    """
    Endpoint principal pour résumer une conversation
    
    Body JSON:
    {
        "dialogue": "Client: Bonjour...\nAgent: Bonjour..."
    }
    
    Response JSON:
    {
        "success": true,
        "summary": "Produit: HP LaserJet | Problème: ...",
        "details": {
            "language": "Français",
            "product": "HP LaserJet",
            "problem": "...",
            "solution": "...",
            "status": "Résolu"
        },
        "timestamp": "2026-07-01T14:30:00"
    }
    """
    try:
        # Récupérer les données
        data = request.get_json()
        
        if not data or 'dialogue' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "dialogue" field in request body'
            }), 400
        
        dialogue = data['dialogue']
        
        if not dialogue or not dialogue.strip():
            return jsonify({
                'success': False,
                'error': 'Dialogue cannot be empty'
            }), 400
        
        # Générer le résumé
        result = summarizer.summarize(dialogue)
        
        # Retourner la réponse
        return jsonify({
            'success': True,
            'summary': result['summary'],
            'details': {
                'language': result['language'],
                'product': result['product'],
                'problem': result['problem'],
                'solution': result['solution'],
                'status': result['status']
            },
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# LANCEMENT DE L'API
# ============================================================================

if __name__ == '__main__':
    print("="*80)
    print("🚀 HP CONVERSATION SUMMARIZER API")
    print("="*80)
    print("\n📡 Démarrage du serveur...")
    print("🌐 URL: http://localhost:5000")
    print("\n📋 Endpoints disponibles:")
    print("   GET  /          - Informations sur l'API")
    print("   GET  /health    - Vérification de santé")
    print("   POST /summarize - Résumer une conversation")
    print("\n💡 Pour tester:")
    print('   curl -X POST http://localhost:5000/summarize -H "Content-Type: application/json" -d "{\\"dialogue\\": \\"Client: Bonjour...\\nAgent: Bonjour...\\"}"')
    print("\n⏹️  Pour arrêter: Ctrl+C")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
