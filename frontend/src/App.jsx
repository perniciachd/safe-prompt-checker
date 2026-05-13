import { useState } from 'react';
import './App.css';

const LEVEL_ORDER = ['conservative', 'balanced', 'minimal'];

function App() {
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [rewriteLoading, setRewriteLoading] = useState(false);
  const [rewriteResult, setRewriteResult] = useState(null);
  const [rewriteError, setRewriteError] = useState(null);
  const [activeTab, setActiveTab] = useState('balanced');
  const [showCraft, setShowCraft] = useState(false);
  const [copiedLevel, setCopiedLevel] = useState(null);

  const handleAnalyse = async () => {
    if (!prompt.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setRewriteResult(null);
    setRewriteError(null);

    try {
      const response = await fetch('/api/analyse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
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

  const handleRewrite = async () => {
    if (!result || !prompt.trim()) return;

    setRewriteLoading(true);
    setRewriteError(null);
    setRewriteResult(null);

    try {
      const response = await fetch('/api/rewrite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, detection_result: result }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Rewrite failed');
      }

      const data = await response.json();
      setRewriteResult(data);

      const balanced = data.rewrites?.find((r) => r.level === 'balanced');
      setActiveTab(balanced ? 'balanced' : data.rewrites?.[0]?.level || 'balanced');
    } catch (err) {
      setRewriteError(err.message);
    } finally {
      setRewriteLoading(false);
    }
  };

  const handleCopy = async (level, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedLevel(level);
      setTimeout(() => setCopiedLevel(null), 2000);
    } catch (err) {
      console.error('Copy failed', err);
    }
  };

  const itemsFlagged = result?.total_items_flagged ?? 0;
  const hasFlags = itemsFlagged > 0;

  const activeRewrite = rewriteResult?.rewrites
    ?.slice()
    .sort((a, b) => LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level))
    .find((r) => r.level === activeTab);

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
          borderRadius: 4,
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
          cursor: loading ? 'not-allowed' : 'pointer',
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
          <p><strong>Items Flagged:</strong> {itemsFlagged}</p>
          {result.plain_summary && (
            <p style={{ padding: 12, backgroundColor: '#f0f7ff', borderRadius: 4 }}>
              {result.plain_summary}
            </p>
          )}

          {result.items && result.items.length > 0 && (
            <div>
              <h3>What we found:</h3>
              <ul>
                {result.items.map((item) => (
                  <li key={item.id} style={{ marginBottom: 12 }}>
                    <strong>{item.category}:</strong> "{item.excerpt}"
                    <br />
                    <em style={{ color: '#666' }}>{item.plain_explanation || item.rationale || item.regulatory_basis}</em>
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

          {!hasFlags && !result.combinatorial_notes && (
            <div style={{ marginTop: 24, padding: 16, backgroundColor: '#e8f5e9', color: '#1b5e20', borderRadius: 4, border: '1px solid #a5d6a7' }}>
              <strong>This prompt is safe to use as-is.</strong>
              <p style={{ margin: '6px 0 0' }}>
                No sensitive data was detected. You can submit this prompt to external AI systems without changes.
              </p>
            </div>
          )}

          {(hasFlags || result.combinatorial_notes) && (
            <div style={{ marginTop: 24 }}>
              <button
                onClick={handleRewrite}
                disabled={rewriteLoading}
                style={{
                  padding: '12px 24px',
                  fontSize: 16,
                  backgroundColor: '#2e7d32',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: rewriteLoading ? 'not-allowed' : 'pointer',
                }}
              >
                {rewriteLoading ? 'Generating recommendations...' : 'Generate Safe Prompt Recommendations'}
              </button>
              <p style={{ marginTop: 8, fontSize: 13, color: '#666' }}>
                Uses the CRAFT framework (Context, Role, Action, Format, Tone) to produce three sanitised rewrites.
              </p>
            </div>
          )}

          {rewriteError && (
            <div style={{ marginTop: 16, padding: 12, backgroundColor: '#fee', color: '#900', borderRadius: 4 }}>
              Error: {rewriteError}
            </div>
          )}

          {rewriteResult?.rewrites?.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <h2>Recommended Safe Prompts</h2>
              <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid #ddd', marginBottom: 16 }}>
                {rewriteResult.rewrites
                  .slice()
                  .sort((a, b) => LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level))
                  .map((rewrite) => {
                    const isActive = rewrite.level === activeTab;
                    return (
                      <button
                        key={rewrite.level}
                        onClick={() => setActiveTab(rewrite.level)}
                        style={{
                          padding: '8px 16px',
                          fontSize: 14,
                          backgroundColor: isActive ? '#0066cc' : 'transparent',
                          color: isActive ? 'white' : '#333',
                          border: 'none',
                          borderBottom: isActive ? '3px solid #0066cc' : '3px solid transparent',
                          borderRadius: '4px 4px 0 0',
                          cursor: 'pointer',
                          fontWeight: isActive ? 600 : 400,
                        }}
                      >
                        {rewrite.label}
                      </button>
                    );
                  })}
              </div>

              {activeRewrite && (
                <div>
                  <p style={{ color: '#444', marginBottom: 12 }}>{activeRewrite.explanation}</p>

                  {activeRewrite.external_use_warning && (
                    <div style={{ padding: 12, backgroundColor: '#fff3e0', color: '#7b3f00', borderRadius: 4, marginBottom: 12, border: '1px solid #ffcc80' }}>
                      <strong>Warning:</strong> {activeRewrite.external_use_warning}
                    </div>
                  )}

                  {Array.isArray(activeRewrite.items_sanitised) && activeRewrite.items_sanitised.length > 0 && (
                    <p style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>
                      Sanitised {activeRewrite.items_sanitised.length} of {itemsFlagged} flagged items
                      (ids: {activeRewrite.items_sanitised.join(', ')}).
                    </p>
                  )}

                  <button
                    onClick={() => setShowCraft(!showCraft)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#0066cc',
                      cursor: 'pointer',
                      padding: 0,
                      fontSize: 14,
                      marginBottom: 12,
                    }}
                  >
                    {showCraft ? '▼ Hide CRAFT breakdown' : '▶ Show CRAFT breakdown'}
                  </button>

                  {showCraft && activeRewrite.craft_breakdown && (
                    <div style={{ padding: 12, backgroundColor: '#f5f5f5', borderRadius: 4, marginBottom: 12, fontSize: 14 }}>
                      <p style={{ margin: '4px 0' }}><strong>Context:</strong> {activeRewrite.craft_breakdown.context}</p>
                      <p style={{ margin: '4px 0' }}><strong>Role:</strong> {activeRewrite.craft_breakdown.role}</p>
                      <p style={{ margin: '4px 0' }}><strong>Action:</strong> {activeRewrite.craft_breakdown.action}</p>
                      <p style={{ margin: '4px 0' }}><strong>Format:</strong> {activeRewrite.craft_breakdown.format}</p>
                      <p style={{ margin: '4px 0' }}><strong>Tone:</strong> {activeRewrite.craft_breakdown.tone}</p>
                    </div>
                  )}

                  <div style={{ position: 'relative' }}>
                    <pre
                      style={{
                        padding: 16,
                        backgroundColor: '#f8f9fa',
                        border: '1px solid #e0e0e0',
                        borderRadius: 4,
                        whiteSpace: 'pre-wrap',
                        wordWrap: 'break-word',
                        fontFamily: 'inherit',
                        fontSize: 14,
                        lineHeight: 1.5,
                        margin: 0,
                      }}
                    >
                      {activeRewrite.rewritten_prompt}
                    </pre>
                    <button
                      onClick={() => handleCopy(activeRewrite.level, activeRewrite.rewritten_prompt)}
                      style={{
                        position: 'absolute',
                        top: 8,
                        right: 8,
                        padding: '6px 12px',
                        fontSize: 13,
                        backgroundColor: copiedLevel === activeRewrite.level ? '#2e7d32' : '#fff',
                        color: copiedLevel === activeRewrite.level ? 'white' : '#333',
                        border: '1px solid #ccc',
                        borderRadius: 4,
                        cursor: 'pointer',
                      }}
                    >
                      {copiedLevel === activeRewrite.level ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
