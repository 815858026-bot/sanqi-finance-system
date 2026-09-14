import React from 'react';
import { Card, Space, Statistic, message } from 'antd';
import apiClient from '../services/api';

const Records: React.FC = () => {
  const [summary, setSummary] = React.useState<any>({});

  React.useEffect(() => {
    apiClient.get('/api/records/summary').then(setSummary).catch(() => message.error('获取综合记录失败'));
  }, []);

  return (
    <Space wrap>
      <Card><Statistic title="办公费用记录" value={summary.office_expense_count || 0} /></Card>
      <Card><Statistic title="物料入库记录" value={summary.material_inbound_count || 0} /></Card>
      <Card><Statistic title="物料领用记录" value={summary.material_outbound_count || 0} /></Card>
    </Space>
  );
};

export default Records;
