import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';

import App from './App';
import { AuthProvider } from './contexts/AuthContext';

import './index.css';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'mock-google-client-id.apps.googleusercontent.com';
if (!import.meta.env.VITE_GOOGLE_CLIENT_ID) {
  console.warn("VITE_GOOGLE_CLIENT_ID is not defined in the environment. Using fallback client ID for local development.");
}

createRoot(document.getElementById('root')!).render(
  <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </GoogleOAuthProvider>
);
