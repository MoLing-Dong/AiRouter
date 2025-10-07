import React from 'react'
import { useTranslation } from '@/hooks/useTranslation'

const SettingsPage: React.FC = () => {
    const { t } = useTranslation('menu')

    return (
        <div className="page">
            <h1>{t('settings')}</h1>
            <p>Configuration page coming soon...</p>
        </div>
    )
}

export default SettingsPage

