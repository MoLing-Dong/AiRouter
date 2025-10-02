import type { CSSProperties } from 'react'
import { Layout, Menu, type MenuProps, theme, Dropdown, Button } from 'antd'
import { Link, Outlet, useLocation } from 'react-router-dom'
import {
    DashboardOutlined,
    ApiOutlined,
    CloudServerOutlined,
    SettingOutlined,
    ThunderboltOutlined,
    SunOutlined,
    MoonOutlined,
    DesktopOutlined,
} from '@ant-design/icons'
import { useTheme } from '@/contexts/ThemeContext'

const { Header, Sider, Content, Footer } = Layout

/**
 * 导航菜单配置
 * 每个菜单项包含唯一标识、显示文本、路由路径和图标
 */
const navItems = [
    { key: 'dashboard', label: '控制台总览', path: '/', icon: <DashboardOutlined /> },
    { key: 'models', label: '模型管理', path: '/models', icon: <ApiOutlined /> },
    { key: 'providers', label: '供应商管理', path: '/providers', icon: <CloudServerOutlined /> },
    { key: 'settings', label: '系统设置', path: '/settings', icon: <SettingOutlined /> },
]

/**
 * 生成菜单项配置
 * 包含图标和链接，折叠时自动只显示图标
 */
const menuItems: MenuProps['items'] = navItems.map((item) => ({
    key: item.key,
    icon: item.icon,
    label: <Link to={item.path}>{item.label}</Link>,
}))

const AppLayout = () => {
    const location = useLocation()
    const { token } = theme.useToken()
    const [collapsed, setCollapsed] = useState(false)
    const { mode, setMode } = useTheme()

    const headerStyle: CSSProperties = {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 64,
        fontSize: 18,
        fontWeight: 600,
        color: token.colorTextLightSolid,
        backgroundColor: token.colorPrimary,
        paddingInline: 24,
    }

    // 主题切换菜单配置
    const themeMenuItems = [
        {
            key: 'light',
            icon: <SunOutlined />,
            label: '亮色模式',
            onClick: () => setMode('light'),
        },
        {
            key: 'dark',
            icon: <MoonOutlined />,
            label: '暗色模式',
            onClick: () => setMode('dark'),
        },
        {
            key: 'auto',
            icon: <DesktopOutlined />,
            label: '跟随系统',
            onClick: () => setMode('auto'),
        },
    ]

    // 根据当前模式显示对应的图标
    const themeIcon = mode === 'light'
        ? <SunOutlined />
        : mode === 'dark'
            ? <MoonOutlined />
            : <DesktopOutlined />

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
        justifyContent: 'center',
        paddingInline: 16,
        fontWeight: 600,
        fontSize: 20,
        color: token.colorTextLightSolid,
        gap: 8,
    }

    const activeKey = navItems.find((item) => {
        if (item.path === '/') {
            return location.pathname === '/'
        }
        return location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)
    })?.key

    return (
        <Layout style={{ height: '100vh' }}>
            <Sider
                style={siderStyle}
                collapsible
                collapsed={collapsed}
                onCollapse={(value) => setCollapsed(value)}
                width={180}
                theme="dark"
            >
                <div style={logoStyle}>
                    <ThunderboltOutlined style={{ fontSize: 24 }} />
                    {!collapsed && <span>AiRouter</span>}
                </div>
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={activeKey ? [activeKey] : ['dashboard']}
                    items={menuItems}
                />
            </Sider>
            <Layout>
                <Header style={headerStyle}>
                    <span>模型路由控制台</span>
                    <Dropdown menu={{ items: themeMenuItems, selectedKeys: [mode] }} placement="bottomRight">
                        <Button
                            type="text"
                            icon={themeIcon}
                            style={{ color: token.colorTextLightSolid }}
                        >
                            主题
                        </Button>
                    </Dropdown>
                </Header>
                <Content style={contentStyle}>
                    <Outlet />
                </Content>
                <Footer style={footerStyle}>AiRouter © {new Date().getFullYear()}</Footer>
            </Layout>
        </Layout>
    )
}

export default AppLayout

