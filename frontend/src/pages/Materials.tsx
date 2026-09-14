import React from 'react';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Statistic, Table, Tabs, message } from 'antd';
import apiClient from '../services/api';

const categoryOptions = ['建材', '五金', '家居', '其他'];

const Materials: React.FC = () => {
  const [materials, setMaterials] = React.useState<any[]>([]);
  const [inbounds, setInbounds] = React.useState<any[]>([]);
  const [outbounds, setOutbounds] = React.useState<any[]>([]);
  const [stats, setStats] = React.useState<any>({ material_stats: [], project_costs: {} });
  const [projects, setProjects] = React.useState<any[]>([]);
  const [materialOpen, setMaterialOpen] = React.useState(false);
  const [inboundOpen, setInboundOpen] = React.useState(false);
  const [outboundOpen, setOutboundOpen] = React.useState(false);
  const [materialForm] = Form.useForm();
  const [inboundForm] = Form.useForm();
  const [outboundForm] = Form.useForm();

  const fetchData = async () => {
    try {
      const [materialData, inboundData, outboundData, statData, projectData] = await Promise.all([
        apiClient.get('/api/materials'),
        apiClient.get('/api/materials/inbounds'),
        apiClient.get('/api/materials/outbounds'),
        apiClient.get('/api/materials/statistics'),
        apiClient.get('/api/projects'),
      ]);
      setMaterials(materialData);
      setInbounds(inboundData);
      setOutbounds(outboundData);
      setStats(statData);
      setProjects(projectData);
    } catch (error) {
      message.error('获取物料信息失败');
    }
  };

  React.useEffect(() => {
    fetchData();
  }, []);

  const submitMaterial = async (values: any) => {
    try {
      await apiClient.post('/api/materials', values);
      message.success('物料已创建');
      setMaterialOpen(false);
      materialForm.resetFields();
      fetchData();
    } catch (error: any) {
      message.error(error?.detail || '保存失败');
    }
  };

  const submitInbound = async (values: any) => {
    try {
      await apiClient.post('/api/materials/inbounds', values);
      message.success('入库已登记');
      setInboundOpen(false);
      inboundForm.resetFields();
      fetchData();
    } catch (error: any) {
      message.error(error?.detail || '保存失败');
    }
  };

  const submitOutbound = async (values: any) => {
    try {
      const selected = projects.find((item) => item.id === values.project_id);
      await apiClient.post('/api/materials/outbounds', {
        ...values,
        project_name: selected?.name || values.project_name,
      });
      message.success('领用申请已提交');
      setOutboundOpen(false);
      outboundForm.resetFields();
      fetchData();
    } catch (error: any) {
      message.error(error?.detail || '提交失败');
    }
  };

  const approveOutbound = async (id: number) => {
    try {
      await apiClient.post(`/api/materials/outbounds/${id}/approve`);
      message.success('已审批并扣减库存');
      fetchData();
    } catch (error: any) {
      message.error(error?.detail || '审批失败');
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space>
        <Button type="primary" onClick={() => setMaterialOpen(true)}>新增物料</Button>
        <Button onClick={() => setInboundOpen(true)}>新增入库</Button>
        <Button onClick={() => setOutboundOpen(true)}>发起领用</Button>
      </Space>
      <Tabs items={[
        {
          key: 'materials',
          label: '物料列表',
          children: <Table rowKey="id" dataSource={materials} columns={[
            { title: '编号', dataIndex: 'code' },
            { title: '名称', dataIndex: 'name' },
            { title: '规格', dataIndex: 'specification' },
            { title: '分类', dataIndex: 'category' },
            { title: '单位', dataIndex: 'unit' },
            { title: '成本价', dataIndex: 'cost_price' },
            { title: '库存', dataIndex: 'current_stock' },
            { title: '预警值', dataIndex: 'warning_quantity' },
          ]} />,
        },
        {
          key: 'inbounds',
          label: '入库记录',
          children: <Table rowKey="id" dataSource={inbounds} columns={[
            { title: '物料', dataIndex: 'material_name' },
            { title: '供应商', dataIndex: 'supplier' },
            { title: '采购日期', dataIndex: 'purchase_date' },
            { title: '单价', dataIndex: 'unit_price' },
            { title: '数量', dataIndex: 'quantity' },
            { title: '总金额', dataIndex: 'total_amount' },
            { title: '登记人', dataIndex: 'operator_name' },
          ]} />,
        },
        {
          key: 'outbounds',
          label: '领用记录',
          children: <Table rowKey="id" dataSource={outbounds} columns={[
            { title: '工地', dataIndex: 'project_name' },
            { title: '领用人', dataIndex: 'requester_name' },
            { title: '领用日期', dataIndex: 'issue_date' },
            { title: '用途', dataIndex: 'purpose' },
            { title: '物料清单', render: (_, record) => record.items?.map((item: any) => `${item.material_name} x ${item.quantity}`).join('；') },
            { title: '状态', dataIndex: 'status' },
            { title: '操作', render: (_, record) => record.status === 'pending' && <Button type="link" onClick={() => approveOutbound(record.id)}>审批</Button> },
          ]} />,
        },
        {
          key: 'stats',
          label: '库存统计',
          children: <Space direction="vertical" style={{ width: '100%' }}>
            <Card><Statistic title="库存总价值" value={stats.inventory_value || 0} precision={2} /></Card>
            <Table rowKey="id" dataSource={stats.material_stats || []} columns={[
              { title: '物料', dataIndex: 'name' },
              { title: '入库数量', dataIndex: 'inbound_quantity' },
              { title: '出库数量', dataIndex: 'outbound_quantity' },
              { title: '当前库存', dataIndex: 'current_stock' },
              { title: '库存价值', dataIndex: 'inventory_value' },
            ]} />
          </Space>,
        },
      ]} />

      <Modal title="新增物料" open={materialOpen} onOk={() => materialForm.submit()} onCancel={() => setMaterialOpen(false)}>
        <Form form={materialForm} layout="vertical" onFinish={submitMaterial}>
          <Form.Item name="code" label="物料编号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="specification" label="规格"><Input /></Form.Item>
          <Form.Item name="unit" label="单位" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="cost_price" label="成本价"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true }]}><Select options={categoryOptions.map((item) => ({ value: item, label: item }))} /></Form.Item>
          <Form.Item name="warning_quantity" label="预警库存"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="image_url" label="图片地址"><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="登记物料入库" open={inboundOpen} onOk={() => inboundForm.submit()} onCancel={() => setInboundOpen(false)}>
        <Form form={inboundForm} layout="vertical" onFinish={submitInbound}>
          <Form.Item name="material_id" label="物料" rules={[{ required: true }]}><Select options={materials.map((item) => ({ value: item.id, label: item.name }))} /></Form.Item>
          <Form.Item name="purchase_date" label="采购日期" rules={[{ required: true }]}><Input type="date" /></Form.Item>
          <Form.Item name="supplier" label="供应商" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="unit_price" label="采购单价" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="quantity" label="数量" rules={[{ required: true }]}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="invoice_url" label="发票/收据"><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal title="发起物料领用" open={outboundOpen} onOk={() => outboundForm.submit()} onCancel={() => setOutboundOpen(false)} width={900}>
        <Form form={outboundForm} layout="vertical" onFinish={submitOutbound} initialValues={{ items: [{}] }}>
          <Form.Item name="project_id" label="关联工地"><Select allowClear options={projects.map((item) => ({ value: item.id, label: item.name }))} /></Form.Item>
          <Form.Item name="project_name" label="工地名称"><Input /></Form.Item>
          <Form.Item name="issue_date" label="领用日期" rules={[{ required: true }]}><Input type="date" /></Form.Item>
          <Form.Item name="purpose" label="用途"><Input.TextArea rows={2} /></Form.Item>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="start" style={{ display: 'flex', marginBottom: 8 }}>
                    <Form.Item {...field} name={[field.name, 'material_id']} rules={[{ required: true }]}><Select style={{ width: 240 }} placeholder="物料" options={materials.map((item) => ({ value: item.id, label: `${item.name}（库存${item.current_stock}）` }))} /></Form.Item>
                    <Form.Item {...field} name={[field.name, 'quantity']} rules={[{ required: true }]}><InputNumber min={1} placeholder="数量" /></Form.Item>
                    <Button danger onClick={() => remove(field.name)}>删除</Button>
                  </Space>
                ))}
                <Button onClick={() => add({})}>新增物料</Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </Space>
  );
};

export default Materials;
