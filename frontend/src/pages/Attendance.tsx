import React from 'react';
import { Button, Card, Col, Form, Input, Row, Select, Space, Statistic, Table, message } from 'antd';
import apiClient from '../services/api';

const Attendance: React.FC = () => {
  const [records, setRecords] = React.useState<any[]>([]);
  const [stats, setStats] = React.useState<any>({});
  const [projects, setProjects] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [form] = Form.useForm();

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [recordData, statData, projectData] = await Promise.all([
        apiClient.get('/api/attendance/records'),
        apiClient.get('/api/attendance/statistics'),
        apiClient.get('/api/projects'),
      ]);
      setRecords(recordData);
      setStats(statData);
      setProjects(projectData);
    } catch (error) {
      message.error('获取考勤信息失败');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchAll();
  }, []);

  const handleAction = async (path: string) => {
    try {
      const values = await form.validateFields();
      await apiClient.post(path, values);
      message.success(path.includes('checkin') ? '上班打卡成功' : '下班打卡成功');
      fetchAll();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.detail || '操作失败');
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card title="考勤打卡">
        <Form form={form} layout="inline">
          <Form.Item name="project_id" label="监理工地">
            <Select allowClear style={{ width: 220 }} options={projects.map((item) => ({ value: item.id, label: item.name }))} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input style={{ width: 240 }} placeholder="打卡说明/用途" />
          </Form.Item>
          <Button type="primary" onClick={() => handleAction('/api/attendance/checkin')}>上班打卡</Button>
          <Button onClick={() => handleAction('/api/attendance/checkout')}>下班打卡</Button>
        </Form>
      </Card>

      <Row gutter={16}>
        <Col span={6}><Card><Statistic title="应出勤天数" value={stats.expected_workdays || 0} /></Card></Col>
        <Col span={6}><Card><Statistic title="实际出勤" value={stats.attended_days || 0} /></Card></Col>
        <Col span={6}><Card><Statistic title="出勤率" value={stats.attendance_rate || 0} suffix="%" /></Card></Col>
        <Col span={6}><Card><Statistic title="迟到/早退" value={`${stats.late_count || 0}/${stats.early_leave_count || 0}`} /></Card></Col>
      </Row>

      <Card title="考勤记录">
        <Table
          rowKey="id"
          loading={loading}
          dataSource={records}
          columns={[
            { title: '日期', dataIndex: 'work_date' },
            { title: '员工', dataIndex: 'user_name' },
            { title: '工地', dataIndex: 'project_name' },
            { title: '上班', dataIndex: 'check_in_time' },
            { title: '下班', dataIndex: 'check_out_time' },
            { title: '工时', dataIndex: 'work_hours' },
            { title: '状态', dataIndex: 'status' },
            { title: '迟到(分)', dataIndex: 'late_minutes' },
            { title: '早退(分)', dataIndex: 'early_leave_minutes' },
          ]}
        />
      </Card>
    </Space>
  );
};

export default Attendance;
