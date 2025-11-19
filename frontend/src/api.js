import axios from 'axios';

const BASE_URL = 'http://localhost:8000'; // Change if backend runs elsewhere

export async function processTypst(file, templateId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('template_id', templateId);
  return axios.post(`${BASE_URL}/process_typst`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export async function compileTypst(typstContent) {
  // Backend expects FormData with 'content' field (Form parameter)
  const formData = new FormData();
  formData.append('content', typstContent);
  
  return axios.post(`${BASE_URL}/compile-typst`, formData);
  // Note: axios automatically sets Content-Type to multipart/form-data for FormData
}