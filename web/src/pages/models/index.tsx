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
import { useTranslation } from '@/hooks/useTranslation'

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
    const { t: tModels } = useTranslation('models')
    const { t: tCommon } = useTranslation('common')
    const { t: tDashboard } = useTranslation('dashboard')

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
            message.error(tModels('fetchFailed'))
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
                message.error(tModels('modelIdNotExist'))
                return
            }
            await modelsApi.deleteModel(model.id)
            message.success(tModels('deleteSuccess'))
            fetchModels(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error(tModels('deleteFailed'))
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
                message.success(tModels('updateSuccess'))
            } else {
                // 创建模型
                await modelsApi.createModel(payload)
                message.success(tModels('createSuccess'))
            }

            setModalVisible(false)
            // 刷新当前页
            fetchModels(pagination.current, pagination.pageSize)
        } catch (error) {
            message.error(editingModel ? tModels('updateFailed') : tModels('createFailed'))
            console.error('Submit error:', error)
        }
    }

    const handleTableChange = (newPagination: any) => {
        fetchModels(newPagination.current, newPagination.pageSize)
    }

    const columns = [
        {
            title: tModels('modelName'),
            dataIndex: 'name',
            key: 'name',
            render: (text: string) => <strong>{text}</strong>
        },
        {
            title: tModels('modelType'),
            dataIndex: 'type',
            key: 'type',
            render: (type: string) => (
                <Tag color={type === 'PUBLIC' ? 'blue' : 'purple'}>
                    {type === 'PUBLIC' ? tModels('public') : tModels('private')}
                </Tag>
            )
        },
        {
            title: tDashboard('provider'),
            dataIndex: 'providers',
            key: 'providers',
            render: (providers: Provider[], record: Model) => (
                <Space wrap>
                    {providers?.length > 0 ? (
                        providers.map((provider, index) => (
                            <Tooltip
                                key={`${record.id}-provider-${provider.id}-${index}`}
                                title={`${tModels('weight')}: ${provider.weight} | ${tModels('health')}: ${provider.health_status}`}
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
                        <Tag color="default">{tModels('unbound')}</Tag>
                    )}
                </Space>
            )
        },
        {
            title: tModels('capabilities'),
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
                        <Tag color="default">{tCommon('none')}</Tag>
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
                    {status === 'active' ? tModels('enabled') : tModels('disabled')}
                </Tag>
            )
        },
        {
            title: tCommon('actions'),
            key: 'actions',
            render: (_: any, record: Model) => (
                <Space>
                    <Tooltip title={tCommon('edit')}>
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(record)}
                        />
                    </Tooltip>
                    <Popconfirm
                        title={tModels('deleteConfirm')}
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
        fetchCapabilities()
        fetchModels()
    }, [])

    return (
        <div>
            <Card>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <h2>{tModels('title')}</h2>
                    <Space>
                        <Button icon={<ReloadOutlined />} onClick={() => fetchModels()}>
                            {tCommon('refresh')}
                        </Button>
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                            {tModels('addModel')}
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
                        showTotal: (total) => tModels('totalModels').replace('{total}', String(total))
                    }}
                    onChange={handleTableChange}
                />
            </Card>

            <Modal
                title={editingModel ? tModels('editModel') : tModels('addModel')}
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
                        label={tModels('modelName')}
                        rules={[{ required: true, message: tModels('pleaseInputName') }]}
                    >
                        <Input placeholder={tModels('examplePlaceholder')} />
                    </Form.Item>

                    <Form.Item
                        name="llm_type"
                        label={tModels('accessType')}
                        rules={[{ required: true, message: tModels('pleaseSelectAccessType') }]}
                        initialValue="PUBLIC"
                        tooltip={tModels('accessTypeTooltip')}
                    >
                        <Select placeholder={tModels('selectAccessType')}>
                            <Select.Option value="PUBLIC">{tModels('publicModel')}</Select.Option>
                            <Select.Option value="PRIVATE">{tModels('privateModel')}</Select.Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="capabilities"
                        label={tModels('modelCapabilities')}
                        tooltip={tModels('capabilityTooltip')}
                    >
                        <Select mode="multiple" placeholder={tModels('selectCapabilities')} loading={capabilitiesLoading}>
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
                        label={tModels('modelDescription')}
                    >
                        <Input.TextArea placeholder={tModels('pleaseInputDescription')} rows={3} />
                    </Form.Item>

                    <Form.Item
                        name="status"
                        label={tCommon('status')}
                        initialValue="active"
                    >
                        <Select>
                            <Select.Option value="active">{tModels('enabled')}</Select.Option>
                            <Select.Option value="inactive">{tModels('disabled')}</Select.Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    )
}

export default ModelsPage

