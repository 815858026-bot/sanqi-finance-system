import React from 'react';
import { Button, Card, Col, DatePicker, Form, Input, InputNumber, message, Modal, Row, Select, Space, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import apiClient from '../services/api';

interface PaymentStage {
  id: number;
  stage_name: string;
  trigger_description: string;
  target_progress?: number;
  planned_percentage: number;
  planned_amount: number;
  received_amount: number;
  received_date?: string;
  status: string;
}

interface ProjectItem {
  id: number;
  name: string;
  contract_number: string;
  client_name: string;
  contract_total_price: number;
  cooperation_type: string;
  status: string;
  payment_stages: PaymentStage[];
  payment_summary: {
    receivable: number;
    received: number;
    outstanding: number;
  };
}

const defaultStages = [
  { stage_name: '第一期', trigger_description: '签约后支付', planned_percentage: 30 },
  { stage_name: '第二期', trigger_description: '施工进度达到 60% 支付', target_progress: 60, planned_percentage: 40 },
  { stage_name: '第三期', trigger_description: '完工时支付余款', target_progress: 100, planned_percentage: 30 },
];

const Projects: React.FC = () => {
  const [projects, setProjects] = React.useState<ProjectItem[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [modalVisible, setModalVisible] = React.useState(false);
  const [receiveModalVisible, setReceiveModalVisible] = React.useState(false);
  const [selectedStage, setSelectedStage] = React.useState<PaymentStage | null>(null);
  const [form] = Form.useForm();
  const [receiveForm] = Form.useForm();

  const fetchProjects = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/projects');
      setProjects(response);
    } catch (error) {
      message.error('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void fetchProjects();
    form.setFieldsValue({ payment_stages: defaultStages, cooperation_type: '半包' });
  }, [fetchProjects, form]);

  const handleCreateProject = async (values: any) => {
    try {
      await apiClient.post('/api/projects', {
        ...values,
        contract_amount: values.contract_total_price,
        payment_stages: (values.payment_stages || []).map((stage: any) => ({
          ...stage,
          planned_percentage: Number(stage.planned_percentage || 0),
          target_progress: stage.target_progress ?? null,
        })),
      });
      message.success('项目创建成功');
      setModalVisible(false);
      form.resetFields();
      form.setFieldsValue({ payment_stages: defaultStages, cooperation_type: '半包' });
      await fetchProjects();
    } catch (error: any) {
      message.error(error?.detail || '创建失败');
    }
  };

  const handleReceivePayment = async (values: any) => {
    if (!selectedStage) {
      return;
    }
    try {
      await apiClient.post(`/api/projects/payment-stages/${selectedStage.id}/receive`, {
        received_amount: values.received_amount,
        received_date: values.received_date.format('YYYY-MM-DD'),
        notes: values.notes,
      });
      message.success('收款登记成功');
      setReceiveModalVisible(false);
      receiveForm.resetFields();
      setSelectedStage(null);
      await fetchProjects();
    } catch (error: any) {
      message.error(error?.detail || '收款登记失败');
    }
  };

  const columns: ColumnsType<ProjectItem> = [
    { title: '项目名称', dataIndex: 'name', key: 'name' },
    { title: '合同号', dataIndex: 'contract_number', key: 'contract_number' },
    { title: '客户名称', dataIndex: 'client_name', key: 'client_name' },
    { title: '合作方式', dataIndex: 'cooperation_type', key: 'cooperation_type', render: (value: string) => <Tag color={value === '全案' ? 'purple' : 'blue'}>{value}</Tag> },
    { title: '合同总价', dataIndex: 'contract_total_price', key: 'contract_total_price' },
    { title: '已收/应收', key: 'payment_summary', render: (_, record) => `${record.payment_summary.received} / ${record.payment_summary.receivable}` },
    { title: '未收', key: 'outstanding', render: (_, record) => record.payment_summary.outstanding },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="项目与收款管理" extra={<Button type="primary" onClick={() => setModalVisible(true)}>新建项目</Button>}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={projects}
          loading={loading}
          expandable={{
            expandedRowRender: (record) => (
              <Table
                rowKey="id"
                pagination={false}
                dataSource={record.payment_stages}
                columns={[
                  { title: '阶段', dataIndex: 'stage_name', key: 'stage_name' },
                  { title: '条件', dataIndex: 'trigger_description', key: 'trigger_description' },
                  { title: '进度', dataIndex: 'target_progress', key: 'target_progress', render: (value?: number) => value ? `${value}%` : '-' },
                  { title: '计划比例', dataIndex: 'planned_percentage', key: 'planned_percentage', render: (value: number) => `${value}%` },
                  { title: '计划金额', dataIndex: 'planned_amount', key: 'planned_amount' },
                  { title: '已收金额', dataIndex: 'received_amount', key: 'received_amount' },
                  { title: '状态', dataIndex: 'status', key: 'status' },
                  {
                    title: '操作',
                    key: 'action',
                    render: (_, stage) => (
                      <Button type="link" onClick={() => {
                        setSelectedStage(stage);
                        setReceiveModalVisible(true);
                        receiveForm.setFieldsValue({ received_date: dayjs() });
                      }}>
                        登记收款
                      </Button>
                    ),
                  },
                ]}
              />
            ),
          }}
        />
      </Card>

      <Modal title="新建项目" open={modalVisible} onOk={() => form.submit()} onCancel={() => setModalVisible(false)} width={900}>
        <Form form={form} onFinish={handleCreateProject} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} md={8}><Form.Item name="name" label="项目名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="contract_number" label="合同号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="client_name" label="客户名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="cooperation_type" label="合作方式" rules={[{ required: true }]}><Select options={[{ label: '半包', value: '半包' }, { label: '全案', value: '全案' }]} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="contract_total_price" label="合同总价" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={24}><Form.List name="payment_stages">
              {(fields) => (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {fields.map((field) => (
                    <Row gutter={16} key={field.key}>
                      <Col xs={24} md={6}><Form.Item {...field} name={[field.name, 'stage_name']} label="阶段名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
                      <Col xs={24} md={8}><Form.Item {...field} name={[field.name, 'trigger_description']} label="付款条件" rules={[{ required: true }]}><Input /></Form.Item></Col>
                      <Col xs={24} md={4}><Form.Item {...field} name={[field.name, 'target_progress']} label="施工进度"><InputNumber min={0} max={100} style={{ width: '100%' }} /></Form.Item></Col>
                      <Col xs={24} md={6}><Form.Item {...field} name={[field.name, 'planned_percentage']} label="收款比例(%)" rules={[{ required: true }]}><InputNumber min={0} max={100} style={{ width: '100%' }} /></Form.Item></Col>
                    </Row>
                  ))}
                </Space>
              )}
            </Form.List></Col>
          </Row>
        </Form>
      </Modal>

      <Modal title={`登记收款 - ${selectedStage?.stage_name || ''}`} open={receiveModalVisible} onOk={() => receiveForm.submit()} onCancel={() => setReceiveModalVisible(false)}>
        <Form form={receiveForm} layout="vertical" onFinish={handleReceivePayment}>
          <Form.Item name="received_amount" label="本次收款金额" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="received_date" label="收款日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

export default Projects;
