import React from 'react';
import { Button, Card, Checkbox, Col, DatePicker, Form, Input, message, Row, Select, Space, Statistic, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import apiClient from '../services/api';
import { useAuthStore } from '../store/authStore';

interface UserOption {
  id: number;
  full_name: string;
}

interface ProjectOption {
  id: number;
  name: string;
}

interface AttendanceRecordItem {
  id: number;
  user_name: string;
  attendance_date: string;
  check_in_time?: string;
  check_out_time?: string;
  project_name?: string;
  is_supervisor_record: boolean;
  is_late: boolean;
  is_early_leave: boolean;
  notes?: string;
}

interface AttendanceStats {
  summary: {
    attendance_rate: number;
    late_count: number;
    early_leave_count: number;
    absent_days: number;
  };
}

const Attendance: React.FC = () => {
  const { user, token } = useAuthStore();
  const [records, setRecords] = React.useState<AttendanceRecordItem[]>([]);
  const [users, setUsers] = React.useState<UserOption[]>([]);
  const [projects, setProjects] = React.useState<ProjectOption[]>([]);
  const [stats, setStats] = React.useState<AttendanceStats | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [form] = Form.useForm();
  const monthStart = dayjs().startOf('month').format('YYYY-MM-DD');
  const today = dayjs().format('YYYY-MM-DD');

  const loadData = React.useCallback(async () => {
    try {
      setLoading(true);
      const [recordData, userOptions, projectData, statsData] = await Promise.all([
        apiClient.get('/api/attendance'),
        apiClient.get('/api/users/options'),
        apiClient.get('/api/projects'),
        apiClient.get('/api/attendance/statistics', { params: { start_date: monthStart, end_date: today } }),
      ]);
      setRecords(recordData);
      setUsers(userOptions);
      setProjects(projectData);
      setStats(statsData);
    } catch (error) {
      message.error('加载考勤数据失败');
    } finally {
      setLoading(false);
    }
  }, [monthStart, today]);

  React.useEffect(() => {
    void loadData();
    form.setFieldsValue({ user_id: user?.id, attendance_date: dayjs() });
  }, [form, loadData, user?.id]);

  const handleSubmit = async (values: any) => {
    try {
      await apiClient.post('/api/attendance', {
        ...values,
        attendance_date: values.attendance_date.format('YYYY-MM-DD'),
        check_in_time: values.check_in_time ? values.check_in_time.toISOString() : null,
        check_out_time: values.check_out_time ? values.check_out_time.toISOString() : null,
      });
      message.success('考勤记录已保存');
      form.resetFields();
      form.setFieldsValue({ user_id: user?.id, attendance_date: dayjs() });
      await loadData();
    } catch (error: any) {
      message.error(error?.detail || '保存考勤失败');
    }
  };

  const handleExport = async () => {
    try {
      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/attendance/export?start_date=${monthStart}&end_date=${today}`, {
        headers: token ? { Authorization: 'Bearer ' + token } : {},
      });
      if (!response.ok) {
        throw new Error('导出失败');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `attendance_${monthStart}_${today}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      message.error('导出考勤报表失败');
    }
  };

  const columns: ColumnsType<AttendanceRecordItem> = [
    { title: '员工', dataIndex: 'user_name', key: 'user_name' },
    { title: '日期', dataIndex: 'attendance_date', key: 'attendance_date' },
    { title: '上班打卡', dataIndex: 'check_in_time', key: 'check_in_time', render: (value?: string) => value ? dayjs(value).format('HH:mm') : '-' },
    { title: '下班打卡', dataIndex: 'check_out_time', key: 'check_out_time', render: (value?: string) => value ? dayjs(value).format('HH:mm') : '-' },
    { title: '工地', dataIndex: 'project_name', key: 'project_name', render: (value?: string) => value || '-' },
    { title: '监理打卡', dataIndex: 'is_supervisor_record', key: 'is_supervisor_record', render: (value: boolean) => value ? '是' : '否' },
    { title: '迟到/早退', key: 'status', render: (_, record) => `${record.is_late ? '迟到' : '正常'} / ${record.is_early_leave ? '早退' : '正常'}` },
    { title: '备注', dataIndex: 'notes', key: 'notes', render: (value?: string) => value || '-' },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col xs={24} md={6}><Card><Statistic title="本月出勤率" value={stats?.summary.attendance_rate || 0} suffix="%" /></Card></Col>
        <Col xs={24} md={6}><Card><Statistic title="迟到次数" value={stats?.summary.late_count || 0} /></Card></Col>
        <Col xs={24} md={6}><Card><Statistic title="早退次数" value={stats?.summary.early_leave_count || 0} /></Card></Col>
        <Col xs={24} md={6}><Card><Statistic title="旷工天数" value={stats?.summary.absent_days || 0} /></Card></Col>
      </Row>

      <Card title="新增考勤记录" extra={<Button onClick={handleExport}>导出本月报表</Button>}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item name="user_id" label="员工" rules={[{ required: true, message: '请选择员工' }]}>
                <Select options={users.map((item) => ({ label: item.full_name, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="attendance_date" label="考勤日期" rules={[{ required: true, message: '请选择日期' }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="project_id" label="监理工地">
                <Select allowClear options={projects.map((item) => ({ label: item.name, value: item.id }))} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="check_in_time" label="上班打卡">
                <DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="check_out_time" label="下班打卡">
                <DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="is_supervisor_record" valuePropName="checked" label=" ">
                <Checkbox>监理打卡专用记录</Checkbox>
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="notes" label="备注">
                <Input.TextArea rows={2} placeholder="例如：工地巡检、外出量房" />
              </Form.Item>
            </Col>
          </Row>
          <Button type="primary" htmlType="submit">保存考勤</Button>
        </Form>
      </Card>

      <Card title="考勤记录">
        <Table rowKey="id" columns={columns} dataSource={records} loading={loading} pagination={{ pageSize: 8 }} />
      </Card>
    </Space>
  );
};

export default Attendance;
