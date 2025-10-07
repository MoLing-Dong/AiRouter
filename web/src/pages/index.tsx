import React, { useState, useEffect } from 'react'
import {
    Row,
    Col,
    Card,
    Statistic,
    Table,
    Progress,
    Tag,
    Badge,
    Spin,
    Space,
    Tooltip
} from 'antd'
import {
    ApiOutlined,
    DatabaseOutlined,
    CloudServerOutlined,
    WarningOutlined
} from '@ant-design/icons'
import { modelsApi } from '@/services/api'
import { useTranslation } from '@/hooks/useTranslation'

interface SystemStats {
    activeModels: number
    totalModels: number
    healthyProviders: number
    totalProviders: number
    degradedProviders: number
    unhealthyProviders: number
    averageResponseTime: number
    totalModelProviderPairs: number
}

const Dashboard: React.FC = () => {
    const { t: tDashboard } = useTranslation('dashboard')
    const { t: tCommon } = useTranslation('common')

    const [stats, setStats] = useState<SystemStats>({
        activeModels: 0,
        totalModels: 0,
        healthyProviders: 0,
        totalProviders: 0,
        degradedProviders: 0,
        unhealthyProviders: 0,
        averageResponseTime: 0,
        totalModelProviderPairs: 0
    })
    const [recentModels, setRecentModels] = useState<any[]>([])
    const [providerHealth, setProviderHealth] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    const fetchDashboardData = async () => {
        setLoading(true)
        try {
            // 获取模型数据（包含供应商健康状态）
            const modelsResponse = await modelsApi.getDbModels(1, 100).catch(() => ({ data: { models: [] } }))
            const modelsData = (modelsResponse as any)?.data?.models || []

            // 统计供应商健康状态（从模型的供应商中聚合）
            const providerHealthMap = new Map<string, {
                id: number
                name: string
                healthStatuses: string[]
                responseTimes: number[]
                modelCount: number
            }>()

            // 遍历所有模型的供应商
            modelsData.forEach((model: any) => {
                model.providers?.forEach((provider: any) => {
                    const key = `${provider.id}-${provider.name}`
                    if (!providerHealthMap.has(key)) {
                        providerHealthMap.set(key, {
                            id: provider.id,
                            name: provider.name,
                            healthStatuses: [],
                            responseTimes: [],
                            modelCount: 0
                        })
                    }
                    const providerData = providerHealthMap.get(key)!
                    providerData.healthStatuses.push(provider.health_status || 'unknown')
                    providerData.modelCount++
                })
            })

            // 计算每个供应商的整体健康状态
            const providerHealthData = Array.from(providerHealthMap.values()).map(provider => {
                const healthCounts = {
                    healthy: provider.healthStatuses.filter(s => s === 'healthy').length,
                    degraded: provider.healthStatuses.filter(s => s === 'degraded').length,
                    unhealthy: provider.healthStatuses.filter(s => s === 'unhealthy').length,
                    unknown: provider.healthStatuses.filter(s => s === 'unknown').length
                }

                // 确定整体健康状态：如果有任何unhealthy就是unhealthy，否则如果有degraded就是degraded
                let overallHealth = 'healthy'
                if (healthCounts.unhealthy > 0) {
                    overallHealth = 'unhealthy'
                } else if (healthCounts.degraded > 0) {
                    overallHealth = 'degraded'
                } else if (healthCounts.unknown === provider.healthStatuses.length) {
                    overallHealth = 'unknown'
                }

                return {
                    id: provider.id,
                    name: provider.name,
                    health: overallHealth,
                    modelCount: provider.modelCount,
                    healthDetails: healthCounts
                }
            })

            // 计算统计数据
            const totalModels = modelsData.length
            const activeModels = modelsData.filter((m: any) => m.is_enabled).length
            const totalProviders = providerHealthData.length
            const healthyProviders = providerHealthData.filter(p => p.health === 'healthy').length
            const degradedProviders = providerHealthData.filter(p => p.health === 'degraded').length
            const unhealthyProviders = providerHealthData.filter(p => p.health === 'unhealthy').length
            const totalModelProviderPairs = modelsData.reduce((sum: number, model: any) =>
                sum + (model.providers?.length || 0), 0)

            setStats({
                activeModels,
                totalModels,
                healthyProviders,
                totalProviders,
                degradedProviders,
                unhealthyProviders,
                averageResponseTime: 245, // TODO: 从实际监控数据获取
                totalModelProviderPairs
            })

            // 准备最近的模型数据（显示供应商信息）
            const formattedModels = modelsData.slice(0, 5).map((model: any) => ({
                id: model.id,
                name: model.name,
                type: model.type,
                providers: model.providers || [],
                status: model.is_enabled ? 'active' : 'inactive'
            }))

            setRecentModels(formattedModels)
            setProviderHealth(providerHealthData.slice(0, 5))
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error)
        } finally {
            setLoading(false)
        }
    }

    const modelColumns = [
        {
            title: tDashboard('modelName'),
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>
        },
        {
            title: tDashboard('provider'),
            dataIndex: 'providers',
            key: 'providers',
            render: (providers: any[]) => (
                <Space wrap size="small">
                    {providers && providers.length > 0 ? (
                        providers.map((p: any, idx: number) => (
                            <Tooltip
                                key={`${p.id}-${idx}`}
                                title={`${p.name}: ${p.health_status || 'unknown'}`}
                            >
                                <Tag
                                    color={
                                        p.health_status === 'healthy' ? 'success' :
                                            p.health_status === 'degraded' ? 'warning' :
                                                p.health_status === 'unhealthy' ? 'error' : 'default'
                                    }
                                    style={{ margin: 0 }}
                                >
                                    {p.name}
                                    {p.is_preferred && ' ⭐'}
                                </Tag>
                            </Tooltip>
                        ))
                    ) : (
                        <Tag color="default">-</Tag>
                    )}
                </Space>
            )
        },
        {
            title: tCommon('status'),
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => (
                <Tag color={status === 'active' ? 'green' : 'red'}>
                    {status === 'active' ? tCommon('enabled') : tCommon('disabled')}
                </Tag>
            )
        }
    ]

    const providerColumns = [
        {
            title: tDashboard('provider'),
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>
        },
        {
            title: tDashboard('healthStatus'),
            dataIndex: 'health',
            key: 'health',
            render: (health: string) => {
                const getColor = () => {
                    if (health === 'healthy') return 'success'
                    if (health === 'degraded') return 'warning'
                    if (health === 'unhealthy') return 'error'
                    return 'default'
                }
                const getText = () => {
                    if (health === 'healthy') return tDashboard('healthy')
                    if (health === 'unhealthy') return tDashboard('unhealthy')
                    if (health === 'degraded') return tCommon('degraded')
                    return tCommon('unknown')
                }
                return <Badge status={getColor()} text={getText()} />
            }
        },
        {
            title: tCommon('models'),
            dataIndex: 'modelCount',
            key: 'modelCount',
            render: (count: number) => (
                <Tooltip title={`${tCommon('servingModels')}: ${count}`}>
                    <Tag color="blue">{count} {tCommon('models')}</Tag>
                </Tooltip>
            )
        },
        {
            title: tCommon('details'),
            dataIndex: 'healthDetails',
            key: 'healthDetails',
            render: (details: any) => (
                <Space size="small" wrap>
                    {details.healthy > 0 && (
                        <Tag color="success">
                            {details.healthy} {tDashboard('healthy')}
                        </Tag>
                    )}
                    {details.degraded > 0 && (
                        <Tag color="warning">
                            {details.degraded} {tCommon('degraded')}
                        </Tag>
                    )}
                    {details.unhealthy > 0 && (
                        <Tag color="error">
                            {details.unhealthy} {tDashboard('unhealthy')}
                        </Tag>
                    )}
                    {details.unknown > 0 && (
                        <Tag color="default">
                            {details.unknown} {tCommon('unknown')}
                        </Tag>
                    )}
                </Space>
            )
        }
    ]

    useEffect(() => {
        fetchDashboardData()
    }, [])

    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" />
            </div>
        )
    }

    return (
        <div>
            {/* 统计卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title={tDashboard('activeModels')}
                            value={stats.activeModels}
                            suffix={`/ ${stats.totalModels}`}
                            prefix={<DatabaseOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                        <Progress
                            percent={stats.totalModels > 0 ? Math.round((stats.activeModels / stats.totalModels) * 100) : 0}
                            size="small"
                            showInfo={false}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title={tDashboard('healthyProviders')}
                            value={stats.healthyProviders}
                            suffix={`/ ${stats.totalProviders}`}
                            prefix={<CloudServerOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                        <Progress
                            percent={stats.totalProviders > 0 ? Math.round((stats.healthyProviders / stats.totalProviders) * 100) : 0}
                            size="small"
                            showInfo={false}
                            strokeColor="#52c41a"
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title={tCommon('degraded')}
                            value={stats.degradedProviders}
                            prefix={<WarningOutlined />}
                            valueStyle={{ color: stats.degradedProviders > 0 ? '#faad14' : '#8c8c8c' }}
                        />
                        <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                            {tDashboard('unhealthy')}: {stats.unhealthyProviders}
                        </div>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title={tCommon('total') + ' ' + tDashboard('connections')}
                            value={stats.totalModelProviderPairs}
                            prefix={<ApiOutlined />}
                            valueStyle={{ color: '#1890ff' }}
                        />
                        <div style={{ marginTop: 8, fontSize: 12, color: '#8c8c8c' }}>
                            {tDashboard('modelProviderPairs')}
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* 详细信息 */}
            <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                    <Card
                        title={tDashboard('recentModels')}
                        size="small"
                        extra={
                            <Tag color="blue">
                                {tCommon('total')}: {stats.totalModels} {tCommon('models')}
                            </Tag>
                        }
                    >
                        <Table
                            columns={modelColumns}
                            dataSource={recentModels}
                            pagination={false}
                            size="small"
                            rowKey="id"
                        />
                    </Card>
                </Col>
                <Col xs={24} lg={12}>
                    <Card
                        title={tDashboard('providerHealth')}
                        size="small"
                        extra={
                            <Space size="small">
                                <Tag color="success">{stats.healthyProviders} {tDashboard('healthy')}</Tag>
                                {stats.degradedProviders > 0 && (
                                    <Tag color="warning">{stats.degradedProviders} {tCommon('degraded')}</Tag>
                                )}
                                {stats.unhealthyProviders > 0 && (
                                    <Tag color="error">{stats.unhealthyProviders} {tDashboard('unhealthy')}</Tag>
                                )}
                            </Space>
                        }
                    >
                        <Table
                            columns={providerColumns}
                            dataSource={providerHealth}
                            pagination={false}
                            size="small"
                            rowKey="id"
                        />
                    </Card>
                </Col>
            </Row>

        </div>
    )
}

export default Dashboard