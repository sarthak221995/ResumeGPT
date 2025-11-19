import React from 'react';

export default function TypstPreview({ typst }) {
  return (
    <div style={{ marginTop: 20 }}>
      <h3>Typst Resume Preview</h3>
      <pre style={{ background: '#f4f4f4', padding: 16, maxHeight: 400, overflow: 'auto' }}>{typst}</pre>
    </div>
  );
}
