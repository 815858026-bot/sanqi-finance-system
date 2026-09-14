import React from 'react';
import { Button, Form, Input, Modal, Select, Space, Table, Tag, message } from 'antd';
import apiClient from '../services/api';

const Meetings: React.FC = () => {
  const [meetings, setMeetings] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [open, setOpen] = React.useState(false);
  const [form] = Form.useForm();

  const fetchMeetings = async () => {
    try {
      setLoading(true);
      setMeetings(await apiClient.get('/api/meetings'));
    } catch (error) {
      message.error('获取会议纪要失败');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchMeetings();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await apiClient.post('/api/meetings', values);
      message.success('会议纪要已保存');
      setOpen(false);
      form.resetFields();
      fetchMeetings();
    } catch (error: any) {
      message.error(error?.detail || '保存失败');
    }
  };

  const handleArchive = async (id: number) => {
    await apiClient.post(`/api/meetings/${id}/archive`);
    message.success('已归档');
    fetchMeetings();
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Button type="primary" onClick={() => setOpen(true)}>新增会议纪要</Button>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={meetings}
        columns={[
          { title: '会议主题', dataIndex: 'title' },
          { title: '时间', dataIndex: 'meeting_time' },
          { title: '地点', dataIndex: 'location' },
          { title: '主持人', dataIndex: 'host_name' },
          { title: '与会人员', dataIndex: 'attendees', render: (items: string[]) => items?.join('、') },
          { title: '状态', dataIndex: 'is_archived', render: (value: boolean) => value ? <Tag>已归档</Tag> : <Tag color="green">进行中</Tag> },
          { title: '操作', render: (_, record) => !record.is_archived && <Button type="link" onClick={() => handleArchive(record.id)}>归档</Button> },
        ]}
      />
      <Modal title="新增会议纪要" open={open} onOk={() => form.submit()} onCancel={() => setOpen(false)} width={800}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="title" label="会议主题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="meeting_time" label="会议时间" rules={[{ required: true }]}><Input type="datetime-local" /></Form.Item>
          <Form.Item name="location" label="会议地点" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="host_name" label="主持人"><Input /></Form.Item>
          <Form.Item name="attendees" label="与会人员"><Select mode="tags" placeholder="输入姓名后回车" /></Form.Item>
          <Form.Item name="agenda" label="会议议题"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="resolution" label="会议决议"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="minutes" label="会议纪要内容" rules={[{ required: true }]}><Input.TextArea rows={6} /></Form.Item>
          <Form.Item name="attachment_name" label="附件名称"><Input /></Form.Item>
          <Form.Item name="attachment_url" label="附件地址"><Input /></Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

export default Meetings;
