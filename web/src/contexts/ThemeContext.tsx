/**
 * 主题上下文管理
 * 
 * 提供亮色、暗色、跟随系统三种主题模式
 * 使用 localStorage 持久化用户的主题偏好
 */
import { createContext, useContext, useEffect, useState } from 'react'
import { ConfigProvider, theme as antdTheme } from 'antd'
import zhCN from 'antd/locale/zh_CN'

type ThemeMode = 'light' | 'dark' | 'auto'

interface ThemeContextType {
    mode: ThemeMode
    setMode: (mode: ThemeMode) => void
    isDark: boolean
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const THEME_STORAGE_KEY = 'aiRouter-theme-mode'

/**
 * 检测系统主题偏好
 */
const getSystemTheme = (): 'light' | 'dark' => {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark'
    }
    return 'light'
}

/**
 * 主题提供者组件
 */
export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    // 从 localStorage 读取保存的主题设置，默认为 auto
    const [mode, setModeState] = useState<ThemeMode>(() => {
        const saved = localStorage.getItem(THEME_STORAGE_KEY)
        return (saved as ThemeMode) || 'auto'
    })

    const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(getSystemTheme())

    // 计算实际应该使用的主题
    const isDark = mode === 'auto' ? systemTheme === 'dark' : mode === 'dark'

    /**
     * 监听系统主题变化
     */
    useEffect(() => {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

        const handleChange = (e: MediaQueryListEvent) => {
            setSystemTheme(e.matches ? 'dark' : 'light')
        }

        // 添加监听器
        mediaQuery.addEventListener('change', handleChange)

        return () => {
            mediaQuery.removeEventListener('change', handleChange)
        }
    }, [])

    /**
     * 设置主题模式并保存到 localStorage
     */
    const setMode = (newMode: ThemeMode) => {
        setModeState(newMode)
        localStorage.setItem(THEME_STORAGE_KEY, newMode)
    }

    return (
        <ThemeContext.Provider value={{ mode, setMode, isDark }}>
            <ConfigProvider
                locale={zhCN}
                theme={{
                    algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
                    token: {
                        colorPrimary: '#1677ff',
                        borderRadius: 6,
                    },
                }}
            >
                {children}
            </ConfigProvider>
        </ThemeContext.Provider>
    )
}

/**
 * 使用主题的 Hook
 */
export const useTheme = () => {
    const context = useContext(ThemeContext)
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider')
    }
    return context
}

