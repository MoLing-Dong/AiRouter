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
    Alert,
    Spin
} from 'antd'
import {
    ApiOutlined,
    DatabaseOutlined,
    CloudServerOutlined,
    CheckCircleOutlined
} from '@ant-design/icons'
import { statsApi, modelsApi, providersApi } from '@/services/api'
import { useTranslation } from '@/hooks/useTranslation'

interface SystemStats {
    activeModels: number
    healthyProviders: number
    averageResponseTime: number
}

const Dashboard: React.FC = () => {
    const { t: tDashboard } = useTranslation('dashboard')
    const { t: tCommon } = useTranslation('common')

    const [stats, setStats] = useState<SystemStats>({
        activeModels: 0,
        healthyProviders: 0,
        averageResponseTime: 0
    })
    const [recentModels, setRecentModels] = useState([])
    const [providerHealth, setProviderHealth] = useState([])
    const [loading, setLoading] = useState(true)

    const fetchDashboardData = async () => {
        setLoading(true)
        try {
            const [systemMetrics, models, providers] = await Promise.all([
                statsApi.getSystemMetrics().then((res) => res.data).catch(() => ({})),
                modelsApi.getDbModels().then((res) => {
                    return res.data
                }).catch(() => ({ models: [] })),
                providersApi.getProviders().then((res) => res.data).catch(() => ({ providers: [] }))
            ])

            // 计算统计数据
            const modelsData = (models as any)?.models || []
            const providersData = (providers as any)?.providers || []

            // 转换模型数据格式
            const formattedModels = modelsData.map((model: any) => ({
                id: model.id,
                name: model.name,
                provider: model.type === 'PUBLIC' ? 'public' : 'private',
                status: model.is_enabled ? 'active' : 'inactive'
            }))

            const activeModels = formattedModels.filter((m: any) => m.status === 'active')?.length || 0
            const healthyProviders = providersData.filter((p: any) => p.is_enabled)?.length || 0

            setStats({
                activeModels,
                healthyProviders,
                averageResponseTime: (systemMetrics as any)?.avg_response_time || 245
            })

            // 转换供应商数据格式用于显示
            const formattedProviders = providersData.map((provider: any) => ({
                id: provider.id,
                name: provider.name,
                health: 'unknown', // 该接口不提供健康检查信息
                responseTime: 0
            }))

            setRecentModels(formattedModels.slice(0, 5) || [])
            setProviderHealth(formattedProviders.slice(0, 5) || [])
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
        },
        {
            title: tDashboard('provider'),
            dataIndex: 'provider',
            key: 'provider',
            render: (provider: string) => provider === 'public' ? tDashboard('public') : tDashboard('private'),
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
        },
        {
            title: tDashboard('healthStatus'),
            dataIndex: 'health',
            key: 'health',
            render: (health: string) => (
                <Badge
                    status={health === 'healthy' ? 'success' : health === 'unhealthy' ? 'error' : 'warning'}
                    text={health === 'healthy' ? tDashboard('healthy') : health === 'unhealthy' ? tDashboard('unhealthy') : tCommon('unknown')}
                />
            )
        },
        {
            title: tCommon('responseTime'),
            dataIndex: 'responseTime',
            key: 'responseTime',
            render: (time: number) => time ? `${time}ms` : '-'
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
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title={tDashboard('activeModels')}
                            value={stats.activeModels}
                            prefix={<DatabaseOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title={tDashboard('healthyProviders')}
                            value={stats.healthyProviders}
                            prefix={<CloudServerOutlined />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* 详细信息 */}
            <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                    <Card title={tDashboard('recentModels')} size="small">
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
                    <Card title={tDashboard('providerHealth')} size="small">
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

            {/* 系统性能
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                <Col xs={24}>
                    <Card title="系统性能概览" size="small">
                        <Row gutter={[16, 16]}>
                            <Col xs={24} md={8}>
                                <div>
                                    <p>CPU 使用率</p>
                                    <Progress percent={65} status="active" />
                                </div>
                            </Col>
                            <Col xs={24} md={8}>
                                <div>
                                    <p>内存使用率</p>
                                    <Progress percent={45} />
                                </div>
                            </Col>
                            <Col xs={24} md={8}>
                                <div>
                                    <p>请求成功率</p>
                                    <Progress percent={98} status="success" />
                                </div>
                            </Col>
                        </Row>
                    </Card>
                </Col>
            </Row> */}
        </div>
    )
}

export default Dashboard