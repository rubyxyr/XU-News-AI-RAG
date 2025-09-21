import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import Header from './Header';
import Sidebar from './Sidebar';

const Layout = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const sidebarWidth = parseInt(theme.custom?.layout?.sidebarWidth) || 280;
  const headerHeight = parseInt(theme.custom?.layout?.headerHeight) || 64;

  return (
    <Box sx={{ minHeight: '100vh', position: 'relative' }}>
      {/* Header */}
      <AppBar
        position="fixed"
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          height: headerHeight,
          width: '100%',
        }}
      >
        <Header onMenuClick={handleSidebarToggle} />
      </AppBar>

      {/* Sidebar */}
      <Drawer
        variant={isMobile ? 'temporary' : 'persistent'}
        open={sidebarOpen}
        onClose={handleSidebarToggle}
        sx={{
          '& .MuiDrawer-paper': {
            width: sidebarWidth,
            boxSizing: 'border-box',
            top: headerHeight,
            height: `calc(100vh - ${headerHeight}px)`,
            borderRight: `1px solid ${theme.palette.divider}`,
            position: 'fixed',
          },
        }}
        ModalProps={{
          keepMounted: true, // Better performance on mobile
        }}
      >
        <Sidebar onItemClick={isMobile ? handleSidebarToggle : undefined} />
      </Drawer>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          minHeight: '100vh',
          marginLeft: !isMobile && sidebarOpen ? `${sidebarWidth}px` : 0,
          paddingTop: `${headerHeight}px`,
          backgroundColor: theme.palette.background.default,
          transition: theme.transitions.create(['margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Box sx={{ p: 3, maxWidth: '100%' }}>
          <Outlet />
        </Box>
      </Box>

      {/* Mobile backdrop */}
      {isMobile && sidebarOpen && (
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: theme.zIndex.drawer - 1,
          }}
          onClick={handleSidebarToggle}
        />
      )}
    </Box>
  );
};

export default Layout;
