import type { RouteObject } from 'react-router-dom'
import { createBrowserRouter } from 'react-router-dom'
import routes from 'virtual:generated-pages-react'
import AppLayout from '@/layouts/AppLayout'

const router = createBrowserRouter([
    {
        path: '/',
        element: <AppLayout />,
        children: routes as RouteObject[],
    },
])

export default router

