import React from 'react';
import { Card, Col, List, Row, Statistic, Tag } from 'antd';
import { ClockCircleOutlined, DollarOutlined, FolderOpenOutlined, WalletOutlined } from '@ant-design/icons';
import apiClient from '../services/api';

const moduleTips = [
  '考勤按 9:00-12:00 / 14:00-18:00 规则记录，周二固定休息。',
  '工资单仅计算基本工资、补贴、绩效、请假扣款和迟到罚款。',
  '工资计算明确不包含社保和个人所得税。',
  '支出单与工资单都必须走 3 级顺序审批后才能支付。',
];

const formatError = (error: unknown): string => {
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'detail' in error && typeof (error as { detail: unknown }).detail === 'string') {
    return (error as { detail: string }).detail;
  }
  return '加载失败';
};

const Dashboard: React.FC = () => {
  const [data, setData] = React.useState<Record<string, number> | null>(null);
  const [error, setError] = React.useState<string>('');

  React.useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const response = await apiClient.get('/api/dashboard/overview');
        setData(response as Record<string, number>);
      } catch (fetchError) {
        setError(formatError(fetchError));
      }
    };

    fetchDashboard().catch(() => undefined);
  }, []);

  return (
    <div>
      <h1 style={{ marginBottom: 16 }}>经营看板</h1>
      {error ? <Tag color="red">{error}</Tag> : null}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="合同总收入" value={data?.total_income || 0} prefix={<DollarOutlined />} precision={2} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="已确认支出" value={data?.total_approved_expense || 0} prefix={<WalletOutlined />} precision={2} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="净利润" value={data?.net_profit || 0} prefix={<DollarOutlined />} precision={2} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="待审批事项" value={data?.pending_approval_count || 0} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="系统范围">
            <List
              dataSource={[
                `项目数：${data?.project_count || 0}`,
                `工资单数：${data?.salary_slip_count || 0}`,
                '模块：考勤 / 请假 / 会议 / 项目收款 / 办公费用 / 物料库存 / 工资 / 支出支付 / 审计',
              ]}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="关键业务规则" extra={<FolderOpenOutlined />}>
            <List dataSource={moduleTips} renderItem={(item) => <List.Item>{item}</List.Item>} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
