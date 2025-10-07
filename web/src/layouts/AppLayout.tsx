import type { CSSProperties } from 'react'
import { Layout, Menu, type MenuProps, theme, Dropdown, Button, Space } from 'antd'
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
import { LocaleSwitcher } from '@/components/LocaleSwitcher'
import { useTranslation } from '@/hooks/useTranslation'

const { Header, Sider, Content, Footer } = Layout

/**
 * 导航菜单配置基础数据
 * 每个菜单项包含唯一标识、路由路径和图标
 */
const navItemsBase = [
    { key: 'dashboard', path: '/', icon: <DashboardOutlined />, labelKey: 'dashboard' },
    { key: 'models', path: '/models', icon: <ApiOutlined />, labelKey: 'models' },
    { key: 'providers', path: '/providers', icon: <CloudServerOutlined />, labelKey: 'providers' },
    { key: 'settings', path: '/settings', icon: <SettingOutlined />, labelKey: 'settings' },
]

const AppLayout = () => {
    const location = useLocation()
    const { token } = theme.useToken()
    const [collapsed, setCollapsed] = useState(false)
    const { mode, setMode } = useTheme()
    const { t: tMenu } = useTranslation('menu')
    const { t: tSettings } = useTranslation('settings')

    /**
     * 生成菜单项配置（动态翻译）
     * 包含图标和链接，折叠时自动只显示图标
     */
    const menuItems: MenuProps['items'] = navItemsBase.map((item) => ({
        key: item.key,
        icon: item.icon,
        label: <Link to={item.path}>{tMenu(item.labelKey)}</Link>,
    }))

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

    // 主题切换菜单配置（动态翻译）
    const themeMenuItems = [
        {
            key: 'light',
            icon: <SunOutlined />,
            label: tSettings('lightMode'),
            onClick: () => setMode('light'),
        },
        {
            key: 'dark',
            icon: <MoonOutlined />,
            label: tSettings('darkMode'),
            onClick: () => setMode('dark'),
        },
        {
            key: 'auto',
            icon: <DesktopOutlined />,
            label: tSettings('autoMode'),
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

    const activeKey = navItemsBase.find((item) => {
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
                    <span>AiRouter Console</span>
                    <Space>
                        <LocaleSwitcher />
                        <Dropdown menu={{ items: themeMenuItems, selectedKeys: [mode] }} placement="bottomRight">
                            <Button
                                type="text"
                                icon={themeIcon}
                                style={{ color: token.colorTextLightSolid }}
                            >
                                {tSettings('theme')}
                            </Button>
                        </Dropdown>
                    </Space>
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

