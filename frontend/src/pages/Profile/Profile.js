import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Avatar,
  Button,
  Grid,
  TextField,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Edit, Save, Cancel } from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../../hooks/redux';
import { updateProfile } from '../../store/slices/authSlice';

const Profile = () => {
  const { user } = useAppSelector((state) => state.auth);
  const dispatch = useAppDispatch();
  
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    bio: ''
  });

  // Initialize form data when user data is available
  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        bio: user.bio || ''
      });
    }
  }, [user]);

  const handleFormChange = (field) => (event) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setMessage(null);

      const result = await dispatch(updateProfile(formData));
      
      if (updateProfile.fulfilled.match(result)) {
        setMessage({ type: 'success', text: 'Profile updated successfully!' });
        setEditing(false);
      } else {
        throw new Error(result.payload || 'Profile update failed');
      }
    } catch (error) {
      console.error('Profile update error:', error);
      setMessage({ 
        type: 'error', 
        text: error.message || 'Failed to update profile' 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    // Reset form data to original user data
    setFormData({
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      bio: user?.bio || ''
    });
    setEditing(false);
    setMessage(null);
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
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Profile Settings
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Avatar
                sx={{
                  width: 120,
                  height: 120,
                  fontSize: '2rem',
                  bgcolor: 'primary.main',
                  mx: 'auto',
                  mb: 2,
                }}
              >
                {getInitials(fullName)}
              </Avatar>
              
              <Typography variant="h5" gutterBottom>
                {fullName}
              </Typography>
              
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {user?.email}
              </Typography>

              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                Member since {new Date(user?.created_at || '2024-01-01').toLocaleDateString()}
              </Typography>

            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6">
                  Personal Information
                </Typography>
                {!editing ? (
                  <Button 
                    startIcon={<Edit />}
                    onClick={() => setEditing(true)}
                  >
                    Edit
                  </Button>
                ) : (
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                      startIcon={loading ? <CircularProgress size={16} /> : <Save />}
                      variant="contained"
                      onClick={handleSave}
                      disabled={loading}
                    >
                      Save
                    </Button>
                    <Button
                      startIcon={<Cancel />}
                      onClick={handleCancel}
                      disabled={loading}
                    >
                      Cancel
                    </Button>
                  </Box>
                )}
              </Box>

              {message && (
                <Alert severity={message.type} sx={{ mb: 3 }}>
                  {message.text}
                </Alert>
              )}

              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="First Name"
                    value={formData.first_name}
                    onChange={handleFormChange('first_name')}
                    disabled={!editing || loading}
                    variant={editing ? "outlined" : "filled"}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Last Name"
                    value={formData.last_name}
                    onChange={handleFormChange('last_name')}
                    disabled={!editing || loading}
                    variant={editing ? "outlined" : "filled"}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Username"
                    value={user?.username || ''}
                    disabled={true}
                    variant="filled"
                    helperText="Username cannot be changed"
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Email"
                    value={user?.email || ''}
                    disabled={true}
                    variant="filled"
                    helperText="Email cannot be changed"
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Bio"
                    multiline
                    rows={4}
                    value={formData.bio}
                    onChange={handleFormChange('bio')}
                    disabled={!editing || loading}
                    variant={editing ? "outlined" : "filled"}
                    placeholder="Tell us about yourself..."
                  />
                </Grid>
              </Grid>

            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Profile;
