import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import routes from 'virtual:generated-pages-react'
import { Layout } from 'antd'

const { Header, Footer, Sider, Content } = Layout

const headerStyle: React.CSSProperties = {
    color: '#fff',
    height: 64,
    paddingInline: 24,
    display: 'flex',
    alignItems: 'center',
    fontSize: 18,
    backgroundColor: '#4096ff',
}

const contentStyle: React.CSSProperties = {
    padding: 24,
    backgroundColor: '#f3f5f9',
    height: '100%',
    overflow: 'auto',
}

const siderStyle: React.CSSProperties = {
    backgroundColor: '#001529',
    color: '#fff',
    padding: '24px 16px',
}

const footerStyle: React.CSSProperties = {
    textAlign: 'center',
    color: 'rgba(0,0,0,0.45)',
    backgroundColor: '#f0f2f5',
    padding: 16,
}

const router = createBrowserRouter(routes)

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <Layout style={{ minHeight: '100vh' }}>
            <Sider width={240} style={siderStyle}>
                侧边导航
            </Sider>
            <Layout>
                <Header style={headerStyle}>模型路由控制台</Header>
                <Content style={contentStyle}>
                    <RouterProvider router={router} />
                </Content>
                <Footer style={footerStyle}>AiRouter © {new Date().getFullYear()}</Footer>
            </Layout>
        </Layout>
    </StrictMode>,
)
