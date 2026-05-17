from flask import Flask, request, jsonify
import joblib
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)

model = joblib.load(
    os.path.join(BASE_DIR, "../models/complaint_classifier.pkl")
)

vectorizer = joblib.load(
    os.path.join(BASE_DIR, "../models/tfidf_vectorizer.pkl")
)

@app.route("/")
def home():
    return "ML API running successfully"

@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()

    text = data.get("text", "")

    X = vectorizer.transform([text])

    prediction = model.predict(X)[0]

    return jsonify({
        "prediction": prediction
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)