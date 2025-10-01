import type { CSSProperties } from 'react'
import { Layout, Menu, type MenuProps, theme } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'

const { Header, Sider, Content, Footer } = Layout

const navItems = [
    { key: 'dashboard', label: '控制台总览', path: '/' },
    { key: 'models', label: '模型管理', path: '/models' },
    { key: 'providers', label: '供应商管理', path: '/providers' },
    { key: 'settings', label: '系统设置', path: '/settings' },
]

const menuItems: MenuProps['items'] = navItems.map((item) => ({
    key: item.key,
    label: <Link to={item.path}>{item.label}</Link>,
}))

const AppLayout = () => {
    const location = useLocation()
    const { token } = theme.useToken()

    const headerStyle: CSSProperties = {
        display: 'flex',
        alignItems: 'center',
        height: 64,
        fontSize: 18,
        fontWeight: 600,
        color: token.colorTextLightSolid,
        backgroundColor: token.colorPrimary,
        paddingInline: 24,
    }

    const contentStyle: CSSProperties = {
        padding: 24,
        background: token.colorBgLayout,
        minHeight: 0,
        overflow: 'auto',
    }

    const footerStyle: CSSProperties = {
        textAlign: 'center',
        color: token.colorTextTertiary,
        background: token.colorBgLayout,
    }

    const siderStyle: CSSProperties = {
        height: '100vh',
        overflow: 'auto',
    }

    const logoStyle: CSSProperties = {
        height: 64,
        display: 'flex',
        alignItems: 'center',
        paddingInline: 16,
        fontWeight: 600,
        fontSize: 20,
        color: token.colorTextLightSolid,
    }

    const activeKey = navItems.find((item) => {
        if (item.path === '/') {
            return location.pathname === '/'
        }
        return location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)
    })?.key

    return (
        <Layout style={{ height: '100vh' }}>
            <Sider style={siderStyle} collapsible width={220} theme="dark">
                <div style={logoStyle}>AiRouter</div>
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={activeKey ? [activeKey] : ['dashboard']}
                    items={menuItems}
                />
            </Sider>
            <Layout>
                <Header style={headerStyle}>模型路由控制台</Header>
                <Content style={contentStyle}>
                    <Outlet />
                </Content>
                <Footer style={footerStyle}>AiRouter © {new Date().getFullYear()}</Footer>
            </Layout>
        </Layout>
    )
}

export default AppLayout

