# ML/scripts/generate_summary_dataset.py
import pandas as pd
import random

# Templates de descriptions longues
descriptions_templates = [
    # Imprimantes
    "Mon imprimante {model} ne s'allume plus depuis {time}. J'ai essayé de la débrancher et de la rebrancher plusieurs fois mais rien ne fonctionne. Le voyant d'alimentation {light_status}. J'ai vérifié la prise électrique avec un autre appareil et elle fonctionne correctement. L'imprimante a {age} et {warranty_status}.",
    
    "Problème de {issue} sur mon imprimante {model}. Cela arrive {frequency}. J'ai {action_taken} mais le problème persiste. J'utilise du papier de qualité recommandée par HP. L'imprimante a {age}.",
    
    # Ordinateurs
    "Problème de {issue} sur mon ordinateur portable HP {model}. {symptom}. J'ai essayé de {action_taken} mais le problème persiste. {additional_info}. {warranty_status}.",
    
    "Écran {screen_issue} au démarrage de mon PC HP {model}. {symptom}. Parfois après plusieurs tentatives de redémarrage {outcome}. Le problème est apparu {when} et {evolution}.",
    
    # Réseau
    "Problème de connexion {network_type} sur mon {model}. {symptom}. J'ai essayé de {action_taken} mais le problème persiste. {additional_info}.",
    
    # Logiciel
    "Erreur lors de {software_action} sur mon {model}. {error_message}. J'ai essayé {action_taken} mais le problème persiste. {additional_info}.",
]

# Données pour remplir les templates
models = ["LaserJet Pro", "OfficeJet Pro", "EliteBook 840", "ProBook 450", "Pavilion", "ZBook"]
times = ["hier matin", "ce matin", "il y a 2 jours", "la semaine dernière"]
light_statuses = ["ne s'allume même pas", "clignote en rouge", "reste orange"]
ages = ["2 ans", "6 mois", "1 an", "3 ans"]
warranty_statuses = ["est encore sous garantie", "n'est plus sous garantie", "garantie expirée"]
issues = ["bourrage papier", "qualité d'impression médiocre", "scanner non fonctionnel", "WiFi instable"]
frequencies = ["presque à chaque impression", "une fois sur deux", "de temps en temps"]
actions_taken = ["nettoyé les rouleaux", "réinstallé les drivers", "redémarré l'appareil", "mis à jour le firmware"]

def generate_description(template, category):
    """Génère une description à partir d'un template"""
    replacements = {
        'model': random.choice(models),
        'time': random.choice(times),
        'light_status': random.choice(light_statuses),
        'age': random.choice(ages),
        'warranty_status': random.choice(warranty_statuses),
        'issue': random.choice(issues),
        'frequency': random.choice(frequencies),
        'action_taken': random.choice(actions_taken),
        'symptom': "La connexion se coupe toutes les 5 minutes",
        'additional_info': "Les autres appareils fonctionnent normalement",
        'screen_issue': "noir",
        'outcome': "l'écran finit par s'allumer",
        'when': "il y a une semaine",
        'evolution': "devient de plus en plus fréquent",
        'network_type': "WiFi",
        'software_action': "l'installation de Windows 10",
        'error_message': "Le processus s'arrête à 64% avec l'erreur 0x80070570"
    }
    
    desc = template
    for key, value in replacements.items():
        desc = desc.replace(f"{{{key}}}", value)
    
    return desc

def generate_summary(description, category):
    """Génère un résumé à partir de la description"""
    # Extraction des mots-clés
    words = description.split()
    
    # Logique simple de résumé (tu peux l'améliorer)
    if "ne s'allume plus" in description:
        return f"Imprimante ne s'allume plus, voyant d'alimentation défaillant."
    elif "bourrage papier" in description:
        return f"Bourrages papier fréquents, rouleaux nettoyés."
    elif "WiFi" in description or "réseau" in description:
        return f"Problème de connexion réseau, coupures fréquentes."
    elif "écran noir" in description:
        return f"Écran noir au démarrage, problème intermittent."
    else:
        return f"Problème technique sur {category}, diagnostic nécessaire."

# Générer le dataset
data = []
categories = ["Printer", "Hardware", "Network", "Software"]

for i in range(100):  # Génère 100 exemples
    category = random.choice(categories)
    template = random.choice(descriptions_templates)
    
    description = generate_description(template, category)
    summary = generate_summary(description, category)
    
    data.append({
        'id': f'REC{i+1:04d}',
        'description': description,
        'summary': summary,
        'category': category,
        'urgency': random.choice(['Low', 'Medium', 'High', 'Critical'])
    })

# Créer DataFrame
df = pd.DataFrame(data)

# Sauvegarder
df.to_csv('ML/datasets/summary_training_data.csv', index=False)
print(f"✅ Dataset créé : {len(df)} exemples")
print(f"\n📊 Distribution des catégories :")
print(df['category'].value_counts())
print(f"\n📈 Exemples :")
print(df.head(3)[['description', 'summary']])
