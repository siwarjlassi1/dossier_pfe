# lambda/microservices/summarize/handler.py

import json
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ConversationSummarizer:
    """Résumeur bilingue optimisé pour HP Support"""
    
    def detect_language(self, text):
        """Détecte français ou anglais"""
        text_lower = text.lower()
        
        french_words = ['bonjour', 'merci', 'je', 'problème', 'imprimante', 'ordinateur', 'garantie']
        english_words = ['hello', 'thank', 'problem', 'issue', 'printer', 'computer', 'warranty']
        
        french_count = sum(1 for word in french_words if word in text_lower)
        english_count = sum(1 for word in english_words if word in text_lower)
        
        return "fr" if french_count > english_count else "en"
    
    def extract_product(self, text):
        """Extrait le produit HP"""
        try:
            patterns = [
                r'HP\s+\w+(?:\s+\w+)?(?:\s+\d+)?',
                r'elitebook\s*\d*',
                r'laserjet\s*\w*',
                r'pavilion\s*\w*',
                r'envy\s*\w*',
                r'omen\s*\w*',
                r'[mM]\d+',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    product = match.group(0).strip()
                    if not product.lower().startswith('hp'):
                        product = f"HP {product.capitalize()}"
                    return product
            return ""
        except Exception as e:
            logger.error(f"Error extracting product: {e}")
            return ""
    
    def extract_problem_short(self, dialogue, lang):
        """Extrait un résumé court du problème (max 80 caractères)"""
        try:
            lines = dialogue.split('\n')
            
            # Chercher après "What is the exact problem?"
            for i, line in enumerate(lines):
                if 'exact' in line.lower() or 'quel est le problème' in line.lower():
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if ':' in next_line:
                            problem = next_line.split(':', 1)[1].strip()
                            
                            # Résumer le problème
                            if lang == "en":
                                if 'wifi' in problem.lower() or 'network' in problem.lower():
                                    return "WiFi disconnection issues"
                                elif 'print' in problem.lower():
                                    return "Printing problems"
                                elif 'battery' in problem.lower():
                                    return "Battery issues"
                                elif 'screen' in problem.lower():
                                    return "Display problems"
                                elif 'slow' in problem.lower():
                                    return "Performance issues"
                                else:
                                    return problem[:80]
                            else:
                                if 'wifi' in problem.lower() or 'réseau' in problem.lower():
                                    return "Problèmes de déconnexion WiFi"
                                elif 'imprim' in problem.lower():
                                    return "Problèmes d'impression"
                                elif 'batterie' in problem.lower():
                                    return "Problèmes de batterie"
                                elif 'écran' in problem.lower():
                                    return "Problèmes d'affichage"
                                elif 'lent' in problem.lower():
                                    return "Problèmes de performance"
                                else:
                                    return problem[:80]
            
            return ""
        except Exception as e:
            logger.error(f"Error extracting problem: {e}")
            return ""
    
    def extract_solution_actions(self, dialogue, lang):
        """Extrait les actions de solution (max 3)"""
        try:
            lines = dialogue.split('\n')
            
            # Chercher "Here is the solution"
            for line in lines:
                if 'solution' in line.lower() and 'agent' in line.lower():
                    if ':' in line:
                        solution = line.split(':', 1)[1].strip()
                        
                        # Extraire les actions clés
                        actions = []
                        
                        if 'update' in solution.lower() and 'driver' in solution.lower():
                            actions.append("update network drivers" if lang == "en" else "mise à jour pilotes réseau")
                        
                        if 'reset' in solution.lower() and 'network' in solution.lower():
                            actions.append("reset network settings" if lang == "en" else "réinitialisation paramètres réseau")
                        
                        if 'power cycle' in solution.lower() or 'restart' in solution.lower() or 'reboot' in solution.lower():
                            actions.append("power cycle" if lang == "en" else "redémarrage complet")
                        
                        if 'check' in solution.lower():
                            actions.append("check background tasks" if lang == "en" else "vérification tâches")
                        
                        if 'contact' in solution.lower() or '24' in solution.lower():
                            actions.append("technical follow-up" if lang == "en" else "suivi technique")
                        
                        # Limiter à 3 actions
                        return actions[:3]
            
            return []
        except Exception as e:
            logger.error(f"Error extracting solution: {e}")
            return []
    
    def extract_warranty_status(self, dialogue):
        """Extrait le statut de garantie"""
        try:
            dialogue_lower = dialogue.lower()
            
            if 'under warranty' in dialogue_lower or 'sous garantie' in dialogue_lower:
                return True
            elif 'out of warranty' in dialogue_lower or 'hors garantie' in dialogue_lower:
                return False
            
            return None
        except Exception as e:
            logger.error(f"Error extracting warranty: {e}")
            return None
    
    def summarize(self, dialogue):
        """Génère un VRAI résumé narratif"""
        try:
            logger.info(f"📝 Dialogue length: {len(dialogue)}")
            
            lang = self.detect_language(dialogue)
            logger.info(f"🌍 Language: {lang}")
            
            product = self.extract_product(dialogue)
            logger.info(f"🖨️ Product: {product}")
            
            problem = self.extract_problem_short(dialogue, lang)
            logger.info(f"❗ Problem: {problem}")
            
            solution_actions = self.extract_solution_actions(dialogue, lang)
            logger.info(f"🔧 Solution actions: {solution_actions}")
            
            warranty = self.extract_warranty_status(dialogue)
            logger.info(f"📋 Warranty: {warranty}")
            
            # ── CONSTRUIRE LE RÉSUMÉ NARRATIF ──────────────────────
            
            if lang == "fr":
                # Partie 1 : Problème
                summary = f"Client signale {problem.lower()}"
                
                # Partie 2 : Produit
                if product:
                    summary += f" sur {product}"
                
                # Partie 3 : Garantie
                if warranty is True:
                    summary += " (sous garantie)"
                elif warranty is False:
                    summary += " (hors garantie)"
                
                summary += "."
                
                # Partie 4 : Solution
                if solution_actions:
                    summary += f" IA recommande : {', '.join(solution_actions)}."
                
                # Partie 5 : Statut
                summary += " Dossier en cours - équipe technique contactera sous 24h."
            
            else:
                # Partie 1 : Problème
                summary = f"Customer reported {problem.lower()}"
                
                # Partie 2 : Produit
                if product:
                    summary += f" on {product}"
                
                # Partie 3 : Garantie
                if warranty is True:
                    summary += " (under warranty)"
                elif warranty is False:
                    summary += " (out of warranty)"
                
                summary += "."
                
                # Partie 4 : Solution
                if solution_actions:
                    summary += f" AI recommended: {', '.join(solution_actions)}."
                
                # Partie 5 : Statut
                summary += " Case in progress - technical team will follow up within 24h."
            
            logger.info(f"✅ Summary: {summary}")
            
            return {
                'summary': summary,
                'language': 'Français' if lang == 'fr' else 'English',
                'product': product,
                'problem': problem,
                'solution': ', '.join(solution_actions) if solution_actions else '',
                'status': 'In progress' if lang == 'en' else 'En cours'
            }
        
        except Exception as e:
            logger.error(f"❌ Error in summarize: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'summary': f'Error: {str(e)}',
                'language': 'Unknown',
                'product': '',
                'problem': '',
                'solution': '',
                'status': ''
            }


# Instance globale
summarizer = ConversationSummarizer()


def lambda_handler(event, context):
    """Handler Lambda"""
    
    logger.info(f"📥 Event: {json.dumps(event)[:300]}")
    
    try:
        if isinstance(event, str):
            event = json.loads(event)
        
        dialogue = event.get('dialogue', '')
        conversation_id = event.get('conversation_id', 'unknown')
        
        if not dialogue:
            logger.error("❌ Missing dialogue")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing dialogue field'
                })
            }
        
        logger.info(f"🔄 Summarizing conversation {conversation_id}...")
        
        result = summarizer.summarize(dialogue)
        
        logger.info(f"✅ Summary generated successfully")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'conversation_id': conversation_id,
                'summary': result['summary'],
                'details': {
                    'language': result['language'],
                    'product': result['product'],
                    'problem': result['problem'],
                    'solution': result['solution'],
                    'status': result['status']
                }
            }, ensure_ascii=False)
        }
    
    except Exception as e:
        logger.error(f"❌ Handler error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
