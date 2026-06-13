import React from 'react'
import ReactDOM from 'react-dom/client'
import LeafyGreenProvider from '@leafygreen-ui/leafygreen-provider'
import App from './App.jsx'
import './styles.css'

// LeafyGreenProvider with darkMode — authentic MongoDB Atlas look
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LeafyGreenProvider darkMode>
      <App />
    </LeafyGreenProvider>
  </React.StrictMode>,
)
