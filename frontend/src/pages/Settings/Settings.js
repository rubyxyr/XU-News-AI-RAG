import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  Divider,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Save } from '@mui/icons-material';

const Settings = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Notification Preferences
          </Typography>
          
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Email notifications for new content"
          />
          <br />
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Daily digest emails"
          />
          <br />
          <FormControlLabel
            control={<Switch />}
            label="Weekly analytics reports"
          />
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            AI & Search Settings
          </Typography>
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Search Result Limit</InputLabel>
            <Select defaultValue={10} label="Search Result Limit">
              <MenuItem value={5}>5 results</MenuItem>
              <MenuItem value={10}>10 results</MenuItem>
              <MenuItem value={20}>20 results</MenuItem>
              <MenuItem value={50}>50 results</MenuItem>
            </Select>
          </FormControl>

          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Auto-generate summaries for new content"
          />
          <br />
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Auto-tag articles"
          />
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Data & Privacy
          </Typography>
          
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Allow analytics data collection"
          />
          <br />
          <FormControlLabel
            control={<Switch />}
            label="Share usage data for improvements"
          />

          <Divider sx={{ my: 2 }} />

          <Button variant="outlined" color="primary" sx={{ mr: 2 }}>
            Export Data
          </Button>
          <Button variant="outlined" color="error">
            Delete Account
          </Button>
        </CardContent>
      </Card>

      <Button variant="contained" startIcon={<Save />} size="large">
        Save Settings
      </Button>
    </Box>
  );
};

export default Settings;
