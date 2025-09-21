import React, { useState, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  Paper,
  CircularProgress,
  Alert,
  LinearProgress,
  Badge,
} from '@mui/material';
import { Search as SearchIcon, OpenInNew } from '@mui/icons-material';
import { useAppSelector } from '../../hooks/redux';
import {
  performSearch,
  performStreamingSearch,
  setQuery,
  selectSearchResults,
  selectExternalResults,
  selectSearchLoading,
  selectSearchStreaming,
  selectSearchProgress,
  selectSearchError,
  selectSearchMetadata,
  resetSearchProgress,
} from '../../store/slices/searchSlice';

const Search = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Get initial query from URL parameter
  const urlQuery = searchParams.get('q') || '';
  
  // Local state for input field
  const [localQuery, setLocalQuery] = useState('');
  const [useStreaming] = useState(true); // Toggle for streaming vs regular search
  const [hasAutoSearched, setHasAutoSearched] = useState(false);
  
  // Initialize local query from URL on mount
  useEffect(() => {
    if (urlQuery) {
      console.log('🔄 Setting initial query from URL:', urlQuery);
      setLocalQuery(urlQuery);
    }
  }, []); // Run only once on mount
  
  // Redux state
  const results = useAppSelector(selectSearchResults);
  const externalResults = useAppSelector(selectExternalResults);
  const loading = useAppSelector(selectSearchLoading);
  const streaming = useAppSelector(selectSearchStreaming);
  const progress = useAppSelector(selectSearchProgress);
  const error = useAppSelector(selectSearchError);
  const searchMetadata = useAppSelector(selectSearchMetadata);

  // Auto-execute search when component mounts with URL query parameter
  useEffect(() => {
    if (urlQuery && urlQuery.trim() && !hasAutoSearched) {
      console.log('🚀 Auto-executing search from URL parameter:', urlQuery);
      setHasAutoSearched(true);
      
      // Set up search parameters
      const searchParams = {
        query: urlQuery.trim(),
        search_type: 'semantic',
        limit: 10,
        include_external: true,
      };

      // Store query in Redux
      dispatch(setQuery(urlQuery));
      dispatch(resetSearchProgress());

      // Execute search
      if (useStreaming) {
        dispatch(performStreamingSearch(searchParams));
      } else {
        dispatch(performSearch(searchParams));
      }
    }
  }, [urlQuery, hasAutoSearched, dispatch, useStreaming]);


  const handleSearch = async (e) => {
    e.preventDefault();
    if (!localQuery.trim()) return;

    console.log('🔍 Starting search for:', localQuery);
    
    // Update URL with current query
    setSearchParams({ q: localQuery.trim() });
    
    dispatch(setQuery(localQuery));
    
    // Clear previous progress
    dispatch(resetSearchProgress());
    
    const searchParams = {
      query: localQuery.trim(),
      search_type: 'semantic',
      limit: 10,
      include_external: true, // Enable external search for better results
    };

    if (useStreaming) {
      console.log('🚀 Using streaming search');
      dispatch(performStreamingSearch(searchParams));
    } else {
      console.log('🔍 Using regular search');
      dispatch(performSearch(searchParams));
    }
  };

  const handleResultClick = (result) => {
    const documentId = result.document_id || result.id;
    if (documentId) {
      // Navigate to documents page with document ID as query parameter
      navigate(`/documents?highlight=${documentId}`);
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Search Knowledge Base
      </Typography>
      
      {/* Search Form */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box component="form" onSubmit={handleSearch}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={8}>
                <TextField
                  fullWidth
                  placeholder="Search your knowledge base using natural language..."
                  value={localQuery}
                  onChange={(e) => {
                    console.log('🔤 Input change:', e.target.value);
                    setLocalQuery(e.target.value);
                  }}
                  variant="outlined"
                  disabled={loading || streaming}
                  sx={{ 
                    '& .MuiInputBase-input': {
                      cursor: 'text !important',
                    }
                  }}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  fullWidth
                  startIcon={!loading && !streaming ? <SearchIcon /> : <CircularProgress size={20} />}
                  disabled={loading || streaming}
                >
                  {loading || streaming ? 
                    (streaming ? 'Searching...' : 'Loading...') : 
                    'Search'
                  }
                </Button>
              </Grid>
            </Grid>
          </Box>
        </CardContent>
      </Card>

      {/* Progress Display */}
      {(streaming || (progress.status !== 'idle' && progress.status !== 'error' && progress.status !== 'done' && progress.status !== 'completed')) && (
        <Card sx={{ mb: 2, bgcolor: 'background.paper' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <CircularProgress size={20} sx={{ mr: 2 }} />
              <Typography variant="body2">
                {progress.message || 'Searching...'}
              </Typography>
              {progress.external_search && (
                <Badge color="info" badgeContent="External" sx={{ ml: 2 }}>
                  <OpenInNew fontSize="small" />
                </Badge>
              )}
              {progress.streaming_summary && (
                <Badge color="warning" badgeContent="AI" sx={{ ml: 1 }}>
                  <CircularProgress size={16} />
                </Badge>
              )}
            </Box>
            
            <LinearProgress 
              variant="determinate" 
              value={progress.progress || 0} 
              sx={{ mb: 1 }}
            />
            
            {/* Streaming Summary Display */}
            {progress.streaming_summary && progress.partial_summary && (
              <Box sx={{ 
                mb: 2, 
                p: 2, 
                bgcolor: 'grey.50', 
                borderRadius: 1, 
                border: '1px solid',
                borderColor: 'grey.200'
              }}>
                <Typography variant="caption" color="primary.main" sx={{ fontWeight: 'bold', display: 'block', mb: 1 }}>
                  🤖 AI Summary (Result {(progress.result_index || 0) + 1}):
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontStyle: progress.summary_completed ? 'normal' : 'italic',
                    color: progress.summary_completed ? 'text.primary' : 'text.secondary',
                    minHeight: '1.5em'
                  }}
                >
                  {progress.partial_summary || 'Generating summary...'}
                  {!progress.summary_completed && (
                    <Box component="span" sx={{ 
                      display: 'inline-block', 
                      width: '3px', 
                      height: '1em', 
                      bgcolor: 'primary.main',
                      animation: 'blink 1s infinite',
                      ml: 0.5,
                      '@keyframes blink': {
                        '0%, 50%': { opacity: 1 },
                        '51%, 100%': { opacity: 0 }
                      }
                    }}>|</Box>
                  )}
                </Typography>
              </Box>
            )}
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                {progress.progress || 0}% complete
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {progress.results_count > 0 && `${progress.results_count} found`}
                {progress.external_results_count > 0 && ` • ${progress.external_results_count} external`}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Terminal Status Display (Error/Done) */}
      {progress.status === 'error' && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          onClose={() => dispatch(resetSearchProgress())}
        >
          <Typography variant="body2" component="div">
            <strong>Search Error:</strong> {progress.message || 'Search failed'}
          </Typography>
          {progress.error && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              {progress.error}
            </Typography>
          )}
        </Alert>
      )}

      {(progress.status === 'done' || progress.status === 'completed') && (
        <Alert 
          severity="success" 
          sx={{ mb: 2 }}
          onClose={() => dispatch(resetSearchProgress())}
        >
          <Typography variant="body2">
            {progress.message || 'Search completed successfully!'}
          </Typography>
          {(progress.results_count > 0 || progress.external_results_count > 0) && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              {progress.results_count > 0 && `${progress.results_count} results found`}
              {progress.external_results_count > 0 && ` • ${progress.external_results_count} external results`}
            </Typography>
          )}
        </Alert>
      )}

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Search failed: {error}
        </Alert>
      )}

      {/* Search Results Metadata */}
      {searchMetadata && !streaming && (
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="body2" color="text.secondary">
            Found {searchMetadata.total_results || results.length} results in {searchMetadata.search_time || 0}s
          </Typography>
          {searchMetadata.has_external_results && (
            <Chip 
              icon={<OpenInNew fontSize="small" />} 
              label={`${searchMetadata.external_results_count} external results`}
              size="small"
              color="info"
              variant="outlined"
            />
          )}
        </Box>
      )}

      {results.length > 0 && (
        <Box>
          {results.map((result, index) => (
            <Card 
              key={result.document_id || result.id || index} 
              sx={{ 
                mb: 2, 
                cursor: 'pointer',
                '&:hover': {
                  boxShadow: 3,
                  transform: 'translateY(-2px)',
                },
                transition: 'all 0.2s ease-in-out'
              }}
              onClick={() => handleResultClick(result)}
            >
              <CardContent sx={{ position: 'relative' }}>
                {/* Relevance Score - Top Right Corner */}
                {result.relevance_score && (
                  <Chip 
                    label={`${Math.round(result.relevance_score * 100)}%`} 
                    color={
                      result.relevance_score >= 0.9 ? "success" :
                      result.relevance_score >= 0.8 ? "primary" :
                      result.relevance_score >= 0.7 ? "info" :
                      "default"
                    }
                    size="small" 
                    sx={{ 
                      position: 'absolute',
                      top: 16,
                      right: 16,
                      zIndex: 1
                    }}
                  />
                )}
                
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, pr: result.relevance_score ? 6 : 0 }}>
                  <Typography variant="caption" color="text.secondary">
                    {result.source_name || result.source || 'Unknown Source'} • {result.published_date ? new Date(result.published_date).toLocaleDateString() : (result.created_at ? new Date(result.created_at).toLocaleDateString() : (result.date || 'Unknown Date'))}
                  </Typography>
                </Box>
                
                <Typography variant="h6" component="h3" gutterBottom>
                  {result.title}
                </Typography>
                
                <Typography variant="body2" color="text.secondary" paragraph>
                  {result.content_preview || result.summary || result.content || 'No content available'}
                </Typography>
                
                {(result.tags || []).length > 0 && (
                  <Box>
                    {result.tags.map((tag, tagIndex) => (
                      <Chip
                        key={`${tag}-${tagIndex}`}
                        label={tag}
                        size="small"
                        variant="outlined"
                        onClick={() => {
                          setLocalQuery(tag);
                          setSearchParams({ q: tag });
                          setHasAutoSearched(false); // Allow auto-search for new tag
                        }}
                        sx={{ mr: 1, mb: 1, cursor: 'pointer' }}
                      />
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* External Results */}
      {externalResults.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <OpenInNew />
            External Results
            <Chip label={externalResults.length} size="small" color="info" />
          </Typography>
          
          {externalResults.map((result, index) => (
            <Card 
              key={result.url || index} 
              sx={{ 
                mb: 2, 
                border: '1px solid',
                borderColor: 'info.main',
                borderRadius: 2,
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Chip 
                    icon={<OpenInNew fontSize="small" />}
                    label={result.source || 'Web'}
                    color="info" 
                    size="small" 
                    sx={{ mr: 2 }}
                  />
                  {result.enhanced && (
                    <Chip 
                      label="AI Enhanced" 
                      color="secondary" 
                      size="small" 
                      variant="outlined"
                    />
                  )}
                </Box>
                
                <Typography 
                  variant="h6" 
                  component="a"
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{
                    textDecoration: 'none',
                    color: 'primary.main',
                    '&:hover': { textDecoration: 'underline' },
                    display: 'block',
                    mb: 1
                  }}
                >
                  {result.title}
                </Typography>
                
                <Typography variant="body2" color="text.secondary" paragraph>
                  {result.snippet || result.ai_summary || 'No description available'}
                </Typography>
                
                <Typography variant="caption" color="text.secondary">
                  {result.url}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Empty State */}
      {results.length === 0 && externalResults.length === 0 && !loading && !streaming && progress.status === 'idle' && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Start searching your knowledge base
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Use natural language queries to find relevant documents, articles, and research papers.
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default Search;
