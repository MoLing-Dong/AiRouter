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
import { PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import { modelsApi } from '@/services/api'
import { useCapabilitiesStore } from '@/stores/capabilitiesStore'

interface Provider {
    id: number
    name: string
    provider_type: string
    weight: number
    is_preferred: boolean
    health_status: string
}

interface Capability {
    capability_id: number
    capability_name: string
    description?: string
}

interface Model {
    id?: number
    name: string
    type: string
    description?: string
    is_enabled: boolean
    providers: Provider[]
    capabilities: Capability[]
    status: 'active' | 'inactive'
}

const ModelsPage: React.FC = () => {
    const [models, setModels] = useState<Model[]>([])
    const [loading, setLoading] = useState(false)
    const [modalVisible, setModalVisible] = useState(false)
    const [editingModel, setEditingModel] = useState<Model | null>(null)
    const [form] = Form.useForm()

    // 从 Zustand store 获取能力数据
    const { capabilities, loading: capabilitiesLoading, fetchCapabilities } = useCapabilitiesStore()

    // 分页状态
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 10,
        total: 0
    })

    const fetchModels = async (page: number = pagination.current, pageSize: number = pagination.pageSize) => {
        setLoading(true)
        try {
            const response: any = await modelsApi.getDbModels(page, pageSize)

            // 直接使用后端返回的数据，只需添加 status 字段
            const formattedModels = (response.data?.models || []).map((model: any) => ({
                ...model,
                status: model.is_enabled ? 'active' : 'inactive',
            }))

            setModels(formattedModels)

            // 更新分页信息
            setPagination({
                current: response.data?.page || 1,
                pageSize: response.data?.page_size || 10,
                total: response.data?.total || 0
            })
        } catch (error) {
            message.error('获取模型列表失败')
            console.error('Failed to fetch models:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleCreate = () => {
        setEditingModel(null)
        form.resetFields()
        setModalVisible(true)
    }

    const handleEdit = (model: Model) => {
        setEditingModel(model)
        // 转换数据格式以匹配表单字段
        form.setFieldsValue({
            name: model.name,
            llm_type: model.type,
            description: model.description,
            status: model.status,
            capabilities: model.capabilities?.map(cap => cap.capability_id) || []
        })
        setModalVisible(true)
    }

    const handleDelete = async (model: Model) => {
        try {
            if (!model.id) {
                message.error('模型ID不存在')
                return
            }
            await modelsApi.deleteModel(model.id)
            message.success('删除成功')
            fetchModels(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error('删除失败')
        }
    }

    const handleSubmit = async (values: any) => {
        try {
            // 转换数据格式以匹配后端 API
            const payload = {
                name: values.name,
                llm_type: values.llm_type || 'PUBLIC',
                description: values.description || null,
                is_enabled: values.status === 'active',
                capability_ids: values.capabilities || null, // 关联能力
                provider_id: values.provider_id || null, // 关联供应商
                provider_weight: values.provider_weight || 10,
                is_provider_preferred: values.is_provider_preferred || false,
            }

            if (editingModel && editingModel.id) {
                // 更新模型
                await modelsApi.updateModel(editingModel.id, payload)
                message.success('更新成功')
            } else {
                // 创建模型
                await modelsApi.createModel(payload)
                message.success('创建成功')
            }

            setModalVisible(false)
            // 刷新当前页
            fetchModels(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error(editingModel ? '更新失败' : '创建失败')
            console.error('Submit error:', error)
        }
    }

    const handleTableChange = (newPagination: any) => {
        fetchModels(newPagination.current, newPagination.pageSize)
    }

    const columns = [
        {
            title: '模型名称',
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>
        },
        {
            title: '类型',
            dataIndex: 'type',
            key: 'type',
            render: (type: string) => (
                <Tag color={type === 'PUBLIC' ? 'blue' : 'purple'}>
                    {type === 'PUBLIC' ? '公开' : '私有'}
                </Tag>
            )
        },
        {
            title: '供应商',
            dataIndex: 'providers',
            key: 'providers',
            render: (providers: Provider[], record: Model) => (
                <Space wrap>
                    {providers?.length > 0 ? (
                        providers.map((provider, index) => (
                            <Tooltip
                                key={`${record.id}-provider-${provider.id}-${index}`}
                                title={`权重: ${provider.weight} | 健康: ${provider.health_status}`}
                            >
                                <Tag
                                    color={provider.is_preferred ? 'gold' : 'default'}
                                    style={{ cursor: 'pointer' }}
                                >
                                    {provider.name}
                                    {provider.is_preferred && ' ⭐'}
                                </Tag>
                            </Tooltip>
                        ))
                    ) : (
                        <Tag color="default">未绑定</Tag>
                    )}
                </Space>
            )
        },
        {
            title: '能力',
            dataIndex: 'capabilities',
            key: 'capabilities',
            render: (capabilities: Capability[], record: Model) => (
                <Space wrap>
                    {capabilities?.length > 0 ? (
                        capabilities.map((cap, index) => (
                            <Tooltip
                                key={`${record.id}-cap-${cap.capability_id}-${index}`}
                                title={cap.description || cap.capability_name}
                            >
                                <Tag color="cyan">{cap.capability_name}</Tag>
                            </Tooltip>
                        ))
                    ) : (
                        <Tag color="default">无</Tag>
                    )}
                </Space>
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
            title: '操作',
            key: 'actions',
            render: (_: any, record: Model) => (
                <Space>
                    <Tooltip title="编辑">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(record)}
                        />
                    </Tooltip>
                    <Popconfirm
                        title="确定要删除这个模型吗？"
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
        fetchCapabilities()
        fetchModels()
    }, [])

    return (
        <div>
            <Card>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <h2>模型管理</h2>
                    <Space>
                        <Button icon={<ReloadOutlined />} onClick={() => fetchModels()}>
                            刷新
                        </Button>
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                            新增模型
                        </Button>
                    </Space>
                </div>

                <Table
                    columns={columns}
                    dataSource={models}
                    loading={loading}
                    rowKey="id"
                    pagination={{
                        current: pagination.current,
                        pageSize: pagination.pageSize,
                        total: pagination.total,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total) => `共 ${total} 个模型`
                    }}
                    onChange={handleTableChange}
                />
            </Card>

            <Modal
                title={editingModel ? '编辑模型' : '新增模型'}
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
                        label="模型名称"
                        rules={[{ required: true, message: '请输入模型名称' }]}
                    >
                        <Input placeholder="例如：gpt-4" />
                    </Form.Item>

                    <Form.Item
                        name="llm_type"
                        label="访问类型"
                        rules={[{ required: true, message: '请选择访问类型' }]}
                        initialValue="PUBLIC"
                        tooltip="模型的具体能力(对话、补全、嵌入、图像)通过下方的能力设置"
                    >
                        <Select placeholder="选择访问类型">
                            <Select.Option value="PUBLIC">公开模型</Select.Option>
                            <Select.Option value="PRIVATE">私有模型</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="capabilities"
                        label="模型能力"
                        tooltip="选择模型支持的功能,可多选"
                    >
                        <Select mode="multiple" placeholder="选择模型能力" loading={capabilitiesLoading}>
                            {capabilities.map(cap => (
                                <Select.Option key={cap.capability_id} value={cap.capability_id}>
                                    {cap.capability_name}
                                    {cap.description && ` - ${cap.description}`}
                                </Select.Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="description"
                        label="模型描述"
                    >
                        <Input.TextArea placeholder="请输入模型描述（可选）" rows={3} />
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

export default ModelsPage

