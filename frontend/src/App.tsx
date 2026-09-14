import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Records from './pages/Records';
import Approval from './pages/Approval';
import Admin from './pages/Admin';
import { useAuthStore } from './store/authStore';

function App() {
  const { token } = useAuthStore();

  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <Routes>
          {!token ? (
            <Route path="/login" element={<Login />} />
          ) : (
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/records" element={<Records />} />
              <Route path="/approval" element={<Approval />} />
              <Route path="/admin" element={<Admin />} />
            </Route>
          )}
          <Route path="*" element={<Navigate to={token ? '/dashboard' : '/login'} replace />} />
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
