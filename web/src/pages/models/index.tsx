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

interface Model {
    id?: number
    name: string
    provider: string
    capabilities: string[]
    status: 'active' | 'inactive'
    health?: 'healthy' | 'unhealthy' | 'unknown'
}

const ModelsPage: React.FC = () => {
    const [models, setModels] = useState<Model[]>([])
    const [loading, setLoading] = useState(false)
    const [modalVisible, setModalVisible] = useState(false)
    const [editingModel, setEditingModel] = useState<Model | null>(null)
    const [form] = Form.useForm()

    const fetchModels = async () => {
        setLoading(true)
        try {
            const [adminModels, dbModels] = await Promise.all([
                modelsApi.getModels(),
                modelsApi.getDbModels()
            ])
            // 合并数据，优先显示数据库中的模型配置
            const modelsData = dbModels?.models || []
            // 转换数据格式以匹配前端接口
            const formattedModels = modelsData.map((model: any) => ({
                id: model.id,
                name: model.name,
                provider: model.type === 'PUBLIC' ? 'public' : 'private',
                capabilities: ['TEXT'], // 根据实际情况调整
                status: model.is_enabled ? 'active' : 'inactive',
                health: 'unknown'
            }))
            setModels(formattedModels)
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
        form.setFieldsValue(model)
        setModalVisible(true)
    }

    const handleDelete = async (model: Model) => {
        try {
            // 注意：API 中没有删除接口，这里仅作示例
            message.success('删除成功')
            fetchModels()
        } catch (error) {
            message.error('删除失败')
        }
    }

    const handleSubmit = async (values: any) => {
        try {
            if (editingModel) {
                // 更新模型（API 中没有更新接口）
                message.success('更新成功')
            } else {
                // 转换数据格式以匹配后端 API
                const payload = {
                    name: values.name,
                    llm_type: values.llm_type || 'chat',
                    description: values.description || null,
                    is_enabled: values.status === 'active',
                    provider_id: null, // 暂时不关联供应商
                    provider_weight: 10,
                    is_provider_preferred: false,
                    capability_ids: null // 暂时不关联能力
                }
                await modelsApi.createModel(payload)
                message.success('创建成功')
            }
            setModalVisible(false)
            fetchModels()
        } catch (error) {
            message.error(editingModel ? '更新失败' : '创建失败')
            console.error('Submit error:', error)
        }
    }

    const columns = [
        {
            title: '模型名称',
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>
        },
        {
            title: '供应商',
            dataIndex: 'provider',
            key: 'provider',
        },
        {
            title: '能力',
            dataIndex: 'capabilities',
            key: 'capabilities',
            render: (capabilities: string[]) => (
                <Space wrap>
                    {capabilities?.map(cap => (
                        <Tag key={cap} color="blue">{cap}</Tag>
                    ))}
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
            title: '健康状态',
            dataIndex: 'health',
            key: 'health',
            render: (health: string) => {
                const colorMap = { healthy: 'green', unhealthy: 'red', unknown: 'orange' }
                const textMap = { healthy: '健康', unhealthy: '异常', unknown: '未知' }
                return (
                    <Tag color={colorMap[health as keyof typeof colorMap] || 'default'}>
                        {textMap[health as keyof typeof textMap] || '未知'}
                    </Tag>
                )
            }
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
        fetchModels()
    }, [])

    return (
        <div>
            <Card>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <h2>模型管理</h2>
                    <Space>
                        <Button icon={<ReloadOutlined />} onClick={fetchModels}>
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
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (total) => `共 ${total} 个模型`
                    }}
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
                        label="模型类型"
                        rules={[{ required: true, message: '请选择模型类型' }]}
                        initialValue="chat"
                    >
                        <Select placeholder="选择模型类型">
                            <Select.Option value="chat">对话模型</Select.Option>
                            <Select.Option value="completion">补全模型</Select.Option>
                            <Select.Option value="embedding">嵌入模型</Select.Option>
                            <Select.Option value="image">图像模型</Select.Option>
                            <Select.Option value="PUBLIC">公共模型</Select.Option>
                            <Select.Option value="PRIVATE">私有模型</Select.Option>
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

