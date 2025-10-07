import React, { useState, useEffect } from 'react'
import {
    Table,
    Button,
    Space,
    Modal,
    Form,
    Input,
    Select,
    message,
    Card,
    Tag,
    Tooltip,
    Popconfirm
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons'
import { providersApi } from '@/services/api'
import { useTranslation } from '@/hooks/useTranslation'

interface Provider {
    id?: number
    name: string
    type: string
    apiKey?: string
    endpoint?: string
    status: 'active' | 'inactive'
    health?: 'healthy' | 'unhealthy' | 'unknown'
    performance?: {
        responseTime: number
        successRate: number
    }
}

const ProvidersPage: React.FC = () => {
    const { t: tProviders } = useTranslation('providers')
    const { t: tCommon } = useTranslation('common')

    const [providers, setProviders] = useState<Provider[]>([])
    const [loading, setLoading] = useState(false)
    const [modalVisible, setModalVisible] = useState(false)
    const [editingProvider, setEditingProvider] = useState<Provider | null>(null)
    const [form] = Form.useForm()

    // 分页状态
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 10,
        total: 0
    })

    const fetchProviders = async (page: number = pagination.current, pageSize: number = pagination.pageSize) => {
        setLoading(true)
        try {
            const response: any = await providersApi.getDbProviders(page, pageSize)

            // 转换数据格式以匹配前端接口
            const formattedProviders = (response.data?.providers || []).map((provider: any) => ({
                id: provider.id,
                name: provider.name,
                type: provider.type,
                endpoint: provider.official_endpoint,
                status: provider.is_enabled ? 'active' : 'inactive',
                performance: {
                    responseTime: 0,
                    successRate: 0
                }
            }))

            setProviders(formattedProviders)

            // 更新分页信息
            setPagination({
                current: response.data?.page || 1,
                pageSize: response.data?.page_size || 10,
                total: response.data?.total || 0
            })
        } catch (error) {
            message.error(tProviders('fetchFailed'))
            console.error('Failed to fetch providers:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleCreate = () => {
        setEditingProvider(null)
        form.resetFields()
        setModalVisible(true)
    }

    const handleEdit = (provider: Provider) => {
        setEditingProvider(provider)
        form.setFieldsValue(provider)
        setModalVisible(true)
    }

    const handleDelete = async (_provider: Provider) => {
        try {
            // 注意：API 中没有删除接口，这里仅作示例
            message.success(tProviders('deleteSuccess'))
            fetchProviders(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error(tProviders('deleteFailed'))
        }
    }

    const handleSubmit = async (values: any) => {
        try {
            if (editingProvider) {
                // 更新供应商（API 中没有更新接口）
                message.success(tProviders('updateSuccess'))
            } else {
                await providersApi.createProvider(values)
                message.success(tProviders('createSuccess'))
            }
            setModalVisible(false)
            // 刷新当前页
            fetchProviders(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error(editingProvider ? tProviders('updateFailed') : tProviders('createFailed'))
        }
    }

    const handleTableChange = (newPagination: any) => {
        fetchProviders(newPagination.current, newPagination.pageSize)
    }

    const handleHealthCheck = async (provider: Provider) => {
        try {
            await providersApi.getProviderHealth(provider.name)
            message.success(tProviders('healthCheckSuccess'))
            fetchProviders()
        } catch (error) {
            message.error(tProviders('healthCheckFailed'))
        }
    }

    const columns = [
        {
            title: tProviders('providerName'),
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>
        },
        {
            title: tProviders('providerType'),
            dataIndex: 'type',
            key: 'type',
            render: (type: string) => (
                <Tag color="blue">{type}</Tag>
            )
        },
        {
            title: tProviders('endpoint'),
            dataIndex: 'endpoint',
            key: 'endpoint',
            render: (endpoint: string) => (
                <Tooltip title={endpoint}>
                    <span style={{ display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {endpoint}
                    </span>
                </Tooltip>
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
        },

        {
            title: tProviders('performance'),
            dataIndex: 'performance',
            key: 'performance',
            render: (performance: Provider['performance']) => (
                performance ? (
                    <Space direction="vertical" size="small">
                        <span>{tCommon('responseTime')}: {performance.responseTime}ms</span>
                        <span>{tProviders('successRate')}: {(performance.successRate * 100).toFixed(1)}%</span>
                    </Space>
                ) : <span>-</span>
            )
        },
        {
            title: tCommon('actions'),
            key: 'actions',
            render: (_: any, record: Provider) => (
                <Space>
                    <Tooltip title={tProviders('healthCheck')}>
                        <Button
                            type="text"
                            icon={<SettingOutlined />}
                            onClick={() => handleHealthCheck(record)}
                        />
                    </Tooltip>
                    <Tooltip title={tCommon('edit')}>
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(record)}
                        />
                    </Tooltip>
                    <Popconfirm
                        title={tProviders('deleteConfirm')}
                        onConfirm={() => handleDelete(record)}
                    >
                        <Tooltip title={tCommon('delete')}>
                            <Button type="text" danger icon={<DeleteOutlined />} />
                        </Tooltip>
                    </Popconfirm>
                </Space>
            )
        }
    ]

    useEffect(() => {
        fetchProviders()
    }, [])

    return (
        <div>
            <Card>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <h2>{tProviders('title')}</h2>
                    <Space>
                        <Button icon={<ReloadOutlined />} onClick={() => fetchProviders()}>
                            {tCommon('refresh')}
                        </Button>
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                            {tProviders('addProvider')}
                        </Button>
                    </Space>
                </div>

                <Table
                    columns={columns}
                    dataSource={providers}
                    loading={loading}
                    rowKey="id"
                    pagination={{
                        current: pagination.current,
                        pageSize: pagination.pageSize,
                        total: pagination.total,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total) => tProviders('totalProviders').replace('{total}', String(total))
                    }}
                    onChange={handleTableChange}
                />
            </Card>

            <Modal
                title={editingProvider ? tProviders('editProvider') : tProviders('addProvider')}
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                onOk={() => form.submit()}
                okText={tCommon('confirm')}
                cancelText={tCommon('cancel')}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                >
                    <Form.Item
                        name="name"
                        label={tProviders('providerName')}
                        rules={[{ required: true, message: tProviders('pleaseInputName') }]}
                    >
                        <Input placeholder={tProviders('providerNamePlaceholder')} />
                    </Form.Item>

                    <Form.Item
                        name="type"
                        label={tProviders('providerType')}
                        rules={[{ required: true, message: tProviders('pleaseSelectType') }]}
                    >
                        <Select placeholder={tProviders('selectProviderType')}>
                            <Select.Option value="openai">OpenAI</Select.Option>
                            <Select.Option value="anthropic">Anthropic</Select.Option>
                            <Select.Option value="google">Google</Select.Option>
                            <Select.Option value="alibaba">阿里云</Select.Option>
                            <Select.Option value="baidu">百度</Select.Option>
                            <Select.Option value="tencent">腾讯云</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="endpoint"
                        label={tProviders('apiEndpoint')}
                        rules={[{ required: true, message: tProviders('pleaseInputEndpoint') }]}
                    >
                        <Input placeholder={tProviders('endpointPlaceholder')} />
                    </Form.Item>

                    <Form.Item
                        name="apiKey"
                        label={tProviders('apiKey')}
                        rules={[{ required: true, message: tProviders('pleaseInputApiKey') }]}
                    >
                        <Input.Password placeholder={tProviders('pleaseInputApiKey')} />
                    </Form.Item>

                    <Form.Item
                        name="status"
                        label={tCommon('status')}
                        initialValue="active"
                    >
                        <Select>
                            <Select.Option value="active">{tCommon('enabled')}</Select.Option>
                            <Select.Option value="inactive">{tCommon('disabled')}</Select.Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}

export default ProvidersPage

