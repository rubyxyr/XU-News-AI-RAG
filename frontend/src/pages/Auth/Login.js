import React, { useState } from 'react';
import { Link as RouterLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  TextField,
  Button,
  Typography,
  Link,
  FormControlLabel,
  Checkbox,
  Alert,
  InputAdornment,
  IconButton,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Login as LoginIcon,
  Email,
  Lock,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { loginUser, clearError } from '../../store/slices/authSlice';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  
  const { loading, error } = useAppSelector((state) => state.auth);
  const [showPassword, setShowPassword] = useState(false);

  // Get the intended destination or default to dashboard
  const from = location.state?.from?.pathname || '/dashboard';

  const validationSchema = Yup.object({
    username: Yup.string()
      .min(3, 'Username must be at least 3 characters')
      .required('Username or email is required'),
    password: Yup.string()
      .min(6, 'Password must be at least 6 characters')
      .required('Password is required'),
  });

  const formik = useFormik({
    initialValues: {
      username: '',
      password: '',
      rememberMe: false,
    },
    validationSchema,
    onSubmit: async (values) => {
      dispatch(clearError());
      const result = await dispatch(loginUser(values));
      
      if (loginUser.fulfilled.match(result)) {
        navigate(from, { replace: true });
      }
    },
  });

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };


  return (
    <Box sx={{ width: '100%', maxWidth: '400px' }}>
      <Box sx={{ textAlign: 'center', mb: 3 }}>
        <LoginIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome Back
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Sign in to your knowledge base
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box component="form" onSubmit={formik.handleSubmit} sx={{ mt: 1 }}>
        <TextField
          fullWidth
          id="username"
          name="username"
          label="Username or Email"
          type="text"
          autoComplete="username"
          autoFocus
          value={formik.values.username}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.username && Boolean(formik.errors.username)}
          helperText={formik.touched.username && formik.errors.username}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Email color="action" />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 2 }}
        />

        <TextField
          fullWidth
          id="password"
          name="password"
          label="Password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="current-password"
          value={formik.values.password}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.password && Boolean(formik.errors.password)}
          helperText={formik.touched.password && formik.errors.password}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Lock color="action" />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="toggle password visibility"
                  onClick={handleTogglePassword}
                  edge="end"
                >
                  {showPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
          sx={{ mb: 1 }}
        />

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <FormControlLabel
            control={
              <Checkbox
                name="rememberMe"
                checked={formik.values.rememberMe}
                onChange={formik.handleChange}
                color="primary"
              />
            }
            label="Remember me"
          />
          <Link
            component={RouterLink}
            to="/forgot-password"
            variant="body2"
            sx={{ textDecoration: 'none' }}
          >
            Forgot password?
          </Link>
        </Box>

        <Button
          type="submit"
          fullWidth
          variant="contained"
          size="large"
          disabled={loading}
          sx={{
            mt: 1,
            mb: 2,
            py: 1.5,
            fontSize: '1rem',
            fontWeight: 600,
            textTransform: 'none',
          }}
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </Button>


        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Don't have an account?{' '}
            <Link
              component={RouterLink}
              to="/register"
              variant="body2"
              sx={{
                color: 'primary.main',
                textDecoration: 'none',
                fontWeight: 600,
                '&:hover': {
                  textDecoration: 'underline',
                },
              }}
            >
              Sign up here
            </Link>
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default Login;
