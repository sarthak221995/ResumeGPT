import React, { useState } from 'react';

export default function ResumeUploader({ onFileSelected }) {
  const [file, setFile] = useState(null);

  function handleChange(e) {
    const selected = e.target.files[0];
    setFile(selected);
    onFileSelected(selected);
  }

  return (
    <div>
      <label htmlFor="resume-upload">Upload Resume (PDF):</label>
      <input
        id="resume-upload"
        type="file"
        accept=".pdf"
        onChange={handleChange}
      />
    </div>
  );
}
