import React, { useState } from 'react';
import ResumeUploader from './components/ResumeUploader';
import TemplateSelector from './components/TemplateSelector';
import TypstPreview from './components/TypstPreview';
import ExportPDFButton from './components/ExportPDFButton';
import { processTypst, compileTypst } from './api';

const TEMPLATES = [
  { id: 1, name: 'Modern' },
  { id: 2, name: 'Classic' },
  { id: 3, name: 'Minimal' },
];

function App() {
  const [file, setFile] = useState(null);
  const [templateId, setTemplateId] = useState(1);
  const [typst, setTypst] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleGenerate() {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const res = await processTypst(file, templateId);
      if (res.data.success && res.data.typst_resume && typeof res.data.typst_resume === 'string' && res.data.typst_resume.trim() !== '') {
        setTypst(res.data.typst_resume);
      } else {
        setTypst('');
        setError(res.data.error || 'Failed to generate Typst resume');
        console.error('Typst generation error:', res.data.error || res.data);
      }
    } catch (e) {
      setTypst('');
      setError('API error: ' + e.message);
      console.error('Typst generation exception:', e);
    }
    setLoading(false);
  }

  async function handleExportPDF(typstContent) {
    if (!typstContent || typeof typstContent !== 'string' || typstContent.trim() === '') {
      setError('No Typst content to export.');
      console.error('ExportPDF called with empty Typst content:', typstContent);
      return;
    }
    setLoading(true);
    setError('');
    console.log('ExportPDF called with typstContent:', typstContent);
    try {
      const res = await compileTypst(typstContent);
      console.log('ExportPDF response:', res);
      if (res.data.success && res.data.pdf_path) {
        window.open(res.data.pdf_path, '_blank');
      } else {
        setError(res.data.error || 'Failed to export PDF');
        console.error('ExportPDF error:', res.data.error || res.data);
      }
    } catch (e) {
      setError('API error: ' + e.message);
      console.error('ExportPDF exception:', e);
    }
    setLoading(false);
  }

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', padding: 24, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px #eee' }}>
      <h2>Resume to Typst Converter</h2>
      <ResumeUploader onFileSelected={setFile} />
      <TemplateSelector value={templateId} onChange={setTemplateId} templates={TEMPLATES} />
      <button onClick={handleGenerate} disabled={!file || loading} style={{ marginTop: 16 }}>
        {loading ? 'Generating...' : 'Generate Typst Resume'}
      </button>
      {error && <div style={{ color: 'red', marginTop: 12 }}>{error}</div>}
      {typst && <TypstPreview typst={typst} />}
      <ExportPDFButton typst={typst} disabled={!typst || loading} onExport={handleExportPDF} />
    </div>
  );
}

export default App;
