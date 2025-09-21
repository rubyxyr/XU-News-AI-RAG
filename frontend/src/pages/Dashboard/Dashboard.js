import React, { useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Chip,
  IconButton,
  InputAdornment,
  Skeleton,
} from '@mui/material';
import {
  Search as SearchIcon,
  TrendingUp,
  Description,
  Source,
  Analytics,
  Add,
  Article,
  ArrowForward,
  LocalOffer,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import apiService from '../../services/apiService';
import { useAppSelector } from '../../hooks/redux';
import {
  fetchDocumentStats,
  fetchRecentDocuments,
  selectDocumentStats,
  selectRecentDocuments,
  selectDocumentsLoading,
  selectDocumentsError,
} from '../../store/slices/documentsSlice';
import {
  fetchSourceStats,
  selectSourcesStats,
  selectSourcesLoading,
  selectSourcesError,
} from '../../store/slices/sourcesSlice';
import {
  fetchKeywords,
  fetchSearchAnalytics,
  selectTopKeywords,
  selectTopPopularQueries,
  selectSearchAnalytics,
  selectAnalyticsLoading,
} from '../../store/slices/analyticsSlice';

const Dashboard = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useAppSelector((state) => state.auth);
  
  // Redux state selectors
  const documentStats = useAppSelector(selectDocumentStats);
  const sourceStats = useAppSelector(selectSourcesStats);
  const recentDocs = useAppSelector(selectRecentDocuments);
  const topKeywords = useAppSelector(selectTopKeywords);
  const popularQueries = useAppSelector(selectTopPopularQueries);
  const searchAnalytics = useAppSelector(selectSearchAnalytics);
  const documentsLoading = useAppSelector(selectDocumentsLoading);
  const sourcesLoading = useAppSelector(selectSourcesLoading);
  const analyticsLoading = useAppSelector(selectAnalyticsLoading);
  // const documentsError = useAppSelector(selectDocumentsError);
  // const sourcesError = useAppSelector(selectSourcesError);
  
  const [searchQuery, setSearchQuery] = React.useState('');
  const [trendingKeywords, setTrendingKeywords] = React.useState([]);
  const [keywordsLoading, setKeywordsLoading] = React.useState(false);
  
  // Computed stats from Redux state
  const stats = {
    totalDocuments: documentStats?.total_documents || 0,
    totalSearches: searchAnalytics?.total_searches || 0,
    activeSources: sourceStats?.active_sources || 0,
  };

  const loading = documentsLoading || sourcesLoading || analyticsLoading;

  // Transform recent documents into activity format
  const recentActivity = recentDocs.map((doc, index) => ({
    id: doc.id,
    type: 'document',
    title: doc.title,
    description: `From ${doc.source_name || 'Unknown Source'}`,
    timestamp: doc.created_at ? new Date(doc.created_at).toLocaleString() : 'Recently',
    source: doc.source_type || 'Document',
  }));

  // Transform popular queries from Redux store  
  const trendingQueries = popularQueries.map((queryData) => ({
    name: queryData.query || 'Unknown Query',
    count: queryData.count || 0,
    trend: queryData.avg_search_time ? `${queryData.avg_search_time.toFixed(2)}s` : '0s',
  }));

  // Fetch trending keywords
  const fetchTrendingKeywords = async () => {
    try {
      setKeywordsLoading(true);
      const response = await apiService.tags.getTrending({ limit: 10 });
      setTrendingKeywords(response.data.trending_keywords || []);
    } catch (error) {
      console.error('Failed to fetch trending keywords:', error);
      setTrendingKeywords([]);
    } finally {
      setKeywordsLoading(false);
    }
  };

  // Fetch real data on component mount
  useEffect(() => {
    console.log('🎯 Dashboard: Loading real data from backend...');
    dispatch(fetchDocumentStats());
    dispatch(fetchSourceStats());
    dispatch(fetchRecentDocuments({ limit: 10 }));
    dispatch(fetchKeywords({ limit: 10 }));
    dispatch(fetchSearchAnalytics());
    fetchTrendingKeywords();
  }, [dispatch]);

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'document':
        return <Article />;
      case 'search':
        return <SearchIcon />;
      case 'upload':
        return <Description />;
      case 'source':
        return <Source />;
      default:
        return <Description />;
    }
  };

  const getActivityColor = (type) => {
    switch (type) {
      case 'document':
        return 'primary';
      case 'search':
        return 'secondary';
      case 'upload':
        return 'success';
      case 'source':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      {/* Welcome Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome back, {user?.first_name || user?.username || 'User'}! 👋
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's what's happening in your knowledge base today.
        </Typography>
      </Box>

      {/* Quick Search */}
      <Card sx={{ mb: 4, background: 'linear-gradient(135deg, #1976D2 0%, #42A5F5 100%)' }}>
        <CardContent sx={{ color: 'white' }}>
          <Typography variant="h6" gutterBottom>
            🔍 Quick Search
          </Typography>
          <Typography variant="body2" sx={{ mb: 2, opacity: 0.9 }}>
            Search across your entire knowledge base using natural language
          </Typography>
          
          <Box
            component="form"
            onSubmit={handleSearchSubmit}
            sx={{ display: 'flex', gap: 2, alignItems: 'center' }}
          >
            <TextField
              fullWidth
              placeholder="What would you like to find today?"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ color: 'rgba(255,255,255,0.7)' }} />
                  </InputAdornment>
                ),
                sx: {
                  backgroundColor: 'rgba(255, 255, 255, 0.15)',
                  color: 'white',
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(255, 255, 255, 0.3)',
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(255, 255, 255, 0.5)',
                  },
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'white',
                  },
                  '& input::placeholder': {
                    color: 'rgba(255, 255, 255, 0.7)',
                  },
                },
              }}
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              sx={{
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                color: 'white',
                minWidth: '120px',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.3)',
                },
              }}
            >
              Search
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                  <Description />
                </Avatar>
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Documents
                  </Typography>
                  {loading ? (
                    <Skeleton width={60} height={32} />
                  ) : (
                    <Typography variant="h5">
                      {stats.totalDocuments.toLocaleString()}
                    </Typography>
                  )}
                </Box>
              </Box>
              <Button
                size="small"
                endIcon={<ArrowForward />}
                onClick={() => navigate('/documents')}
              >
                View All
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'secondary.main', mr: 2 }}>
                  <SearchIcon />
                </Avatar>
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Searches
                  </Typography>
                  {loading ? (
                    <Skeleton width={60} height={32} />
                  ) : (
                    <Typography variant="h5">
                      {stats.totalSearches.toLocaleString()}
                    </Typography>
                  )}
                </Box>
              </Box>
              <Button
                size="small"
                endIcon={<ArrowForward />}
                onClick={() => navigate('/analytics')}
              >
                View Analytics
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar sx={{ bgcolor: 'warning.main', mr: 2 }}>
                  <Source />
                </Avatar>
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Sources
                  </Typography>
                  {loading ? (
                    <Skeleton width={40} height={32} />
                  ) : (
                    <Typography variant="h5">
                      {stats.activeSources}
                    </Typography>
                  )}
                </Box>
              </Box>
              <Button
                size="small"
                endIcon={<ArrowForward />}
                onClick={() => navigate('/sources')}
              >
                Manage Sources
              </Button>
            </CardContent>
          </Card>
        </Grid>


        {/* Recent Activity */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" component="h2">
                  Recent Activity
                </Typography>
                <Button
                  size="small"
                  endIcon={<ArrowForward />}
                  onClick={() => navigate('/analytics')}
                >
                  View All
                </Button>
              </Box>

              <List>
                {loading ? (
                  // Loading skeletons
                  Array.from(new Array(4)).map((_, index) => (
                    <ListItem key={index}>
                      <ListItemAvatar>
                        <Skeleton variant="circular" width={40} height={40} />
                      </ListItemAvatar>
                      <ListItemText
                        primary={<Skeleton width="60%" />}
                        secondary={<Skeleton width="40%" />}
                      />
                    </ListItem>
                  ))
                ) : (
                  recentActivity.map((activity) => (
                    <ListItem key={activity.id} divider>
                      <ListItemAvatar>
                        <Avatar sx={{ bgcolor: `${getActivityColor(activity.type)}.main` }}>
                          {getActivityIcon(activity.type)}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={activity.title}
                        secondary={
                          <Box component="div">
                            <Typography variant="body2" color="text.secondary" component="div">
                              {activity.description}
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5, gap: 1 }}>
                              <Chip
                                label={activity.source}
                                size="small"
                                variant="outlined"
                              />
                              <Typography variant="caption" color="text.secondary" component="span">
                                {activity.timestamp}
                              </Typography>
                            </Box>
                          </Box>
                        }
                        secondaryTypographyProps={{
                          component: 'div'
                        }}
                      />
                    </ListItem>
                  ))
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Trending Keywords */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" component="h2">
                  🏷️ Trending Keywords
                </Typography>
                <IconButton size="small">
                  <LocalOffer />
                </IconButton>
              </Box>

              {keywordsLoading || loading ? (
                // Loading skeletons
                Array.from(new Array(5)).map((_, index) => (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Skeleton width="80%" height={24} />
                    <Skeleton width="60%" height={16} />
                  </Box>
                ))
              ) : trendingKeywords.length > 0 ? (
                trendingKeywords.map((keyword, index) => (
                  <Box key={keyword.name} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {index + 1}. "{keyword.name}"
                      </Typography>
                      <Chip
                        label={`${keyword.percentage}%`}
                        size="small"
                        color="primary"
                        variant="outlined"
                        sx={{ 
                          backgroundColor: keyword.color ? `${keyword.color}20` : undefined,
                          borderColor: keyword.color || undefined
                        }}
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {keyword.count} documents
                    </Typography>
                  </Box>
                ))
              ) : (
                <Box sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    No trending keywords available yet.
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Keywords will appear as you add more documents with tags.
                  </Typography>
                </Box>
              )}

              <Button
                fullWidth
                variant="outlined"
                size="small"
                sx={{ mt: 2 }}
                onClick={() => navigate('/documents')}
              >
                View All Documents
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Quick Actions
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ cursor: 'pointer' }} onClick={() => navigate('/documents?action=upload')}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Add sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                <Typography variant="h6" gutterBottom>
                  Upload Document
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Add new content to your knowledge base
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ cursor: 'pointer' }} onClick={() => navigate('/sources?action=add')}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Source sx={{ fontSize: 48, color: 'warning.main', mb: 1 }} />
                <Typography variant="h6" gutterBottom>
                  Add RSS Source
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Configure automatic news collection
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ cursor: 'pointer' }} onClick={() => navigate('/search')}>
              <CardContent sx={{ textAlign: 'center' }}>
                <SearchIcon sx={{ fontSize: 48, color: 'secondary.main', mb: 1 }} />
                <Typography variant="h6" gutterBottom>
                  Advanced Search
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Search with filters and advanced options
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ cursor: 'pointer' }} onClick={() => navigate('/analytics')}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Analytics sx={{ fontSize: 48, color: 'info.main', mb: 1 }} />
                <Typography variant="h6" gutterBottom>
                  View Analytics
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Analyze your content and usage patterns
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default Dashboard;
