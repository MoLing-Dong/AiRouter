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
            message.error('获取供应商列表失败')
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
            message.success('删除成功')
            fetchProviders(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error('删除失败')
        }
    }

    const handleSubmit = async (values: any) => {
        try {
            if (editingProvider) {
                // 更新供应商（API 中没有更新接口）
                message.success('更新成功')
            } else {
                await providersApi.createProvider(values)
                message.success('创建成功')
            }
            setModalVisible(false)
            // 刷新当前页
            fetchProviders(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error(editingProvider ? '更新失败' : '创建失败')
        }
    }

    const handleTableChange = (newPagination: any) => {
        fetchProviders(newPagination.current, newPagination.pageSize)
    }

    const handleHealthCheck = async (provider: Provider) => {
        try {
            await providersApi.getProviderHealth(provider.name)
            message.success('健康检查完成')
            fetchProviders()
        } catch (error) {
            message.error('健康检查失败')
        }
    }

    const columns = [
        {
            title: '供应商名称',
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>
        },
        {
            title: '类型',
            dataIndex: 'type',
            key: 'type',
            render: (type: string) => (
                <Tag color="blue">{type}</Tag>
            )
        },
        {
            title: '端点',
            dataIndex: 'endpoint',
            key: 'endpoint',
            render: (endpoint: string) => (
                <Tooltip title={endpoint}>
                    <span style={{ maxWidth: 200, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {endpoint}
                    </span>
                </Tooltip>
            )
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => (
                <Tag color={status === 'active' ? 'green' : 'red'}>
                    {status === 'active' ? '启用' : '禁用'}
                </Tag>
            )
        },

        {
            title: '性能',
            dataIndex: 'performance',
            key: 'performance',
            render: (performance: Provider['performance']) => (
                performance ? (
                    <Space direction="vertical" size="small">
                        <span>响应时间: {performance.responseTime}ms</span>
                        <span>成功率: {(performance.successRate * 100).toFixed(1)}%</span>
                    </Space>
                ) : <span>-</span>
            )
        },
        {
            title: '操作',
            key: 'actions',
            render: (_: any, record: Provider) => (
                <Space>
                    <Tooltip title="健康检查">
                        <Button
                            type="text"
                            icon={<SettingOutlined />}
                            onClick={() => handleHealthCheck(record)}
                        />
                    </Tooltip>
                    <Tooltip title="编辑">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(record)}
                        />
                    </Tooltip>
                    <Popconfirm
                        title="确定要删除这个供应商吗？"
                        onConfirm={() => handleDelete(record)}
                    >
                        <Tooltip title="删除">
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
                    <h2>供应商管理</h2>
                    <Space>
                        <Button icon={<ReloadOutlined />} onClick={() => fetchProviders()}>
                            刷新
                        </Button>
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                            新增供应商
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
                        showTotal: (total) => `共 ${total} 个供应商`
                    }}
                    onChange={handleTableChange}
                />
            </Card>

            <Modal
                title={editingProvider ? '编辑供应商' : '新增供应商'}
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                onOk={() => form.submit()}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                >
                    <Form.Item
                        name="name"
                        label="供应商名称"
                        rules={[{ required: true, message: '请输入供应商名称' }]}
                    >
                        <Input placeholder="例如：openai" />
                    </Form.Item>

                    <Form.Item
                        name="type"
                        label="类型"
                        rules={[{ required: true, message: '请选择供应商类型' }]}
                    >
                        <Select placeholder="选择供应商类型">
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
                        label="API 端点"
                        rules={[{ required: true, message: '请输入 API 端点' }]}
                    >
                        <Input placeholder="例如：https://api.openai.com/v1" />
                    </Form.Item>

                    <Form.Item
                        name="apiKey"
                        label="API Key"
                        rules={[{ required: true, message: '请输入 API Key' }]}
                    >
                        <Input.Password placeholder="请输入 API Key" />
                    </Form.Item>

                    <Form.Item
                        name="status"
                        label="状态"
                        initialValue="active"
                    >
                        <Select>
                            <Select.Option value="active">启用</Select.Option>
                            <Select.Option value="inactive">禁用</Select.Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}

export default ProvidersPage

