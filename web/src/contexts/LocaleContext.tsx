/**
 * 国际化上下文管理
 * 
 * 支持中文和英文两种语言
 * 使用 localStorage 持久化用户的语言偏好
 */
import { createContext, useContext, useState, type ReactNode } from 'react'
import type { Locale } from 'antd/es/locale'
import zhCN from 'antd/locale/zh_CN'
import enUS from 'antd/locale/en_US'

export type LocaleType = 'zh-CN' | 'en-US'

interface LocaleContextType {
    locale: LocaleType
    setLocale: (locale: LocaleType) => void
    antdLocale: Locale
    t: (zhText: string, enText: string) => string
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined)

const LOCALE_STORAGE_KEY = 'aiRouter-locale'

// Ant Design locale 映射
const antdLocaleMap: Record<LocaleType, Locale> = {
    'zh-CN': zhCN,
    'en-US': enUS,
}

/**
 * 国际化提供者组件
 */
export const LocaleProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    // 从 localStorage 读取保存的语言设置，默认为中文
    const [locale, setLocaleState] = useState<LocaleType>(() => {
        const saved = localStorage.getItem(LOCALE_STORAGE_KEY)
        return (saved as LocaleType) || 'zh-CN'
    })

    /**
     * 设置语言并保存到 localStorage
     */
    const setLocale = (newLocale: LocaleType) => {
        setLocaleState(newLocale)
        localStorage.setItem(LOCALE_STORAGE_KEY, newLocale)
    }

    /**
     * 简单的翻译函数
     * @param zhText 中文文本
     * @param enText 英文文本
     */
    const t = (zhText: string, enText: string): string => {
        return locale === 'zh-CN' ? zhText : enText
    }

    return (
        <LocaleContext.Provider
            value={{
                locale,
                setLocale,
                antdLocale: antdLocaleMap[locale],
                t,
            }}
        >
            {children}
        </LocaleContext.Provider>
    )
}

/**
 * 使用国际化的 Hook
 */
export const useLocale = () => {
    const context = useContext(LocaleContext)
    if (!context) {
        throw new Error('useLocale must be used within LocaleProvider')
    }
    return context
}

