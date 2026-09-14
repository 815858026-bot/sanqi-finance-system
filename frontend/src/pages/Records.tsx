import React from 'react';
import { Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Table, Tabs, message } from 'antd';
import apiClient from '../services/api';

const formatError = (error: unknown): string => {
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'detail' in error && typeof (error as { detail: unknown }).detail === 'string') {
    return (error as { detail: string }).detail;
  }
  return '操作失败';
};

const Records: React.FC = () => {
  const [attendance, setAttendance] = React.useState<any[]>([]);
  const [leaves, setLeaves] = React.useState<any[]>([]);
  const [meetings, setMeetings] = React.useState<any[]>([]);
  const [expenses, setExpenses] = React.useState<any[]>([]);
  const [materials, setMaterials] = React.useState<any[]>([]);
  const [salaryConfigs, setSalaryConfigs] = React.useState<any[]>([]);
  const [salarySlips, setSalarySlips] = React.useState<any[]>([]);
  const [expenseRequests, setExpenseRequests] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);

  const fetchAll = React.useCallback(async () => {
    try {
      setLoading(true);
      const [attendanceRes, leaveRes, meetingRes, expenseRes, materialRes, configRes, slipRes, requestRes] = await Promise.all([
        apiClient.get('/api/records/attendance'),
        apiClient.get('/api/records/leaves'),
        apiClient.get('/api/records/meetings'),
        apiClient.get('/api/records/office-expenses'),
        apiClient.get('/api/records/materials'),
        apiClient.get('/api/records/salary-configs'),
        apiClient.get('/api/records/salary-slips'),
        apiClient.get('/api/records/expense-requests'),
      ]);
      setAttendance((attendanceRes as any[]) || []);
      setLeaves((leaveRes as any[]) || []);
      setMeetings((meetingRes as any[]) || []);
      setExpenses((expenseRes as any[]) || []);
      setMaterials((materialRes as any[]) || []);
      setSalaryConfigs((configRes as any[]) || []);
      setSalarySlips((slipRes as any[]) || []);
      setExpenseRequests((requestRes as any[]) || []);
    } catch (error) {
      message.error(formatError(error));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchAll().catch(() => undefined);
  }, [fetchAll]);

  const submit = async (url: string, values: Record<string, unknown>, success: string) => {
    try {
      await apiClient.post(url, values);
      message.success(success);
      await fetchAll();
    } catch (error) {
      message.error(formatError(error));
    }
  };

  return (
    <Tabs
      items={[
        {
          key: 'attendance',
          label: '考勤',
          children: (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <Card title="录入打卡">
                  <Form layout="vertical" onFinish={(values) => submit('/api/records/attendance', values, '考勤已保存')}>
                    <Form.Item name="employee_id" label="员工ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
                    <Form.Item name="work_date" label="日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
                    <Form.Item name="check_in" label="上班打卡"><Input placeholder="09:00:00" /></Form.Item>
                    <Form.Item name="check_out" label="下班打卡"><Input placeholder="18:00:00" /></Form.Item>
                    <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
                    <Button type="primary" htmlType="submit" block>保存</Button>
                  </Form>
                </Card>
              </Col>
              <Col xs={24} lg={16}>
                <Table rowKey="id" loading={loading} dataSource={attendance} columns={[
                  { title: '员工ID', dataIndex: 'employee_id' },
                  { title: '日期', dataIndex: 'work_date' },
                  { title: '上班', dataIndex: 'check_in' },
                  { title: '下班', dataIndex: 'check_out' },
                  { title: '出勤天数', dataIndex: 'attendance_days' },
                  { title: '迟到', dataIndex: 'is_late', render: (value: boolean) => (value ? '是' : '否') },
                  { title: '早退', dataIndex: 'is_early_leave', render: (value: boolean) => (value ? '是' : '否') },
                ]} />
              </Col>
            </Row>
          ),
        },
        {
          key: 'leave',
          label: '请假',
          children: (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <Card title="记录请假">
                  <Form layout="vertical" onFinish={(values) => submit('/api/records/leaves', values, '请假已记录')} initialValues={{ leave_type: '事假', unit: 'day' }}>
                    <Form.Item name="employee_id" label="员工ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
                    <Form.Item name="leave_date" label="请假日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
                    <Form.Item name="leave_type" label="类型" rules={[{ required: true }]}>
                      <Select options={['病假', '事假', '婚假', '产假', '陪产假', '丧假', '无薪假'].map((value) => ({ label: value, value }))} />
                    </Form.Item>
                    <Form.Item name="unit" label="单位" rules={[{ required: true }]}>
                      <Select options={[{ label: '按天', value: 'day' }, { label: '按小时', value: 'hour' }]} />
                    </Form.Item>
                    <Form.Item name="quantity" label="数量"><InputNumber style={{ width: '100%' }} min={0} step={0.5} /></Form.Item>
                    <Form.Item name="start_time" label="开始时间"><Input placeholder="14:00:00" /></Form.Item>
                    <Form.Item name="end_time" label="结束时间"><Input placeholder="18:00:00" /></Form.Item>
                    <Form.Item name="reason" label="说明"><Input.TextArea rows={2} /></Form.Item>
                    <Button type="primary" htmlType="submit" block>保存</Button>
                  </Form>
                </Card>
              </Col>
              <Col xs={24} lg={16}>
                <Table rowKey="id" loading={loading} dataSource={leaves} columns={[
                  { title: '员工ID', dataIndex: 'employee_id' },
                  { title: '日期', dataIndex: 'leave_date' },
                  { title: '类型', dataIndex: 'leave_type' },
                  { title: '单位', dataIndex: 'unit' },
                  { title: '数量', dataIndex: 'quantity' },
                  { title: '原因', dataIndex: 'reason' },
                ]} />
              </Col>
            </Row>
          ),
        },
        {
          key: 'meeting',
          label: '会议纪要',
          children: (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={9}>
                <Card title="创建会议">
                  <Form layout="vertical" onFinish={(values) => submit('/api/records/meetings', values, '会议纪要已存档')}>
                    <Form.Item name="meeting_time" label="会议时间" rules={[{ required: true }]}><Input placeholder="2026-09-14T10:00:00" /></Form.Item>
                    <Form.Item name="location" label="地点" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item name="participants" label="参与人" rules={[{ required: true }]}><Input /></Form.Item>
                    <Form.Item name="agenda" label="议题" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item>
                    <Form.Item name="decision" label="决议" rules={[{ required: true }]}><Input.TextArea rows={3} /></Form.Item>
                    <Button type="primary" htmlType="submit" block>保存</Button>
                  </Form>
                </Card>
              </Col>
              <Col xs={24} lg={15}>
                <Table rowKey="id" loading={loading} dataSource={meetings} columns={[
                  { title: '时间', dataIndex: 'meeting_time' },
                  { title: '地点', dataIndex: 'location' },
                  { title: '参与人', dataIndex: 'participants' },
                  { title: '议题', dataIndex: 'agenda' },
                ]} />
              </Col>
            </Row>
          ),
        },
        {
          key: 'expense',
          label: '办公费用 / 支出单',
          children: (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <Space direction="vertical" style={{ width: '100%' }} size={16}>
                  <Card title="录入办公费用">
                    <Form layout="vertical" onFinish={(values) => submit('/api/records/office-expenses', values, '办公费用已记录')}>
                      <Form.Item name="category" label="分类" rules={[{ required: true }]}><Input placeholder="房租 / 物业 / 水电网" /></Form.Item>
                      <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="expense_date" label="日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
                      <Form.Item name="description" label="说明"><Input.TextArea rows={2} /></Form.Item>
                      <Button type="primary" htmlType="submit" block>保存</Button>
                    </Form>
                  </Card>
                  <Card title="创建支出单">
                    <Form layout="vertical" onFinish={(values) => submit('/api/records/expense-requests', values, '支出单已创建')}>
                      <Form.Item name="project_id" label="项目ID"><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="purpose" label="用途" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item>
                      <Form.Item name="invoice_attachment" label="发票附件路径"><Input /></Form.Item>
                      <Button type="primary" htmlType="submit" block>提交</Button>
                    </Form>
                  </Card>
                </Space>
              </Col>
              <Col xs={24} lg={16}>
                <Card title="办公费用">
                  <Table rowKey="id" pagination={false} loading={loading} dataSource={expenses} columns={[
                    { title: '分类', dataIndex: 'category' },
                    { title: '金额', dataIndex: 'amount' },
                    { title: '日期', dataIndex: 'expense_date' },
                    { title: '说明', dataIndex: 'description' },
                  ]} />
                </Card>
                <Card title="支出单" style={{ marginTop: 16 }}>
                  <Table rowKey="id" loading={loading} dataSource={expenseRequests} columns={[
                    { title: 'ID', dataIndex: 'id' },
                    { title: '项目ID', dataIndex: 'project_id' },
                    { title: '金额', dataIndex: 'amount' },
                    { title: '用途', dataIndex: 'purpose' },
                    { title: '状态', dataIndex: 'status' },
                  ]} />
                </Card>
              </Col>
            </Row>
          ),
        },
        {
          key: 'inventory',
          label: '物料库存',
          children: (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <Space direction="vertical" style={{ width: '100%' }} size={16}>
                  <Card title="创建物料">
                    <Form layout="vertical" onFinish={(values) => submit('/api/records/materials', values, '物料已创建')}>
                      <Form.Item name="name" label="物料名" rules={[{ required: true }]}><Input /></Form.Item>
                      <Form.Item name="unit" label="单位"><Input /></Form.Item>
                      <Form.Item name="minimum_stock" label="预警库存"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Button type="primary" htmlType="submit" block>保存</Button>
                    </Form>
                  </Card>
                  <Card title="物料入库">
                    <Form layout="vertical" onFinish={(values) => submit('/api/records/materials/stock-in', values, '入库成功')}>
                      <Form.Item name="material_id" label="物料ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="project_id" label="项目ID"><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="supplier" label="供应商" rules={[{ required: true }]}><Input /></Form.Item>
                      <Form.Item name="purchase_date" label="采购日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
                      <Form.Item name="unit_price" label="单价" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="quantity" label="数量" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="invoice_attachment" label="采购发票"><Input /></Form.Item>
                      <Button type="primary" htmlType="submit" block>入库</Button>
                    </Form>
                  </Card>
                  <Card title="物料出库">
                    <Form layout="vertical" onFinish={(values) => submit('/api/records/materials/stock-out', values, '出库成功')}>
                      <Form.Item name="material_id" label="物料ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="project_id" label="项目ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="employee_id" label="领用人ID"><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="usage_date" label="出库日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
                      <Form.Item name="quantity" label="数量" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
                      <Button type="primary" htmlType="submit" block>出库</Button>
                    </Form>
                  </Card>
                </Space>
              </Col>
              <Col xs={24} lg={16}>
                <Table rowKey="id" loading={loading} dataSource={materials} columns={[
                  { title: 'ID', dataIndex: 'id' },
                  { title: '物料', dataIndex: 'name' },
                  { title: '单位', dataIndex: 'unit' },
                  { title: '当前库存', dataIndex: 'current_stock' },
                  { title: '预警库存', dataIndex: 'minimum_stock' },
                  { title: '是否预警', dataIndex: 'low_stock', render: (value: boolean) => (value ? '是' : '否') },
                ]} />
              </Col>
            </Row>
          ),
        },
        {
          key: 'salary',
          label: '工资核算',
          children: (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <Space direction="vertical" style={{ width: '100%' }} size={16}>
                  <Card title="工资配置">
                    <Form layout="vertical" onFinish={(values) => submit('/api/records/salary-configs', values, '工资配置已创建')} initialValues={{ is_sick_leave_paid: true, is_personal_leave_paid: false }}>
                      <Form.Item name="employee_id" label="员工ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="job_title" label="职位" rules={[{ required: true }]}><Input /></Form.Item>
                      <Form.Item name="base_salary" label="基本工资" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="position_allowance" label="职位补贴"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="performance_bonus" label="绩效奖金"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="late_penalty" label="迟到罚款"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
                      <Form.Item name="is_sick_leave_paid" label="病假带薪" rules={[{ required: true }]}><Select options={[{ label: '是', value: true }, { label: '否', value: false }]} /></Form.Item>
                      <Form.Item name="is_personal_leave_paid" label="事假带薪" rules={[{ required: true }]}><Select options={[{ label: '是', value: true }, { label: '否', value: false }]} /></Form.Item>
                      <Button type="primary" htmlType="submit" block>保存</Button>
                    </Form>
                  </Card>
                  <Card title="月度工资计算">
                    <Form layout="vertical" onFinish={(values) => submit('/api/records/salary-slips/calculate', values, '工资单已生成')}>
                      <Form.Item name="employee_id" label="员工ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
                      <Form.Item name="year_month" label="年月" rules={[{ required: true }]}><Input placeholder="YYYY-MM" /></Form.Item>
                      <Form.Item name="remark" label="备注"><Input.TextArea rows={2} placeholder="默认不计算社保和个税" /></Form.Item>
                      <Button type="primary" htmlType="submit" block>开始计算</Button>
                    </Form>
                  </Card>
                </Space>
              </Col>
              <Col xs={24} lg={16}>
                <Card title="工资配置列表">
                  <Table rowKey="id" pagination={false} loading={loading} dataSource={salaryConfigs} columns={[
                    { title: '员工ID', dataIndex: 'employee_id' },
                    { title: '职位', dataIndex: 'job_title' },
                    { title: '基本工资', dataIndex: 'base_salary' },
                    { title: '日工资', dataIndex: 'daily_salary' },
                    { title: '时薪', dataIndex: 'hourly_salary' },
                  ]} />
                </Card>
                <Card title="工资单列表" style={{ marginTop: 16 }} extra="不计算社保和个税">
                  <Table rowKey="id" loading={loading} dataSource={salarySlips} columns={[
                    { title: '单号', dataIndex: 'slip_number' },
                    { title: '员工ID', dataIndex: 'employee_id' },
                    { title: '年月', dataIndex: 'year_month' },
                    { title: '应发', dataIndex: 'gross_income' },
                    { title: '请假扣款', dataIndex: 'leave_deduction' },
                    { title: '迟到罚款', dataIndex: 'late_penalty_amount' },
                    { title: '个税', dataIndex: 'personal_income_tax' },
                    { title: '社保', dataIndex: 'social_insurance' },
                    { title: '实发', dataIndex: 'net_salary' },
                    { title: '状态', dataIndex: 'status' },
                  ]} />
                </Card>
              </Col>
            </Row>
          ),
        },
      ]}
    />
  );
};

export default Records;
