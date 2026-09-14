import React from 'react';
import { Button, Form, Input, InputNumber, Modal, Space, Table, Tabs, Tag, message } from 'antd';
import apiClient from '../services/api';
import { useAuthStore } from '../store/authStore';

const formatError = (error: unknown): string => {
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'detail' in error && typeof (error as { detail: unknown }).detail === 'string') {
    return (error as { detail: string }).detail;
  }
  return '操作失败';
};

const Approval: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const [pending, setPending] = React.useState<{ salary_slips: any[]; expense_requests: any[]; payment_reviews: any[]; viewer_role?: string }>({
    salary_slips: [],
    expense_requests: [],
    payment_reviews: [],
  });
  const [loading, setLoading] = React.useState(false);
  const [salaryModalId, setSalaryModalId] = React.useState<number | null>(null);
  const [paymentExpenseId, setPaymentExpenseId] = React.useState<number | null>(null);
  const [salaryForm] = Form.useForm();
  const [paymentForm] = Form.useForm();

  const fetchPending = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/approval/pending');
      setPending(response as { salary_slips: any[]; expense_requests: any[]; payment_reviews: any[]; viewer_role?: string });
    } catch (error) {
      message.error(formatError(error));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchPending().catch(() => undefined);
  }, [fetchPending]);

  const postAction = async (url: string, payload: Record<string, unknown>, success: string) => {
    try {
      await apiClient.post(url, payload);
      message.success(success);
      await fetchPending();
    } catch (error) {
      message.error(formatError(error));
    }
  };

  const isCashier = user?.role === 'cashier';
  const canApprove = user?.username === 'admin' || user?.username === 'partner001' || user?.username === 'partner002';
  const canReviewPayment = ['admin', 'finance_admin', 'finance'].includes(user?.role || '');

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Tag color="blue">当前账号：{user?.full_name || user?.username}</Tag>
        <Tag color="purple">角色：{pending.viewer_role || user?.role}</Tag>
      </Space>
      <Tabs
        items={[
          {
            key: 'salary',
            label: '工资审批/发放',
            children: (
              <Table
                rowKey="id"
                loading={loading}
                dataSource={pending.salary_slips}
                columns={[
                  { title: 'ID', dataIndex: 'id' },
                  { title: '工资单号', dataIndex: 'slip_number' },
                  { title: '实发工资', dataIndex: 'net_salary' },
                  { title: '状态', dataIndex: 'status' },
                  {
                    title: '操作',
                    render: (_, record) => (
                      <Space>
                        {canApprove ? (
                          <Button size="small" onClick={() => postAction(`/api/approval/salary-slips/${record.id}/approve`, { approved: true }, '工资单审批成功')}>
                            同意
                          </Button>
                        ) : null}
                        {(user?.role === 'admin' || isCashier) && record.status === '待支付' ? (
                          <Button size="small" type="primary" onClick={() => setSalaryModalId(record.id)}>
                            登记发放
                          </Button>
                        ) : null}
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'expense',
            label: '支出审批/支付',
            children: (
              <Table
                rowKey="id"
                loading={loading}
                dataSource={pending.expense_requests}
                columns={[
                  { title: 'ID', dataIndex: 'id' },
                  { title: '金额', dataIndex: 'amount' },
                  { title: '用途', dataIndex: 'purpose' },
                  { title: '状态', dataIndex: 'status' },
                  {
                    title: '操作',
                    render: (_, record) => (
                      <Space>
                        {canApprove ? (
                          <Button size="small" onClick={() => postAction(`/api/approval/expense-requests/${record.id}/approve`, { approved: true }, '支出单审批成功')}>
                            同意
                          </Button>
                        ) : null}
                        {isCashier && record.status === '待支付' ? (
                          <Button size="small" type="primary" onClick={() => setPaymentExpenseId(record.id)}>
                            填写支付表
                          </Button>
                        ) : null}
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'payment',
            label: '支付复核',
            children: (
              <Table
                rowKey="id"
                loading={loading}
                dataSource={pending.payment_reviews}
                columns={[
                  { title: '支付表ID', dataIndex: 'id' },
                  { title: '支出单ID', dataIndex: 'expense_request_id' },
                  { title: '金额', dataIndex: 'amount' },
                  { title: '状态', dataIndex: 'status' },
                  {
                    title: '操作',
                    render: (_, record) => (
                      canReviewPayment ? (
                        <Button size="small" type="primary" onClick={() => postAction(`/api/approval/payments/${record.id}/review`, { approved: true }, '支付复核完成')}>
                          复核通过
                        </Button>
                      ) : null
                    ),
                  },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal title="登记工资发放" open={salaryModalId !== null} onOk={() => salaryForm.submit()} onCancel={() => setSalaryModalId(null)}>
        <Form
          form={salaryForm}
          layout="vertical"
          onFinish={async (values) => {
            if (!salaryModalId) {
              return;
            }
            await postAction(`/api/approval/salary-slips/${salaryModalId}/pay`, values, '工资发放已记录');
            setSalaryModalId(null);
            salaryForm.resetFields();
          }}
        >
          <Form.Item name="pay_date" label="发放日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="填写支付表" open={paymentExpenseId !== null} onOk={() => paymentForm.submit()} onCancel={() => setPaymentExpenseId(null)}>
        <Form
          form={paymentForm}
          layout="vertical"
          onFinish={async (values) => {
            if (!paymentExpenseId) {
              return;
            }
            await postAction(`/api/approval/expense-requests/${paymentExpenseId}/payment`, values, '支付表已提交');
            setPaymentExpenseId(null);
            paymentForm.resetFields();
          }}
        >
          <Form.Item name="payee" label="收款人" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
          <Form.Item name="payment_method" label="支付方式" rules={[{ required: true }]}><Input placeholder="银行转账 / 现金" /></Form.Item>
          <Form.Item name="payment_date" label="支付日期" rules={[{ required: true }]}><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="attachment" label="支付附件" rules={[{ required: true }]}><Input placeholder="必须上传凭证路径" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Approval;
