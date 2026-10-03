import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App'
import './index.css'

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

if (!googleClientId) {
  console.error("VITE_GOOGLE_CLIENT_ID is missing");
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={googleClientId ?? ''}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>,
)
