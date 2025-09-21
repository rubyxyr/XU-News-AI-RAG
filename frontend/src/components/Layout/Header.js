import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Toolbar,
  Typography,
  IconButton,
  Box,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  ListItemIcon,
  ListItemText,
  Badge,
  Tooltip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Search as SearchIcon,
  AccountCircle,
  Settings,
  Logout,
  Dashboard,
  Notifications,
} from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { logoutUser } from '../../store/slices/authSlice';

const Header = ({ onMenuClick }) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const [anchorEl, setAnchorEl] = useState(null);

  const handleProfileMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    dispatch(logoutUser());
    handleMenuClose();
    navigate('/login');
  };

  const getInitials = (name) => {
    if (!name) return user?.username?.charAt(0).toUpperCase() || 'U';
    return name
      .split(' ')
      .map((n) => n.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const fullName = user?.first_name && user?.last_name 
    ? `${user.first_name} ${user.last_name}` 
    : user?.username || 'User';

  return (
    <Toolbar sx={{ justifyContent: 'space-between', px: { xs: 1, sm: 3 } }}>
      {/* Left Section */}
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          onClick={onMenuClick}
          edge="start"
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
        
        <Typography
          variant="h6"
          noWrap
          component="div"
          sx={{
            fontWeight: 700,
            background: 'linear-gradient(45deg, #1976D2 30%, #42A5F5 90%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            display: { xs: 'none', sm: 'block' },
          }}
        >
          XU-News AI-RAG
        </Typography>
      </Box>


      {/* Right Section */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {/* Mobile Search */}
        <IconButton
          sx={{ display: { xs: 'block', md: 'none' } }}
          onClick={() => navigate('/search')}
          color="inherit"
        >
          <SearchIcon />
        </IconButton>

        {/* Notifications */}
        <Tooltip title="Notifications">
          <IconButton color="inherit">
            <Badge badgeContent={0} color="error">
              <Notifications />
            </Badge>
          </IconButton>
        </Tooltip>

        {/* Profile Menu */}
        <Tooltip title="Account settings">
          <IconButton onClick={handleProfileMenuOpen} sx={{ p: 0, ml: 1 }}>
            <Avatar
              sx={{
                width: 36,
                height: 36,
                bgcolor: 'primary.main',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              {getInitials(fullName)}
            </Avatar>
          </IconButton>
        </Tooltip>

        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          onClick={handleMenuClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          sx={{
            '& .MuiPaper-root': {
              minWidth: 200,
              mt: 1.5,
            },
          }}
        >
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {fullName}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {user?.email}
            </Typography>
          </Box>

          <Divider />

          <MenuItem onClick={() => navigate('/dashboard')}>
            <ListItemIcon>
              <Dashboard fontSize="small" />
            </ListItemIcon>
            <ListItemText>Dashboard</ListItemText>
          </MenuItem>

          <MenuItem onClick={() => navigate('/profile')}>
            <ListItemIcon>
              <AccountCircle fontSize="small" />
            </ListItemIcon>
            <ListItemText>Profile</ListItemText>
          </MenuItem>

          <MenuItem onClick={() => navigate('/settings')}>
            <ListItemIcon>
              <Settings fontSize="small" />
            </ListItemIcon>
            <ListItemText>Settings</ListItemText>
          </MenuItem>

          <Divider />

          <MenuItem onClick={handleLogout}>
            <ListItemIcon>
              <Logout fontSize="small" />
            </ListItemIcon>
            <ListItemText>Logout</ListItemText>
          </MenuItem>
        </Menu>
      </Box>
    </Toolbar>
  );
};

export default Header;
