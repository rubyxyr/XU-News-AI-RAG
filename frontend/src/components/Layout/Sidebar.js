import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
  Chip,
  Collapse,
} from '@mui/material';
import {
  Dashboard,
  Search,
  Description,
  Analytics,
  RssFeed,
  Settings,
  ExpandLess,
  ExpandMore,
  TrendingUp,
} from '@mui/icons-material';
import { useAppSelector } from '../../hooks/redux';
import {
  fetchDocumentStats,
  selectDocumentStats,
  selectDocumentsLoading,
} from '../../store/slices/documentsSlice';
import {
  fetchSourceStats,
  selectSourcesStats,
  selectSourcesLoading,
} from '../../store/slices/sourcesSlice';

const Sidebar = ({ onItemClick }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAppSelector((state) => state.auth);
  
  // Redux state
  const documentStats = useAppSelector(selectDocumentStats);
  const sourceStats = useAppSelector(selectSourcesStats);
  const documentsLoading = useAppSelector(selectDocumentsLoading);
  const sourcesLoading = useAppSelector(selectSourcesLoading);
  
  const [quickStatsOpen, setQuickStatsOpen] = React.useState(true);

  // Fetch data on component mount
  useEffect(() => {
    console.log('📊 Sidebar: Loading real stats data...');
    dispatch(fetchDocumentStats());
    dispatch(fetchSourceStats());
  }, [dispatch]);
  
  // Navigation items configuration with real data
  const mainNavItems = [
    {
      text: 'Dashboard',
      icon: <Dashboard />,
      path: '/dashboard',
      badge: null,
    },
    {
      text: 'Search',
      icon: <Search />,
      path: '/search',
      badge: null,
    },
    {
      text: 'Documents',
      icon: <Description />,
      path: '/documents',
      badge: documentsLoading ? '...' : (documentStats?.total_documents || 0).toLocaleString(),
    },
    {
      text: 'Sources',
      icon: <RssFeed />,
      path: '/sources',
      badge: sourcesLoading ? '...' : (sourceStats?.total_sources || 0).toString(),
    },
    {
      text: 'Analytics',
      icon: <Analytics />,
      path: '/analytics',
      badge: null,
    },
  ];

  const secondaryNavItems = [
    {
      text: 'Settings',
      icon: <Settings />,
      path: '/settings',
      badge: null,
    },
  ];


  const handleNavigation = (path) => {
    navigate(path);
    if (onItemClick) {
      onItemClick();
    }
  };

  const isCurrentPath = (path) => {
    return location.pathname === path || 
           (path === '/dashboard' && location.pathname === '/');
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Main Navigation */}
      <List sx={{ pt: 2 }}>
        {mainNavItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={isCurrentPath(item.path)}
              onClick={() => handleNavigation(item.path)}
              sx={{
                mx: 1,
                borderRadius: 2,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'white',
                  '& .MuiListItemIcon-root': {
                    color: 'white',
                  },
                  '&:hover': {
                    backgroundColor: 'primary.dark',
                  },
                },
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
              {item.badge && (
                <Chip
                  label={item.badge}
                  size="small"
                  sx={{
                    fontSize: '0.75rem',
                    height: 20,
                    backgroundColor: isCurrentPath(item.path) ? 'rgba(255,255,255,0.2)' : 'action.hover',
                    color: isCurrentPath(item.path) ? 'white' : 'text.secondary',
                  }}
                />
              )}
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      <Divider sx={{ mx: 2, my: 1 }} />

      {/* Quick Stats */}
      <List>
        <ListItem>
          <ListItemButton
            onClick={() => setQuickStatsOpen(!quickStatsOpen)}
            sx={{ px: 2 }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>
              <TrendingUp />
            </ListItemIcon>
            <ListItemText primary="Quick Stats" />
            {quickStatsOpen ? <ExpandLess /> : <ExpandMore />}
          </ListItemButton>
        </ListItem>
        
        <Collapse in={quickStatsOpen} timeout="auto" unmountOnExit>
          <Box sx={{ px: 3, py: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Documents
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                {documentsLoading ? '...' : (documentStats?.total_documents || 0).toLocaleString()}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Searches
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                0
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Sources
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                {sourcesLoading ? '...' : (sourceStats?.total_sources || 0)}
              </Typography>
            </Box>
          </Box>
        </Collapse>
      </List>


      {/* Bottom Navigation */}
      <List sx={{ mt: 'auto', pb: 2 }}>
        <Divider sx={{ mx: 2, mb: 1 }} />
        {secondaryNavItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={isCurrentPath(item.path)}
              onClick={() => handleNavigation(item.path)}
              sx={{
                mx: 1,
                borderRadius: 2,
                '&.Mui-selected': {
                  backgroundColor: 'primary.main',
                  color: 'white',
                  '& .MuiListItemIcon-root': {
                    color: 'white',
                  },
                },
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default Sidebar;
