import React from 'react';
import { Table, Tag, message } from 'antd';
import apiClient from '../services/api';

const Admin: React.FC = () => {
  const [users, setUsers] = React.useState<any[]>([]);

  React.useEffect(() => {
    apiClient.get('/api/users').then(setUsers).catch(() => message.error('获取用户列表失败'));
  }, []);

  return (
    <Table
      rowKey="id"
      dataSource={users}
      columns={[
        { title: '用户名', dataIndex: 'username' },
        { title: '姓名', dataIndex: 'full_name' },
        { title: '角色', dataIndex: 'role' },
        { title: '状态', dataIndex: 'is_active', render: (value: boolean) => value ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag> },
      ]}
    />
  );
};

export default Admin;
