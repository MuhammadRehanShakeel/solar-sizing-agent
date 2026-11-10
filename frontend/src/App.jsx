/**
 * App.jsx - Which page is shown for which address.
 *   Customers (no login): /  /advisor  /calculator  /backup  /survey  /quote/<token>
 *   Staff (login):        /staff/...
 */
import { Navigate, Route, Routes } from 'react-router-dom';
import { useSelector } from 'react-redux';
import SiteLayout from './components/SiteLayout';
import Home from './pages/Home';
import Chat from './pages/Chat';
import Calculator from './pages/Calculator';
import BackupPlanner from './pages/BackupPlanner';
import Survey from './pages/Survey';
import QuotePage from './pages/QuotePage';
import StaffLayout from './components/StaffLayout';
import Login from './pages/staff/Login';
import Dashboard from './pages/staff/Dashboard';
import Leads from './pages/staff/Leads';
import Surveys from './pages/staff/Surveys';
import Chats from './pages/staff/Chats';
import Prices from './pages/staff/Prices';
import Users from './pages/staff/Users';
import Audit from './pages/staff/Audit';

function Staff({ admin = false, children }) {
  const user = useSelector((s) => s.auth.user);
  if (!user) return <Navigate to="/staff/login" replace />;
  if (admin && user.role !== 'admin') return <Navigate to="/staff" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route element={<SiteLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/calculator" element={<Calculator />} />
        <Route path="/backup" element={<BackupPlanner />} />
        <Route path="/survey" element={<Survey />} />
        <Route path="/quote/:token" element={<QuotePage />} />
      </Route>
      <Route element={<SiteLayout fullHeight />}>
        <Route path="/advisor" element={<Chat />} />
      </Route>
      <Route path="/staff/login" element={<Login />} />
      <Route path="/staff" element={<Staff><StaffLayout /></Staff>}>
        <Route index element={<Dashboard />} />
        <Route path="leads" element={<Leads />} />
        <Route path="surveys" element={<Surveys />} />
        <Route path="chats" element={<Chats />} />
        <Route path="prices" element={<Prices />} />
        <Route path="users" element={<Staff admin><Users /></Staff>} />
        <Route path="audit" element={<Staff admin><Audit /></Staff>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
