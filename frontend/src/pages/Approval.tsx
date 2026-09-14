import React from 'react';
import { Table, message } from 'antd';
import apiClient from '../services/api';

const Approval: React.FC = () => {
  const [rows, setRows] = React.useState<any[]>([]);

  React.useEffect(() => {
    const fetchPending = async () => {
      try {
        const data = await apiClient.get('/api/approval/pending');
        setRows(data.material_outbounds || []);
      } catch {
        message.error('获取待审批列表失败');
      }
    };
    fetchPending();
  }, []);

  return (
    <Table
      rowKey="id"
      dataSource={rows}
      columns={[
        { title: '工地', dataIndex: 'project_name' },
        { title: '申请人', dataIndex: 'requester_name' },
        { title: '申请日期', dataIndex: 'issue_date' },
        { title: '内容', render: (_, record) => record.items?.map((item: any) => `${item.material_name} x ${item.quantity}`).join('；') },
        { title: '状态', dataIndex: 'status' },
      ]}
    />
  );
};

export default Approval;
