import re, json
from collections import defaultdict

# 1. Lire le fichier GRXML
with open("in8200_GetModelNumber_1.grxml") as f:
    content = f.read()

# 2. Découper en 419 blocs (un par modèle)
blocks = re.split(r'\n\t<item>\n', content)

mapping = defaultdict(set)

# 3. Pour chaque bloc...
for block in blocks[1:]:
    
    # Extraire le SWI_meaning (ex: "m26")
    m = re.search(r"SWI_meaning='([^']+)'", block)
    meaning = m.group(1)
    
    # Extraire les variantes dans les <one-of>
    one_ofs = re.findall(r'<one-of>(.*?)</one-of>', block, re.DOTALL)
    for oof in one_ofs:
        for si in re.findall(r'<item>(.*?)</item>', oof, re.DOTALL):
            clean = re.sub(r'<[^>]+>', ' ', si)
            clean = re.sub(r'\s+', ' ', clean).strip().lower()
            if clean:
                mapping[meaning].add(clean)

# 4. Inverser le mapping
reverse_map = {}
for meaning, variants in mapping.items():
    for v in variants:
        reverse_map[v] = meaning
        reverse_map[v.replace(" ", "")] = meaning

# 5. Sauvegarder en JSON → c'est le grxml_mapping.json !
with open("grxml_mapping.json", "w") as f:
    json.dump(reverse_map, f, indent=2)

### Ce script a produit `grxml_mapping.json`

##in8200_GetModelNumber_1.grxml  →  [script Python]  →  grxml_mapping.json
      ## (fichier GRXML)               (exécuté 1x)        (3338 entrées)


## Ce qui est dans ton Lambda
##lambda/orchestrator/
##├── handler.py
##├── grxml_mapping.json      ← résultat du script (fichier statique)
##├── model_normalizer.py     ← charge le JSON et normalise
##└── intents/
  ##  └── commander_produit.py