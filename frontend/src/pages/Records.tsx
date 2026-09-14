import React from 'react';
import { Card, Space, Statistic, message } from 'antd';
import apiClient from '../services/api';

const Records: React.FC = () => {
  const [summary, setSummary] = React.useState<any>({});

  React.useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await apiClient.get('/api/records/summary');
        setSummary(data);
      } catch {
        message.error('获取综合记录失败');
      }
    };
    fetchSummary();
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
