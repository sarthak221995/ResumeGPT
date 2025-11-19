import React from 'react';

export default function ExportPDFButton({ typst, disabled, onExport }) {
  return (
    <button disabled={disabled} onClick={() => onExport(typst)} style={{ marginTop: 16 }}>
      Export to PDF
    </button>
  );
}
