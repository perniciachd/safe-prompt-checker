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