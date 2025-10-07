/**
 * 语言切换组件
 * 
 * 提供中英文切换功能
 */
import { Dropdown, Button, theme } from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { useLocale } from '@/contexts/LocaleContext'
import type { MenuProps } from 'antd'

interface LocaleSwitcherProps {
    style?: React.CSSProperties
}

export const LocaleSwitcher: React.FC<LocaleSwitcherProps> = ({ style }) => {
    const { locale, setLocale } = useLocale()
    const { token } = theme.useToken()

    const items: MenuProps['items'] = [
        {
            key: 'zh-CN',
            label: '简体中文',
            onClick: () => setLocale('zh-CN'),
        },
        {
            key: 'en-US',
            label: 'English',
            onClick: () => setLocale('en-US'),
        },
    ]

    const currentLocaleLabel = locale === 'zh-CN' ? '简体中文' : 'English'

    return (
        <Dropdown menu={{ items, selectedKeys: [locale] }} placement="bottomRight">
            <Button
                type="text"
                icon={<GlobalOutlined />}
                style={style || { color: token.colorTextLightSolid }}
            >
                {currentLocaleLabel}
            </Button>
        </Dropdown>
    )
}

