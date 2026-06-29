from flask import Flask, request, jsonify
from transformers import T5Tokenizer, T5ForConditionalGeneration
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "results",
    "summarizer",
    "checkpoint-50"
)

print(f"📂 Loading model from: {MODEL_PATH}")

tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH)
model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)

# ✅ Mettre le modèle en mode évaluation (plus rapide)
model.eval()

print("✅ Model loaded successfully")


def generate_summary(text):
    """Génère un résumé optimisé pour la vitesse."""
    
    # ✅ Limiter la longueur d'entrée pour accélérer
    input_text = "summarize: " + text[:300]  # Max 300 caractères
    
    inputs = tokenizer(
        input_text,
        return_tensors="pt",
        max_length=256,      # ✅ Réduit de 512 → 256
        truncation=True,
        padding=False        # ✅ Pas de padding inutile
    )
    
    outputs = model.generate(
        inputs["input_ids"],
        max_length=30,       # ✅ Réduit de 40 → 30
        min_length=10,
        num_beams=2,         # ✅ Réduit de 4 → 2 (2x plus rapide)
        early_stopping=True,
        do_sample=False,     # ✅ Désactiver le sampling
        no_repeat_ngram_size=2  # ✅ Éviter les répétitions
    )
    
    summary = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True
    )
    
    return summary


@app.route("/")
def home():
    return "Summary API running successfully ✅"


@app.route("/summarize", methods=["POST"])
def summarize():
    """Endpoint de résumé avec gestion d'erreur."""
    
    try:
        data = request.get_json()
        
        if not data or "text" not in data:
            return jsonify({"error": "Missing 'text' field"}), 400
        
        text = data.get("text", "")
        
        if not text.strip():
            return jsonify({"error": "Empty text"}), 400
        
        # ✅ Générer le résumé
        summary = generate_summary(text)
        
        return jsonify({
            "summary": summary,
            "status": "success"
        })
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500


if __name__ == "__main__":
    print("🚀 Starting Summary API on port 5001...")
    app.run(host="0.0.0.0", port=5001, debug=False)  # ✅ debug=False en production
