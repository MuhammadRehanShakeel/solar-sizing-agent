/**
 * StaffLayout.jsx - Side menu (desktop) / drawer (phone) around the installer's pages.
 * Menu items are filtered by role, but the BACKEND enforces the real permissions.
 */
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  AppBar, Avatar, Box, Chip, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Tooltip,
  Typography, useMediaQuery,
} from '@mui/material';
import SurveyIcon from '@mui/icons-material/EventAvailableOutlined';
import DashboardIcon from '@mui/icons-material/SpaceDashboardOutlined';
import LeadsIcon from '@mui/icons-material/PhoneInTalkOutlined';
import ChatsIcon from '@mui/icons-material/ForumOutlined';
import PriceIcon from '@mui/icons-material/SellOutlined';
import UsersIcon from '@mui/icons-material/GroupOutlined';
import AuditIcon from '@mui/icons-material/HistoryOutlined';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/LogoutOutlined';
import OpenIcon from '@mui/icons-material/OpenInNewRounded';
import { logout } from '../store/authSlice';
import { colors } from '../theme';
import Logo from './Logo';

const WIDTH = 236;
const MENU = [
  { to: '/staff', label: 'Dashboard', icon: <DashboardIcon />, roles: ['admin', 'sales'] },
  { to: '/staff/leads', label: 'Leads', icon: <LeadsIcon />, roles: ['admin', 'sales'] },
  { to: '/staff/surveys', label: 'Site surveys', icon: <SurveyIcon />, roles: ['admin', 'sales'] },
  { to: '/staff/chats', label: 'Conversations', icon: <ChatsIcon />, roles: ['admin', 'sales'] },
  { to: '/staff/prices', label: 'Prices', icon: <PriceIcon />, roles: ['admin', 'sales'] },
  { to: '/staff/users', label: 'Staff accounts', icon: <UsersIcon />, roles: ['admin'] },
  { to: '/staff/audit', label: 'Audit log', icon: <AuditIcon />, roles: ['admin'] },
];

export default function StaffLayout() {
  const user = useSelector((s) => s.auth.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const desktop = useMediaQuery('(min-width:900px)');
  const [open, setOpen] = useState(false);

  const menu = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', bgcolor: colors.ink, color: '#fff' }}>
      <Box sx={{ px: 2.5, py: 2.2 }}><Logo light /></Box>
      <List sx={{ px: 1.2, flex: 1 }}>
        {MENU.filter((m) => m.roles.includes(user.role)).map((m) => (
          <ListItemButton key={m.to} component={NavLink} to={m.to} end={m.to === '/staff'} onClick={() => setOpen(false)}
            sx={{ borderRadius: 2, mb: 0.4, color: '#b8c4cf',
              '&.active': { bgcolor: 'rgba(245,158,11,0.16)', color: colors.sun, '& svg': { color: colors.sun } } }}>
            <ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}>{m.icon}</ListItemIcon>
            <ListItemText primary={m.label} primaryTypographyProps={{ fontSize: 14.5, fontWeight: 600 }} />
          </ListItemButton>
        ))}
        <ListItemButton component="a" href="/" target="_blank" sx={{ borderRadius: 2, color: '#b8c4cf' }}>
          <ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}><OpenIcon /></ListItemIcon>
          <ListItemText primary="Customer chat" primaryTypographyProps={{ fontSize: 14.5, fontWeight: 600 }} />
        </ListItemButton>
      </List>
      <Box sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 1.2 }}>
        <Avatar sx={{ bgcolor: colors.sun, color: colors.ink, width: 36, height: 36, fontWeight: 700 }}>
          {user.full_name?.[0]?.toUpperCase()}
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography noWrap fontSize={14} fontWeight={600}>{user.full_name}</Typography>
          <Chip label={user.role} size="small" sx={{ height: 18, fontSize: 11, textTransform: 'capitalize', bgcolor: 'rgba(255,255,255,.12)', color: '#fff' }} />
        </Box>
        <Tooltip title="Log out">
          <IconButton onClick={() => { dispatch(logout()); navigate('/staff/login'); }} size="small" sx={{ color: '#b8c4cf' }}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: colors.bg }}>
      {desktop ? (
        <Drawer variant="permanent" sx={{ width: WIDTH, '& .MuiDrawer-paper': { width: WIDTH, border: 0 } }}>{menu}</Drawer>
      ) : (
        <>
          <AppBar position="fixed" elevation={0} sx={{ bgcolor: '#fff', color: colors.ink, borderBottom: `1px solid ${colors.line}` }}>
            <Toolbar>
              <IconButton edge="start" onClick={() => setOpen(true)} sx={{ mr: 1 }} aria-label="Menu"><MenuIcon /></IconButton>
              <Logo small />
            </Toolbar>
          </AppBar>
          <Drawer open={open} onClose={() => setOpen(false)} sx={{ '& .MuiDrawer-paper': { width: WIDTH } }}>{menu}</Drawer>
        </>
      )}
      <Box component="main" sx={{ flex: 1, minWidth: 0, p: { xs: 2, md: 3.5 }, pt: { xs: 10, md: 3.5 } }}>
        <Outlet />
      </Box>
    </Box>
  );
}
