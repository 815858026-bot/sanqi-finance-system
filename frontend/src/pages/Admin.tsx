import React from 'react';
import { Button, Card, Col, Form, Input, Row, Select, Space, Table, message } from 'antd';
import apiClient from '../services/api';
import { useAuthStore } from '../store/authStore';

const formatError = (error: unknown): string => {
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'detail' in error && typeof (error as { detail: unknown }).detail === 'string') {
    return (error as { detail: string }).detail;
  }
  return '操作失败';
};

const Admin: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const [users, setUsers] = React.useState<any[]>([]);
  const [logs, setLogs] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const canManageUsers = ['admin', 'finance_admin'].includes(user?.role || '');

  const fetchData = React.useCallback(async () => {
    try {
      setLoading(true);
      const logResponse = await apiClient.get('/api/audit/logs');
      setLogs((logResponse as any[]) || []);
      if (canManageUsers) {
        const userResponse = await apiClient.get('/api/users');
        setUsers((userResponse as any[]) || []);
      }
    } catch (error) {
      message.error(formatError(error));
    } finally {
      setLoading(false);
    }
  }, [canManageUsers]);

  React.useEffect(() => {
    fetchData().catch(() => undefined);
  }, [fetchData]);

  const submitUser = async (values: Record<string, unknown>) => {
    try {
      await apiClient.post('/api/users', values);
      message.success('用户创建成功');
      await fetchData();
    } catch (error) {
      message.error(formatError(error));
    }
  };

  const toggleUserStatus = async (record: { id: number; is_active: boolean }) => {
    try {
      await apiClient.patch(`/api/users/${record.id}/status?is_active=${String(!record.is_active)}`);
      message.success('状态已更新');
      await fetchData();
    } catch (error) {
      message.error(formatError(error));
    }
  };

  return (
    <Row gutter={[16, 16]}>
      {canManageUsers ? (
        <Col xs={24} lg={9}>
          <Card title="创建用户">
            <Form layout="vertical" onFinish={submitUser} initialValues={{ role: 'finance' }}>
              <Form.Item name="username" label="用户名" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="password" label="密码" rules={[{ required: true }]}><Input.Password /></Form.Item>
              <Form.Item name="full_name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="role" label="角色" rules={[{ required: true }]}>
                <Select options={[
                  { label: '超级管理员', value: 'admin' },
                  { label: '合伙人', value: 'partner' },
                  { label: '财务主管', value: 'finance_admin' },
                  { label: '财务人员', value: 'finance' },
                  { label: '出纳', value: 'cashier' },
                ]} />
              </Form.Item>
              <Form.Item name="email" label="邮箱"><Input /></Form.Item>
              <Form.Item name="phone" label="手机号"><Input /></Form.Item>
              <Button type="primary" htmlType="submit" block>创建</Button>
            </Form>
          </Card>
        </Col>
      ) : null}
      <Col xs={24} lg={canManageUsers ? 15 : 24}>
        {canManageUsers ? (
          <Card title="用户列表" style={{ marginBottom: 16 }}>
            <Table rowKey="id" loading={loading} dataSource={users} columns={[
              { title: '用户名', dataIndex: 'username' },
              { title: '姓名', dataIndex: 'full_name' },
              { title: '角色', dataIndex: 'role' },
              { title: '状态', dataIndex: 'is_active', render: (value: boolean) => (value ? '启用' : '停用') },
              {
                title: '操作',
                render: (_, record) => (
                  <Space>
                    <Button size="small" onClick={() => toggleUserStatus(record)}>
                      {record.is_active ? '停用' : '启用'}
                    </Button>
                  </Space>
                ),
              },
            ]} />
          </Card>
        ) : null}
        <Card title="审计日志（全员只读）">
          <Table rowKey="id" loading={loading} dataSource={logs} columns={[
            { title: '时间', dataIndex: 'created_at' },
            { title: '操作人', dataIndex: 'operator_name' },
            { title: '动作', dataIndex: 'action' },
            { title: '对象', dataIndex: 'target' },
            { title: '详情', dataIndex: 'detail' },
          ]} />
        </Card>
      </Col>
    </Row>
  );
};

export default Admin;
