import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { applyTheme } from './lib'

applyTheme()
// "system" follows the OS when it switches between light and dark
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => applyTheme())

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
