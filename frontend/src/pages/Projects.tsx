import React from 'react';
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import apiClient from '../services/api';

type ProjectRecord = {
  id: number;
  name: string;
  contract_number: string;
  client_name: string;
  cooperation_mode: string;
  contract_amount: number;
  planned_collection: number;
  received_amount: number;
  receivable_amount: number;
  status: string;
};

const formatError = (error: unknown): string => {
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'detail' in error && typeof (error as { detail: unknown }).detail === 'string') {
    return (error as { detail: string }).detail;
  }
  return '操作失败';
};

const Projects: React.FC = () => {
  const [projects, setProjects] = React.useState<ProjectRecord[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [projectModalVisible, setProjectModalVisible] = React.useState(false);
  const [planModalVisible, setPlanModalVisible] = React.useState(false);
  const [collectionModalVisible, setCollectionModalVisible] = React.useState(false);
  const [selectedProjectId, setSelectedProjectId] = React.useState<number | null>(null);
  const [projectForm] = Form.useForm();
  const [planForm] = Form.useForm();
  const [collectionForm] = Form.useForm();

  const fetchProjects = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/projects');
      setProjects((response as ProjectRecord[]) || []);
    } catch (error) {
      message.error(formatError(error));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchProjects().catch(() => undefined);
  }, [fetchProjects]);

  const handleCreateProject = async (values: Record<string, unknown>) => {
    try {
      await apiClient.post('/api/projects', values);
      message.success('项目创建成功');
      setProjectModalVisible(false);
      projectForm.resetFields();
      await fetchProjects();
    } catch (error) {
      message.error(formatError(error));
    }
  };

  const handleCreatePlan = async (values: Record<string, unknown>) => {
    if (!selectedProjectId) {
      return;
    }
    try {
      await apiClient.post(`/api/projects/${selectedProjectId}/plans`, values);
      message.success('收款计划已创建');
      setPlanModalVisible(false);
      planForm.resetFields();
      await fetchProjects();
    } catch (error) {
      message.error(formatError(error));
    }
  };

  const handleCreateCollection = async (values: Record<string, unknown>) => {
    if (!selectedProjectId) {
      return;
    }
    try {
      await apiClient.post(`/api/projects/${selectedProjectId}/collections`, values);
      message.success('收款进度已登记');
      setCollectionModalVisible(false);
      collectionForm.resetFields();
      await fetchProjects();
    } catch (error) {
      message.error(formatError(error));
    }
  };

  const openPlanModal = (projectId: number) => {
    setSelectedProjectId(projectId);
    setPlanModalVisible(true);
  };

  const openCollectionModal = (projectId: number) => {
    setSelectedProjectId(projectId);
    setCollectionModalVisible(true);
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setProjectModalVisible(true)}>
          新建项目
        </Button>
      </Space>
      <Table<ProjectRecord>
        rowKey="id"
        loading={loading}
        dataSource={projects}
        columns={[
          { title: '项目名称', dataIndex: 'name' },
          { title: '客户', dataIndex: 'client_name' },
          { title: '合同号', dataIndex: 'contract_number' },
          { title: '合作方式', dataIndex: 'cooperation_mode' },
          { title: '合同总价', dataIndex: 'contract_amount' },
          { title: '计划收款', dataIndex: 'planned_collection' },
          { title: '已收金额', dataIndex: 'received_amount' },
          { title: '应收金额', dataIndex: 'receivable_amount' },
          { title: '状态', dataIndex: 'status' },
          {
            title: '操作',
            render: (_, record) => (
              <Space>
                <Button size="small" onClick={() => openPlanModal(record.id)}>
                  收款计划
                </Button>
                <Button size="small" onClick={() => openCollectionModal(record.id)}>
                  登记收款
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal title="新建项目" open={projectModalVisible} onOk={() => projectForm.submit()} onCancel={() => setProjectModalVisible(false)}>
        <Form form={projectForm} onFinish={handleCreateProject} layout="vertical" initialValues={{ cooperation_mode: '半包', status: '进行中' }}>
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="contract_number" label="合同号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="client_name" label="客户名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="site_name" label="工地名称"><Input /></Form.Item>
          <Form.Item name="cooperation_mode" label="合作方式" rules={[{ required: true }]}>
            <Select options={[{ label: '半包', value: '半包' }, { label: '全案', value: '全案' }]} />
          </Form.Item>
          <Form.Item name="contract_amount" label="合同总价" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal title="新增收款计划" open={planModalVisible} onOk={() => planForm.submit()} onCancel={() => setPlanModalVisible(false)}>
        <Form form={planForm} onFinish={handleCreatePlan} layout="vertical">
          <Form.Item name="stage_name" label="阶段" rules={[{ required: true }]}><Input placeholder="签约 / 进度 / 完工" /></Form.Item>
          <Form.Item name="planned_amount" label="计划金额" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
          <Form.Item name="planned_date" label="计划日期"><Input placeholder="YYYY-MM-DD" /></Form.Item>
        </Form>
      </Modal>

      <Modal title="登记实际收款" open={collectionModalVisible} onOk={() => collectionForm.submit()} onCancel={() => setCollectionModalVisible(false)}>
        <Form form={collectionForm} onFinish={handleCreateCollection} layout="vertical">
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
          <Form.Item name="received_date" label="收款日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Projects;
