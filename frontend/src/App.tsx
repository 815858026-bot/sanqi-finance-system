import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Attendance from './pages/Attendance';
import Meetings from './pages/Meetings';
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
              <Route path="/attendance" element={<Attendance />} />
              <Route path="/meetings" element={<Meetings />} />
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
