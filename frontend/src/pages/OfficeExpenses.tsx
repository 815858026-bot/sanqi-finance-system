import React from 'react';
import { Button, Card, Form, Input, InputNumber, Modal, Select, Space, Statistic, Table, message } from 'antd';
import apiClient from '../services/api';

const expenseOptions = ['房租', '物业费', '水费', '电费', '网费', '其他杂费'];

const OfficeExpenses: React.FC = () => {
  const [expenses, setExpenses] = React.useState<any[]>([]);
  const [stats, setStats] = React.useState<any>({ by_type: {} });
  const [singleOpen, setSingleOpen] = React.useState(false);
  const [batchOpen, setBatchOpen] = React.useState(false);
  const [singleForm] = Form.useForm();
  const [batchForm] = Form.useForm();

  const fetchData = async () => {
    try {
      const [expenseData, statData] = await Promise.all([
        apiClient.get('/api/office-expenses'),
        apiClient.get('/api/office-expenses/statistics'),
      ]);
      setExpenses(expenseData);
      setStats(statData);
    } catch (error) {
      message.error('获取办公费用失败');
    }
  };

  React.useEffect(() => {
    fetchData();
  }, []);

  const submitSingle = async (values: any) => {
    try {
      await apiClient.post('/api/office-expenses', values);
      message.success('办公费用已记录');
      setSingleOpen(false);
      singleForm.resetFields();
      fetchData();
    } catch (error: any) {
      message.error(error?.detail || '保存失败');
    }
  };

  const submitBatch = async (values: any) => {
    try {
      await apiClient.post('/api/office-expenses/batch-import', values);
      message.success('批量导入完成');
      setBatchOpen(false);
      batchForm.resetFields();
      fetchData();
    } catch (error: any) {
      message.error(error?.detail || '批量导入失败');
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space>
        <Button type="primary" onClick={() => setSingleOpen(true)}>新增费用</Button>
        <Button onClick={() => setBatchOpen(true)}>批量导入</Button>
      </Space>
      <Space wrap>
        <Card><Statistic title="费用总额" value={stats.total_amount || 0} precision={2} /></Card>
        {Object.entries(stats.by_type || {}).map(([key, value]) => (
          <Card key={key}><Statistic title={key} value={value as number} precision={2} /></Card>
        ))}
      </Space>
      <Table
        rowKey="id"
        dataSource={expenses}
        columns={[
          { title: '项目名', dataIndex: 'project_name' },
          { title: '费用类型', dataIndex: 'expense_type' },
          { title: '金额', dataIndex: 'amount' },
          { title: '付款日期', dataIndex: 'payment_date' },
          { title: '付款人', dataIndex: 'payer' },
          { title: '凭证', dataIndex: 'receipt_url' },
          { title: '描述', dataIndex: 'description' },
        ]}
      />

      <Modal title="新增办公费用" open={singleOpen} onOk={() => singleForm.submit()} onCancel={() => setSingleOpen(false)}>
        <Form form={singleForm} layout="vertical" onFinish={submitSingle}>
          <Form.Item name="project_name" label="项目名"><Input /></Form.Item>
          <Form.Item name="expense_type" label="费用类型" rules={[{ required: true }]}><Select options={expenseOptions.map((item) => ({ value: item, label: item }))} /></Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="payment_date" label="付款日期" rules={[{ required: true }]}><Input type="date" /></Form.Item>
          <Form.Item name="payer" label="付款人" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="receipt_url" label="凭证地址"><Input /></Form.Item>
          <Form.Item name="description" label="说明"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="批量导入办公费用" open={batchOpen} onOk={() => batchForm.submit()} onCancel={() => setBatchOpen(false)} width={900}>
        <Form form={batchForm} layout="vertical" onFinish={submitBatch} initialValues={{ items: [{}, {}] }}>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Card key={field.key} size="small" style={{ marginBottom: 12 }} extra={<Button type="link" danger onClick={() => remove(field.name)}>删除</Button>}>
                    <Space align="start" wrap>
                      <Form.Item {...field} name={[field.name, 'project_name']}><Input placeholder="项目名" /></Form.Item>
                      <Form.Item {...field} name={[field.name, 'expense_type']} rules={[{ required: true }]}><Select style={{ width: 140 }} options={expenseOptions.map((item) => ({ value: item, label: item }))} /></Form.Item>
                      <Form.Item {...field} name={[field.name, 'amount']} rules={[{ required: true }]}><InputNumber placeholder="金额" min={0} /></Form.Item>
                      <Form.Item {...field} name={[field.name, 'payment_date']} rules={[{ required: true }]}><Input type="date" /></Form.Item>
                      <Form.Item {...field} name={[field.name, 'payer']} rules={[{ required: true }]}><Input placeholder="付款人" /></Form.Item>
                    </Space>
                  </Card>
                ))}
                <Button onClick={() => add({})}>新增一行</Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </Space>
  );
};

export default OfficeExpenses;
