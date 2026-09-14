import React from 'react';
import { Button, Card, Col, DatePicker, Form, Input, InputNumber, List, message, Modal, Row, Select, Space, Statistic, Table, Upload } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, UploadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import apiClient from '../services/api';

interface ExpenseItem {
  id: number;
  item_name: string;
  project_name?: string;
  category: string;
  amount: number;
  payment_date: string;
  payer: string;
  receipt_path?: string;
  note?: string;
  is_recurring: boolean;
  reminder_day?: number;
  status: string;
}

interface CategoryStat {
  category: string;
  total: number;
  count: number;
}

interface ReminderItem {
  expense_id: number;
  item_name: string;
  category: string;
  next_due_date: string;
  amount: number;
}

const categoryOptions = ['房租', '物业费', '水费', '电费', '网费', '其他杂费'];

const Records: React.FC = () => {
  const [expenses, setExpenses] = React.useState<ExpenseItem[]>([]);
  const [categoryStats, setCategoryStats] = React.useState<CategoryStat[]>([]);
  const [reminders, setReminders] = React.useState<ReminderItem[]>([]);
  const [monthlyTotal, setMonthlyTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(false);
  const [receiptPath, setReceiptPath] = React.useState<string>();
  const [modalVisible, setModalVisible] = React.useState(false);
  const [bulkVisible, setBulkVisible] = React.useState(false);
  const [form] = Form.useForm();
  const [bulkForm] = Form.useForm();

  const loadData = React.useCallback(async () => {
    try {
      setLoading(true);
      const now = dayjs();
      const [expenseData, monthlyData, categoryData, reminderData] = await Promise.all([
        apiClient.get('/api/records'),
        apiClient.get('/api/records/statistics/monthly', { params: { year: now.year(), month: now.month() + 1 } }),
        apiClient.get('/api/records/statistics/categories'),
        apiClient.get('/api/records/reminders'),
      ]);
      setExpenses(expenseData);
      setMonthlyTotal(monthlyData.total || 0);
      setCategoryStats(categoryData);
      setReminders(reminderData);
    } catch (error) {
      message.error('加载办公费用失败');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadData();
    bulkForm.setFieldsValue({ items: [{}] });
  }, [bulkForm, loadData]);

  const handleCreate = async (values: any) => {
    try {
      await apiClient.post('/api/records', {
        ...values,
        payment_date: values.payment_date.format('YYYY-MM-DD'),
        receipt_path: receiptPath,
      });
      message.success('办公费用已保存');
      setModalVisible(false);
      setReceiptPath(undefined);
      form.resetFields();
      await loadData();
    } catch (error: any) {
      message.error(error?.detail || '保存失败');
    }
  };

  const handleBulkImport = async (values: any) => {
    try {
      const payload = (values.items || []).map((item: any) => ({
        ...item,
        payment_date: item.payment_date.format('YYYY-MM-DD'),
      }));
      await apiClient.post('/api/records/bulk', payload);
      message.success('批量导入成功');
      setBulkVisible(false);
      bulkForm.resetFields();
      bulkForm.setFieldsValue({ items: [{}] });
      await loadData();
    } catch (error: any) {
      message.error(error?.detail || '批量导入失败');
    }
  };

  const uploadProps = {
    customRequest: async (options: any) => {
      try {
        const formData = new FormData();
        formData.append('file', options.file);
        const result = await apiClient.post('/api/records/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setReceiptPath(result.receipt_path);
        options.onSuccess(result);
      } catch (error) {
        options.onError(error);
        message.error('凭证上传失败');
      }
    },
  };

  const columns: ColumnsType<ExpenseItem> = [
    { title: '费用名称', dataIndex: 'item_name', key: 'item_name' },
    { title: '项目名', dataIndex: 'project_name', key: 'project_name', render: (value?: string) => value || '-' },
    { title: '类型', dataIndex: 'category', key: 'category' },
    { title: '金额', dataIndex: 'amount', key: 'amount' },
    { title: '付款日期', dataIndex: 'payment_date', key: 'payment_date' },
    { title: '付款人', dataIndex: 'payer', key: 'payer' },
    { title: '凭证', dataIndex: 'receipt_path', key: 'receipt_path', render: (value?: string) => value ? <a href={value} target="_blank" rel="noreferrer">查看</a> : '-' },
    { title: '状态', dataIndex: 'status', key: 'status' },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col xs={24} md={8}><Card><Statistic title="本月办公费用" value={monthlyTotal} precision={2} /></Card></Col>
        <Col xs={24} md={8}><Card><Statistic title="费用分类数" value={categoryStats.length} /></Card></Col>
        <Col xs={24} md={8}><Card><Statistic title="待提醒定期费用" value={reminders.length} /></Card></Col>
      </Row>

      <Card title="办公费用管理" extra={<Space><Button icon={<PlusOutlined />} onClick={() => setBulkVisible(true)}>批量导入</Button><Button type="primary" onClick={() => setModalVisible(true)}>新增费用</Button></Space>}>
        <Table rowKey="id" columns={columns} dataSource={expenses} loading={loading} pagination={{ pageSize: 8 }} />
      </Card>

      <Row gutter={16}>
        <Col xs={24} md={12}>
          <Card title="按费用类型统计">
            <List dataSource={categoryStats} renderItem={(item) => <List.Item>{item.category}：{item.total}（{item.count}笔）</List.Item>} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="定期费用提醒">
            <List dataSource={reminders} renderItem={(item) => <List.Item>{item.item_name}（{item.category}）- {item.next_due_date} - ¥{item.amount}</List.Item>} />
          </Card>
        </Col>
      </Row>

      <Modal title="新增办公费用" open={modalVisible} onOk={() => form.submit()} onCancel={() => setModalVisible(false)}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="item_name" label="费用名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="project_name" label="项目名"><Input /></Form.Item>
          <Form.Item name="category" label="费用类型" rules={[{ required: true }]}><Select options={categoryOptions.map((item) => ({ label: item, value: item }))} /></Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="payment_date" label="付款日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="payer" label="付款人" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="note" label="备注"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="reminder_day" label="提醒日（定期费用可填）"><InputNumber min={1} max={31} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="is_recurring" label="是否定期费用"><Select options={[{ label: '否', value: false }, { label: '是', value: true }]} /></Form.Item>
          <Upload {...uploadProps}><Button icon={<UploadOutlined />}>上传收据/凭证</Button></Upload>
        </Form>
      </Modal>

      <Modal title="批量导入办公费用" open={bulkVisible} onOk={() => bulkForm.submit()} onCancel={() => setBulkVisible(false)} width={900}>
        <Form form={bulkForm} layout="vertical" onFinish={handleBulkImport}>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <Space direction="vertical" style={{ width: '100%' }}>
                {fields.map((field) => (
                  <Card key={field.key} size="small" extra={<Button type="link" danger onClick={() => remove(field.name)}>删除</Button>}>
                    <Row gutter={16}>
                      <Col xs={24} md={6}><Form.Item {...field} name={[field.name, 'item_name']} label="费用名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
                      <Col xs={24} md={5}><Form.Item {...field} name={[field.name, 'category']} label="类型" rules={[{ required: true }]}><Select options={categoryOptions.map((item) => ({ label: item, value: item }))} /></Form.Item></Col>
                      <Col xs={24} md={4}><Form.Item {...field} name={[field.name, 'amount']} label="金额" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
                      <Col xs={24} md={5}><Form.Item {...field} name={[field.name, 'payment_date']} label="付款日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
                      <Col xs={24} md={4}><Form.Item {...field} name={[field.name, 'payer']} label="付款人" rules={[{ required: true }]}><Input /></Form.Item></Col>
                    </Row>
                  </Card>
                ))}
                <Button onClick={() => add({})}>新增一行</Button>
              </Space>
            )}
          </Form.List>
        </Form>
      </Modal>
    </Space>
  );
};

export default Records;
