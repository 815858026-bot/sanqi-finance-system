import React from 'react';
import { Button, Card, Col, message, Row, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import apiClient from '../services/api';
import { useAuthStore } from '../store/authStore';

interface PendingExpense {
  id: number;
  item_name: string;
  category: string;
  amount: number;
  payment_date: string;
  payer: string;
}

interface PendingMeeting {
  id: number;
  title: string;
  meeting_time: string;
  host: string;
  location: string;
}

const Approval: React.FC = () => {
  const { user } = useAuthStore();
  const [pendingExpenses, setPendingExpenses] = React.useState<PendingExpense[]>([]);
  const [pendingMeetings, setPendingMeetings] = React.useState<PendingMeeting[]>([]);
  const [loading, setLoading] = React.useState(false);

  const canApproveExpense = user?.role === 'super_admin' || user?.role === 'accountant_admin';
  const canSignMeeting = user?.role === 'super_admin' || user?.role === 'partner';

  const loadPending = React.useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.get('/api/approval/pending');
      setPendingExpenses(data.pending_expenses || []);
      setPendingMeetings(data.pending_meetings || []);
    } catch (error) {
      message.error('加载待审批事项失败');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadPending();
  }, [loadPending]);

  const handleExpenseDecision = async (id: number, approve: boolean) => {
    await apiClient.post(`/api/records/${id}/approve`, null, { params: { approve } });
    message.success(approve ? '已审批通过' : '已驳回');
    await loadPending();
  };

  const handleSignMeeting = async (id: number) => {
    await apiClient.post(`/api/meetings/${id}/sign`);
    message.success('会议纪要已签批');
    await loadPending();
  };

  const expenseColumns: ColumnsType<PendingExpense> = [
    { title: '费用名称', dataIndex: 'item_name', key: 'item_name' },
    { title: '类型', dataIndex: 'category', key: 'category' },
    { title: '金额', dataIndex: 'amount', key: 'amount' },
    { title: '日期', dataIndex: 'payment_date', key: 'payment_date' },
    { title: '付款人', dataIndex: 'payer', key: 'payer' },
    {
      title: '审批',
      key: 'action',
      render: (_, record) => canApproveExpense ? (
        <>
          <Button type="link" onClick={() => void handleExpenseDecision(record.id, true)}>通过</Button>
          <Button type="link" danger onClick={() => void handleExpenseDecision(record.id, false)}>驳回</Button>
        </>
      ) : '待主管审批',
    },
  ];

  const meetingColumns: ColumnsType<PendingMeeting> = [
    { title: '会议主题', dataIndex: 'title', key: 'title' },
    { title: '时间', dataIndex: 'meeting_time', key: 'meeting_time', render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm') },
    { title: '主持人', dataIndex: 'host', key: 'host' },
    { title: '地点', dataIndex: 'location', key: 'location' },
    { title: '签批', key: 'action', render: (_, record) => canSignMeeting ? <Button type="link" onClick={() => void handleSignMeeting(record.id)}>签批</Button> : '待合伙人签批' },
  ];

  return (
    <Row gutter={16}>
      <Col xs={24} lg={12}>
        <Card title="待审批办公费用">
          <Table rowKey="id" columns={expenseColumns} dataSource={pendingExpenses} loading={loading} pagination={false} />
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card title="待签批会议纪要">
          <Table rowKey="id" columns={meetingColumns} dataSource={pendingMeetings} loading={loading} pagination={false} />
        </Card>
      </Col>
    </Row>
  );
};

export default Approval;
