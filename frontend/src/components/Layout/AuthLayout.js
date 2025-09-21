import React from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Link,
  useTheme,
  useMediaQuery,
} from '@mui/material';

const AuthLayout = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${theme.palette.primary.light} 0%, ${theme.palette.primary.main} 100%)`,
        padding: theme.spacing(2),
      }}
    >
      <Container
        component="main"
        maxWidth="sm"
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        {/* Logo and Brand */}
        <Box
          sx={{
            mb: 4,
            textAlign: 'center',
          }}
        >
          <Typography
            variant="h3"
            component="h1"
            sx={{
              fontWeight: 700,
              color: 'white',
              mb: 1,
              fontSize: isMobile ? '2rem' : '3rem',
            }}
          >
            XU-News AI-RAG
          </Typography>
          <Typography
            variant="h6"
            sx={{
              color: 'rgba(255, 255, 255, 0.8)',
              fontSize: isMobile ? '1rem' : '1.25rem',
            }}
          >
            Personalized News Intelligent Knowledge Base
          </Typography>
        </Box>

        {/* Auth Form Container */}
        <Paper
          elevation={24}
          sx={{
            padding: theme.spacing(4),
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
            borderRadius: theme.spacing(2),
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
          }}
        >
          {children}
        </Paper>

        {/* Footer */}
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>
            Powered by AI • Built with ❤️
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            © 2024 XU-News AI-RAG. All rights reserved.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default AuthLayout;
