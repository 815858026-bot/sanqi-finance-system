import React from 'react';
import { Button, Drawer, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd';
import apiClient from '../services/api';

const cooperationLabel: Record<string, string> = {
  half_package: '半包',
  full_case: '全案',
};

const Projects: React.FC = () => {
  const [projects, setProjects] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [modalVisible, setModalVisible] = React.useState(false);
  const [phaseOpen, setPhaseOpen] = React.useState(false);
  const [activeProject, setActiveProject] = React.useState<any>(null);
  const [form] = Form.useForm();
  const [phaseForm] = Form.useForm();

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/projects');
      setProjects(response);
    } catch (error) {
      message.error('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = async (values: any) => {
    try {
      await apiClient.post('/api/projects', values);
      message.success('项目创建成功');
      setModalVisible(false);
      form.resetFields();
      fetchProjects();
    } catch (error: any) {
      message.error(error?.detail || '创建失败');
    }
  };

  const openPhaseDrawer = (record: any) => {
    setActiveProject(record);
    phaseForm.setFieldsValue({
      phases: record.payment_phases?.length
        ? record.payment_phases.map((phase: any) => ({ ...phase }))
        : [
            { phase_number: 1, phase_name: '签约后支付', trigger_progress: 0, payment_percent: 30, planned_amount: Math.round((record.total_price || 0) * 0.3) },
            { phase_number: 2, phase_name: '施工进度支付', trigger_progress: 50, payment_percent: 50, planned_amount: Math.round((record.total_price || 0) * 0.5) },
            { phase_number: 3, phase_name: '完工尾款', trigger_progress: 100, payment_percent: 20, planned_amount: Math.round((record.total_price || 0) * 0.2) },
          ],
    });
    setPhaseOpen(true);
  };

  const savePhases = async (values: any) => {
    try {
      await apiClient.post(`/api/projects/${activeProject.id}/payment-phases`, values.phases);
      message.success('收款阶段已更新');
      setPhaseOpen(false);
      fetchProjects();
    } catch (error: any) {
      message.error(error?.detail || '保存失败');
    }
  };

  const columns = [
    { title: '项目名称', dataIndex: 'name', key: 'name' },
    { title: '合同号', dataIndex: 'contract_number', key: 'contract_number' },
    { title: '客户名称', dataIndex: 'client_name', key: 'client_name' },
    { title: '合作方式', dataIndex: 'cooperation_type', key: 'cooperation_type', render: (value: string) => cooperationLabel[value] || value },
    { title: '合同总价', dataIndex: 'total_price', key: 'total_price' },
    { title: '已收/应收', key: 'collection', render: (_: any, record: any) => `${record.received_amount} / ${record.receivable_amount}` },
    { title: '收款进度', dataIndex: 'collection_progress', key: 'collection_progress', render: (value: number) => <Tag color={value >= 100 ? 'green' : 'blue'}>{value}%</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status' },
    { title: '操作', key: 'action', render: (_: any, record: any) => <Button type="link" onClick={() => openPhaseDrawer(record)}>分期收款</Button> },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setModalVisible(true)}>新建项目</Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={projects} loading={loading} />

      <Modal title="新建项目" open={modalVisible} onOk={() => form.submit()} onCancel={() => setModalVisible(false)}>
        <Form form={form} onFinish={handleCreateProject} layout="vertical">
          <Form.Item name="name" label="项目名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="contract_number" label="合同号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="client_name" label="客户名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="cooperation_type" label="合作方式" initialValue="half_package" rules={[{ required: true }]}><Select options={[{ value: 'half_package', label: '半包' }, { value: 'full_case', label: '全案' }]} /></Form.Item>
          <Form.Item name="contract_amount" label="合同额" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="total_price" label="合同总价"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="description" label="备注"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Drawer title={activeProject ? `${activeProject.name} - 分期收款` : '分期收款'} open={phaseOpen} onClose={() => setPhaseOpen(false)} width={800}>
        <Form form={phaseForm} layout="vertical" onFinish={savePhases}>
          <Form.List name="phases">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="start" style={{ display: 'flex', marginBottom: 8 }}>
                    <Form.Item {...field} name={[field.name, 'phase_number']} label="阶段" rules={[{ required: true }]}><InputNumber min={1} /></Form.Item>
                    <Form.Item {...field} name={[field.name, 'phase_name']} label="阶段名称" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item {...field} name={[field.name, 'trigger_progress']} label="触发进度(%)"><InputNumber min={0} max={100} /></Form.Item>
                    <Form.Item {...field} name={[field.name, 'payment_percent']} label="支付比例(%)" rules={[{ required: true }]}><InputNumber min={0} max={100} /></Form.Item>
                    <Form.Item {...field} name={[field.name, 'planned_amount']} label="应收金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
                    <Button danger onClick={() => remove(field.name)}>删除</Button>
                  </Space>
                ))}
                <Space>
                  <Button onClick={() => add({})}>新增阶段</Button>
                  <Button type="primary" onClick={() => phaseForm.submit()}>保存阶段</Button>
                </Space>
              </>
            )}
          </Form.List>
        </Form>
      </Drawer>
    </div>
  );
};

export default Projects;
