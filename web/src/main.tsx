import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { RouterProvider } from 'react-router-dom'
import router from './routes'
import { LocaleProvider } from './contexts/LocaleContext'
import { ThemeProvider } from './contexts/ThemeContext'

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <LocaleProvider>
            <ThemeProvider>
                <RouterProvider router={router} />
            </ThemeProvider>
        </LocaleProvider>
    </StrictMode>,
)
