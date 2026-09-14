import React from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, DollarOutlined, FileTextOutlined } from '@ant-design/icons';

import apiClient from '../services/api';

interface DashboardData {
  total_income: number;
  total_approved_expense: number;
  net_profit: number;
  pending_approval_count: number;
  attendance_rate: number;
  meeting_count: number;
  receivable_total: number;
  outstanding_total: number;
}

const Dashboard: React.FC = () => {
  const [data, setData] = React.useState<DashboardData | null>(null);

  React.useEffect(() => {
    const fetchDashboard = async () => {
      const response = await apiClient.get('/api/dashboard/overview');
      setData(response);
    };
    void fetchDashboard();
  }, []);

  return (
    <div>
      <h1>财务看板</h1>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="已收款" value={data?.total_income || 0} prefix={<DollarOutlined />} precision={2} /></Card></Col>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="已批准办公费用" value={data?.total_approved_expense || 0} prefix={<DollarOutlined />} precision={2} /></Card></Col>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="净利润" value={data?.net_profit || 0} prefix={<DollarOutlined />} precision={2} /></Card></Col>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="待审批事项" value={data?.pending_approval_count || 0} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="本月出勤率" value={data?.attendance_rate || 0} suffix="%" prefix={<CheckCircleOutlined />} /></Card></Col>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="会议纪要总数" value={data?.meeting_count || 0} prefix={<FileTextOutlined />} /></Card></Col>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="项目应收总额" value={data?.receivable_total || 0} prefix={<DollarOutlined />} precision={2} /></Card></Col>
        <Col xs={24} sm={12} md={6}><Card><Statistic title="项目未收总额" value={data?.outstanding_total || 0} prefix={<DollarOutlined />} precision={2} /></Card></Col>
      </Row>
    </div>
  );
};

export default Dashboard;
