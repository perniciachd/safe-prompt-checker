# SAFE Tool — Day 1 Setup Guide

This document walks you through setting up the project from scratch on your Mac. By the end of Day 1 you'll have a working backend and frontend talking to each other.

Project root: `/Users/manan/Desktop/PerniciaAI/TrainingTopics/ResponsibleAI/tool/`

---

## Final Folder Structure (after Day 1)

```
tool/
├── safe-detection-prompt.md          (existing engineering doc)
├── marketing-assets/                 (existing)
├── system-prompts/                   (existing)
│
├── backend/
│   ├── venv/                         (Python virtual environment)
│   ├── app.py                        (Flask application)
│   ├── llm_service.py                (OpenAI integration, model-agnostic)
│   ├── prompts.py                    (system prompts as Python strings)
│   ├── requirements.txt              (Python dependencies)
│   ├── .env                          (API key — never commit this)
│   └── .gitignore
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── InputScreen.jsx
│   │   │   └── ResultsScreen.jsx
│   │   └── api.js                    (backend communication)
│   ├── package.json
│   ├── vite.config.js
│   └── .gitignore
│
└── README.md
```

---

## Step 1: Open Terminal and Navigate to Project

```bash
cd /Users/manan/Desktop/PerniciaAI/TrainingTopics/ResponsibleAI/tool
```

Confirm where you are:
```bash
pwd
```

---

## Step 2: Initialise Git Repository

This protects your work from day one.

```bash
git init
echo "node_modules/" > .gitignore
echo "venv/" >> .gitignore
echo ".env" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "dist/" >> .gitignore
echo ".DS_Store" >> .gitignore
```

---

## Step 3: Set Up the Python Backend

### 3a. Create the backend folder and enter it

```bash
mkdir backend
cd backend
```

### 3b. Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

You should now see `(venv)` at the start of your terminal prompt. This means you're working inside the isolated Python environment.

### 3c. Create requirements.txt

Create a file called `requirements.txt` with this content:

```
flask==3.0.0
flask-cors==4.0.0
openai==1.54.0
python-dotenv==1.0.0
```

Then install:

```bash
pip install -r requirements.txt
```

### 3d. Create your .env file

Create `.env` with this content (replace with your actual key):

```
OPENAI_API_KEY=sk-your-actual-openai-key-here
LLM_PROVIDER=openai
```

The `LLM_PROVIDER` variable is what makes the abstraction clean. Later, to switch to Claude, you change this one line and add an Anthropic key. Your application code doesn't change.

### 3e. Create prompts.py

Create `prompts.py` with the production detection prompt:

```python
"""
System prompts for the SAFE Framework Detection Tool.
Versioned. Modify here when refining.
"""

DETECTION_PROMPT_V1_2 = """You are a SAFE Framework Detection Specialist with deep expertise in 
financial services confidentiality requirements. Your job is to analyse 
prompts written by professionals before they are submitted to external 
AI systems and identify every element that constitutes sensitive data 
under regulatory and confidentiality standards.

Your analysis must account for:
- SEBI regulations on insider trading and material non-public information
- RBI guidelines on customer data confidentiality and banking secrecy
- DPDP Act 2023 requirements for personal data protection
- GDPR for any clients or data subjects in EU jurisdictions
- Internal fiduciary duties to clients and counterparties
- Market abuse and front-running risks
- General employment and HR confidentiality norms
- Healthcare data sensitivity where relevant

Missing a single sensitive element could result in regulatory action, 
license risk, breach of fiduciary duty, or significant reputational 
damage. The cost of false negatives is high. When uncertain, flag.

SENSITIVE DATA CATEGORIES TO DETECT:

1. personal_identifiers
2. compensation_data
3. performance_and_employment_status
4. client_account_information
5. trade_and_transaction_data
6. deal_and_corporate_finance_information
7. regulatory_and_compliance_matters
8. internal_financial_metrics
9. counterparty_and_exposure_data
10. personal_financial_information
11. health_and_medical_information

DETECTION METHODOLOGY:

Pass 1: Direct identifiers
Pass 2: Indirect identifiers
Pass 3: Quantitative sensitive data
Pass 4: Combinatorial risk
Pass 5: Context and metadata

ADDITIONAL DETECTION DISCIPLINE:

1. Combinatorial reasoning lives ONLY in combinatorial_notes field. 
   Do NOT create individual items with category "combinatorial_risk".

2. Client portfolio holdings tied to identified clients should be 
   classified under client_account_information, not 
   trade_and_transaction_data.

3. In each item's rationale, cite specific regulation or standard 
   that applies, but keep language accessible.

OUTPUT FORMAT:

Return ONLY a JSON object (no other text, no markdown fences) with this structure:

{
  "overall_risk_score": <integer 1-10>,
  "total_items_flagged": <integer>,
  "plain_summary": "<2-3 sentences in plain English explaining what was found>",
  "items": [
    {
      "id": <integer>,
      "category": "<category name>",
      "excerpt": "<exact text>",
      "plain_explanation": "<one sentence in plain English>",
      "regulatory_basis": "<specific regulation or standard>",
      "confidence": "high|medium|low",
      "suggested_replacement_type": "<brief hint>"
    }
  ],
  "combinatorial_notes": "<string or null>"
}
"""

# Rewriter prompt will be added in Day 3
REWRITER_PROMPT_V1_0 = """[Placeholder — to be drafted on Day 3]"""
```

I added a `plain_summary` field and `plain_explanation` per item. These are what your demo audience will see by default; the regulatory citations become "show details."

### 3f. Create llm_service.py

This is the abstraction layer. Your application calls these functions; the functions internally route to whichever LLM is configured.

```python
"""
Model-agnostic LLM service.
Switch providers by changing LLM_PROVIDER in .env.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

if LLM_PROVIDER == "openai":
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a prompt to the configured LLM and returns the raw response text.
    Provider-agnostic. Switch backends by changing LLM_PROVIDER.
    """
    if LLM_PROVIDER == "openai":
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def analyse_prompt(user_prompt: str, detection_system_prompt: str) -> dict:
    """
    Runs detection on a user prompt. Returns parsed JSON dictionary.
    """
    raw_response = call_llm(detection_system_prompt, user_prompt)
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse LLM response",
            "raw_response": raw_response,
            "details": str(e)
        }
```

### 3g. Create app.py

This is your Flask application:

```python
"""
SAFE Tool Backend.
Run with: python app.py
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
```

### 3h. Test the backend

With your venv still active:

```bash
python app.py
```

You should see Flask startup output indicating it's running on port 5001.

Open a new terminal window (don't close the one running Flask) and test the health check:

```bash
curl http://localhost:5001/api/health
```

You should get back: `{"status": "ok", "service": "safe-tool-backend"}`

Now test the analyse endpoint with a real prompt:

```bash
curl -X POST http://localhost:5001/api/analyse \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Help me draft a portfolio review for our client Anand Sharma, account WM-44721. His AUM is 18.5 crores."}'
```

You should get back a JSON response with risk score, items flagged, and combinatorial notes. If you do, your backend is working.

If you get errors, the most likely causes are: API key wrong in .env, virtual environment not activated, or OpenAI account out of credits.

---

## Step 4: Set Up the React Frontend

Open a second terminal window. Don't shut down the backend.

### 4a. Navigate back to project root and create frontend

```bash
cd /Users/manan/Desktop/PerniciaAI/TrainingTopics/ResponsibleAI/tool
npm create vite@latest frontend -- --template react
cd frontend
npm install
```

### 4b. Update src/App.jsx

Replace the contents of `src/App.jsx` with this minimal starter:

```jsx
import { useState } from 'react';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyse = async () => {
    if (!prompt.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await fetch('http://localhost:5001/api/analyse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Analysis failed');
      }
      
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '40px auto', padding: '0 20px', fontFamily: 'system-ui, sans-serif' }}>
      <h1>SAFE Prompt Checker</h1>
      <p style={{ color: '#666' }}>
        Paste a work prompt below. The tool will identify sensitive data 
        before you send it to any external AI system. 
        Your prompt is analysed and immediately discarded — nothing is stored.
      </p>
      
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Paste your prompt here..."
        rows={8}
        style={{ 
          width: '100%', 
          padding: 12, 
          fontSize: 14, 
          fontFamily: 'inherit',
          border: '1px solid #ccc',
          borderRadius: 4
        }}
      />
      
      <button
        onClick={handleAnalyse}
        disabled={loading || !prompt.trim()}
        style={{
          marginTop: 12,
          padding: '12px 24px',
          fontSize: 16,
          backgroundColor: '#0066cc',
          color: 'white',
          border: 'none',
          borderRadius: 4,
          cursor: loading ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? 'Analysing...' : 'Check My Prompt'}
      </button>
      
      {error && (
        <div style={{ marginTop: 20, padding: 12, backgroundColor: '#fee', color: '#900', borderRadius: 4 }}>
          Error: {error}
        </div>
      )}
      
      {result && (
        <div style={{ marginTop: 30 }}>
          <h2>Analysis Results</h2>
          <p><strong>Risk Score:</strong> {result.overall_risk_score}/10</p>
          <p><strong>Items Flagged:</strong> {result.total_items_flagged}</p>
          {result.plain_summary && (
            <p style={{ padding: 12, backgroundColor: '#f0f7ff', borderRadius: 4 }}>
              {result.plain_summary}
            </p>
          )}
          
          {result.items && result.items.length > 0 && (
            <div>
              <h3>What we found:</h3>
              <ul>
                {result.items.map(item => (
                  <li key={item.id} style={{ marginBottom: 12 }}>
                    <strong>{item.category}:</strong> "{item.excerpt}"
                    <br />
                    <em style={{ color: '#666' }}>{item.plain_explanation || item.regulatory_basis}</em>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {result.combinatorial_notes && (
            <div style={{ marginTop: 20, padding: 12, backgroundColor: '#fff8e1', borderRadius: 4 }}>
              <strong>Combined risk notes:</strong>
              <p>{result.combinatorial_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
```

### 4c. Run the frontend

```bash
npm run dev
```

You should see Vite startup output telling you the app is running at `http://localhost:5173`. Open that URL in your browser.

You should see the SAFE Prompt Checker interface. Paste in a test prompt — try one from our test set — and click Check My Prompt. Within a few seconds you should see the analysis results.

---

## Step 5: Verify End-to-End

A successful Day 1 looks like this:

1. Backend running on port 5001 in one terminal
2. Frontend running on port 5173 in another terminal
3. Browser open to `http://localhost:5173`
4. You paste a test prompt and the analysis comes back with risk score, items flagged, plain summary, and combinatorial notes

If all of that works, you've completed Day 1. The plumbing exists. The detection works through your code, not just through a chat interface.

---

## What's Next (Days 2 and 3)

**Day 2** — Improve the detection layer. Currently the prompts.py has a slightly compressed version of the detection prompt. We'll restore full category definitions and tune the output format. We'll also add error handling for cases where OpenAI returns malformed JSON.

**Day 3** — Build the rewriter. This is the missing piece of the SAFE pipeline. I'll draft the rewriter system prompt, you add the endpoint, and we wire it up so the frontend shows both the detection AND the sanitised rewrite.

---

## Common Issues and Fixes

**"command not found: python3"** — Install Python from python.org or via Homebrew (`brew install python3`).

**"command not found: npm"** — Install Node.js from nodejs.org. Use the LTS version.

**OpenAI API errors about invalid key** — Check `.env` has the correct key, no extra spaces or quotes around the value.

**OpenAI errors about rate limits or quota** — You've used up your $5 credit. Top up in OpenAI Console.

**CORS errors in browser console** — flask-cors is installed and CORS(app) is in app.py. Restart the backend.

**Backend port 5001 already in use** — Change the port in app.py (e.g. to 5002) and update the URL in App.jsx accordingly. macOS sometimes has AirPlay using 5000, which is why we used 5001.

**JSON parse errors from OpenAI** — Sometimes the model returns malformed JSON. The `response_format={"type": "json_object"}` parameter forces JSON mode and prevents most of these. If they persist, we can add retry logic on Day 2.

---

## What This Setup Gives You

You now have a clean, professional project structure that demonstrates good engineering practice:

- Separation of concerns (frontend, backend, prompts, LLM service)
- Model-agnostic abstraction (swap providers in one place)
- Environment-based configuration (no hard-coded keys)
- Versioned system prompts (track refinements)
- Git-tracked from day one
- Standard tooling (Flask, Vite, React) that any developer recognises

When you eventually pitch this to corporate training clients or showcase it on LinkedIn, the codebase itself is part of the credibility. This is what a Responsible AI tool looks like, built properly.
