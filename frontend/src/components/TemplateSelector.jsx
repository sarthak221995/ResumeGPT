import React from 'react';

export default function TemplateSelector({ value, onChange, templates }) {
  return (
    <div>
      <label htmlFor="template-select">Select Template:</label>
      <select id="template-select" value={value} onChange={e => onChange(Number(e.target.value))}>
        {templates.map(t => (
          <option key={t.id} value={t.id}>{t.name}</option>
        ))}
      </select>
    </div>
  );
}
