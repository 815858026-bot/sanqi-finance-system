import React from 'react';
import { Avatar, Button, Dropdown, Layout, Menu, Tag } from 'antd';
import { LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined, UserOutlined } from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const { Header, Sider, Content } = Layout;

type MenuItem = {
  key: string;
  label: string;
  roles?: string[];
};

const MENU_ITEMS: MenuItem[] = [
  { key: '/dashboard', label: '财务看板' },
  { key: '/projects', label: '项目收款' },
  { key: '/records', label: '考勤/工资/库存' },
  { key: '/approval', label: '审批与支付' },
  { key: '/admin', label: '用户与审计', roles: ['admin', 'partner', 'finance_admin', 'finance', 'cashier'] },
];

const roleText: Record<string, string> = {
  admin: '超级管理员',
  partner: '合伙人',
  finance_admin: '财务主管',
  finance: '财务人员',
  cashier: '出纳',
};

const LayoutComponent: React.FC = () => {
  const [collapsed, setCollapsed] = React.useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const menuItems = MENU_ITEMS.filter((item) => !item.roles || item.roles.includes(user?.role)).map((item) => ({
    key: item.key,
    label: item.label,
  }));

  const userMenu = [
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ];

  const handleMenuClick = (e: { key: string }) => {
    if (e.key === 'logout') {
      logout();
      navigate('/login');
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div
          style={{
            color: '#fff',
            fontSize: 18,
            fontWeight: 700,
            padding: '20px 16px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          三七设计
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={(e) => navigate(e.key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Tag color="blue">{roleText[user?.role || 'finance'] || user?.role}</Tag>
            <span>{user?.full_name || user?.username}</span>
            <Dropdown menu={{ items: userMenu, onClick: handleMenuClick }}>
              <Avatar style={{ backgroundColor: '#87d068', cursor: 'pointer' }} icon={<UserOutlined />} />
            </Dropdown>
          </div>
        </Header>
        <Content style={{ margin: '16px' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default LayoutComponent;
