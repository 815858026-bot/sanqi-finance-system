import React from 'react';
import { Button, Card, Col, DatePicker, Form, Input, message, Row, Space, Table, Upload } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { UploadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import apiClient from '../services/api';
import { useAuthStore } from '../store/authStore';

interface MeetingItem {
  id: number;
  title: string;
  meeting_time: string;
  location: string;
  host: string;
  attendees: string[];
  topics: string;
  decisions?: string;
  content: string;
  attachment_path?: string;
  status: string;
  signed_off_by?: string;
}

const Meetings: React.FC = () => {
  const { user } = useAuthStore();
  const [meetings, setMeetings] = React.useState<MeetingItem[]>([]);
  const [attachmentPath, setAttachmentPath] = React.useState<string>();
  const [loading, setLoading] = React.useState(false);
  const [form] = Form.useForm();

  const canSign = user?.role === 'partner' || user?.role === 'super_admin';
  const canArchive = user?.role === 'super_admin' || user?.role === 'accountant_admin';

  const loadMeetings = React.useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.get('/api/meetings');
      setMeetings(data);
    } catch (error) {
      message.error('加载会议纪要失败');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadMeetings();
  }, [loadMeetings]);

  const handleCreate = async (values: any) => {
    try {
      await apiClient.post('/api/meetings', {
        ...values,
        meeting_time: values.meeting_time.toISOString(),
        attendees: values.attendees.split(/[,\n]/).map((item: string) => item.trim()).filter(Boolean),
        attachment_path: attachmentPath,
      });
      message.success('会议纪要已创建');
      form.resetFields();
      setAttachmentPath(undefined);
      await loadMeetings();
    } catch (error: any) {
      message.error(error?.detail || '创建会议纪要失败');
    }
  };

  const uploadProps = {
    customRequest: async (options: any) => {
      try {
        const formData = new FormData();
        formData.append('file', options.file);
        const result = await apiClient.post('/api/meetings/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        setAttachmentPath(result.attachment_path);
        options.onSuccess(result);
        message.success('附件上传成功');
      } catch (error) {
        options.onError(error);
        message.error('附件上传失败');
      }
    },
    showUploadList: true,
  };

  const handleSign = async (id: number) => {
    await apiClient.post(`/api/meetings/${id}/sign`);
    message.success('会议纪要已签批');
    await loadMeetings();
  };

  const handleArchive = async (id: number) => {
    await apiClient.post(`/api/meetings/${id}/archive`);
    message.success('会议纪要已归档');
    await loadMeetings();
  };

  const columns: ColumnsType<MeetingItem> = [
    { title: '会议主题', dataIndex: 'title', key: 'title' },
    { title: '时间', dataIndex: 'meeting_time', key: 'meeting_time', render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm') },
    { title: '地点', dataIndex: 'location', key: 'location' },
    { title: '主持人', dataIndex: 'host', key: 'host' },
    { title: '与会人员', dataIndex: 'attendees', key: 'attendees', render: (value: string[]) => value.join('、') },
    { title: '决议', dataIndex: 'decisions', key: 'decisions', render: (value?: string) => value || '-' },
    { title: '附件', dataIndex: 'attachment_path', key: 'attachment_path', render: (value?: string) => value ? <a href={value} target="_blank" rel="noreferrer">查看附件</a> : '-' },
    { title: '签批', key: 'signed', render: (_, record) => record.signed_off_by || (canSign ? <Button type="link" onClick={() => void handleSign(record.id)}>签批</Button> : '待签批') },
    { title: '操作', key: 'action', render: (_, record) => canArchive && record.status === 'draft' ? <Button type="link" onClick={() => void handleArchive(record.id)}>归档</Button> : record.status },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="新建会议纪要">
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col xs={24} md={8}><Form.Item name="title" label="会议主题" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="meeting_time" label="会议时间" rules={[{ required: true }]}><DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="location" label="会议地点" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="host" label="主持人" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col xs={24} md={16}><Form.Item name="attendees" label="与会人员" rules={[{ required: true }]}><Input.TextArea rows={2} placeholder="多个与会人员可用逗号或换行分隔" /></Form.Item></Col>
            <Col span={24}><Form.Item name="topics" label="会议议题" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item></Col>
            <Col span={24}><Form.Item name="decisions" label="会议决议"><Input.TextArea rows={2} /></Form.Item></Col>
            <Col span={24}><Form.Item name="content" label="会议纪要内容" rules={[{ required: true }]}><Input.TextArea rows={4} /></Form.Item></Col>
            <Col span={24}><Upload {...uploadProps}><Button icon={<UploadOutlined />}>上传会议附件</Button></Upload></Col>
          </Row>
          <Button type="primary" htmlType="submit">保存会议纪要</Button>
        </Form>
      </Card>
      <Card title="会议纪要列表">
        <Table rowKey="id" columns={columns} dataSource={meetings} loading={loading} pagination={{ pageSize: 8 }} />
      </Card>
    </Space>
  );
};

export default Meetings;
