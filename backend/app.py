"""
SAFE Tool Backend.
Run with: python app.py
Private repository test - confirming push access
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from llm_service import analyse_prompt
from prompts import DETECTION_PROMPT_V1_2

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "safe-tool-backend"})


@app.route("/api/analyse", methods=["POST"])
def analyse():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "Missing 'prompt' field in request body"}), 400
    
    user_prompt = data["prompt"].strip()
    if not user_prompt:
        return jsonify({"error": "Prompt is empty"}), 400
    
    if len(user_prompt) > 10000:
        return jsonify({"error": "Prompt exceeds maximum length of 10000 characters"}), 400
    
    result = analyse_prompt(user_prompt, DETECTION_PROMPT_V1_2)
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)