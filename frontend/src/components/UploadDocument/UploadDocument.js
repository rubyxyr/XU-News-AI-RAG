import React, { useState, useRef } from 'react';
import { useDispatch } from 'react-redux';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Chip,
  Stack,
  Alert,
  LinearProgress,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  CloudUpload,
  Close,
  TableChart,
  Delete,
} from '@mui/icons-material';
import { uploadDocument } from '../../store/slices/documentsSlice';

const SUPPORTED_FILE_TYPES = {
  'csv': { icon: <TableChart />, name: 'CSV File', accept: '.csv' },
  'xlsx': { icon: <TableChart />, name: 'Excel File', accept: '.xlsx' },
};

const MAX_FILE_SIZE = 16 * 1024 * 1024; // 16MB
const ACCEPTED_EXTENSIONS = Object.keys(SUPPORTED_FILE_TYPES);
const ACCEPT_ATTR = Object.values(SUPPORTED_FILE_TYPES).map(type => type.accept).join(',');

const UploadDocument = ({ open, onClose, onSuccess }) => {
  const dispatch = useDispatch();
  const fileInputRef = useRef(null);
  
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('');
  const [error, setError] = useState('');

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    const validFiles = [];
    const errors = [];

    files.forEach(file => {
      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: File size exceeds 16MB limit`);
        return;
      }

      // Check file extension
      const extension = file.name.split('.').pop()?.toLowerCase();
      if (!ACCEPTED_EXTENSIONS.includes(extension)) {
        errors.push(`${file.name}: Unsupported file type. Supported types: ${ACCEPTED_EXTENSIONS.join(', ')}`);
        return;
      }

      validFiles.push({
        file,
        name: file.name,
        size: file.size,
        type: extension,
        id: Date.now() + Math.random(),
      });
    });

    if (errors.length > 0) {
      setError(errors.join('\n'));
    } else {
      setError('');
    }

    setSelectedFiles(prev => [...prev, ...validFiles]);
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveFile = (fileId) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    
    const files = Array.from(event.dataTransfer.files);
    handleFileSelect({ target: { files } });
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (type) => {
    return SUPPORTED_FILE_TYPES[type]?.icon || <TableChart />;
  };

  const getFileTypeName = (type) => {
    return SUPPORTED_FILE_TYPES[type]?.name || 'Unknown File Type';
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one file to upload');
      return;
    }

    setUploading(true);
    setError('');
    setUploadProgress(0);

    try {
      const totalFiles = selectedFiles.length;
      let completedFiles = 0;

      for (const fileData of selectedFiles) {
        const formDataToSend = new FormData();
        formDataToSend.append('file', fileData.file);

        try {
          // Use streaming upload for all files
          await handleStreamingUpload(formDataToSend, fileData.name, completedFiles, totalFiles);
          
          completedFiles++;
          setUploadProgress((completedFiles / totalFiles) * 100);
        } catch (fileError) {
          throw new Error(`Failed to upload ${fileData.name}: ${fileError.message}`);
        }
      }

      // Success - reset form and close
      setSelectedFiles([]);
      setUploadProgress(100);
      
      if (onSuccess) {
        onSuccess();
      }
      
      setTimeout(() => {
        onClose();
        setUploadProgress(0);
      }, 1000);

    } catch (error) {
      console.error('Upload failed:', error);
      setError(error.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleStreamingUpload = async (formData, fileName, completedFiles, totalFiles) => {
    return new Promise((resolve, reject) => {
      const token = localStorage.getItem('access_token');
      const baseURL = process.env.REACT_APP_API_URL || '';
      
      fetch(`${baseURL}/api/content/documents/upload/stream`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function readStream() {
          return reader.read().then(({ done, value }) => {
            if (done) {
              return resolve();
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            lines.forEach(line => {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  
                  if (data.type === 'progress') {
                    // Calculate overall progress across all files
                    const fileProgress = data.percentage || 0;
                    const overallProgress = ((completedFiles * 100) + fileProgress) / totalFiles;
                    setUploadProgress(overallProgress);
                    
                    // Update status message if available
                    if (data.message) {
                      setUploadStatus(`${fileName}: ${data.message}`);
                    }
                  } else if (data.type === 'success') {
                    setUploadStatus(`${fileName}: Upload completed successfully`);
                    resolve(data);
                  } else if (data.type === 'error') {
                    reject(new Error(data.message));
                  }
                } catch (e) {
                  console.warn('Failed to parse SSE data:', line);
                }
              }
            });

            return readStream();
          });
        }

        return readStream();
      })
      .catch(error => {
        console.error('Streaming upload failed:', error);
        reject(error);
      });
    });
  };

  const handleClose = () => {
    if (!uploading) {
      setSelectedFiles([]);
      setError('');
      setUploadProgress(0);
      setUploadStatus('');
      onClose();
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose} 
      maxWidth="md" 
      fullWidth
      disableEscapeKeyDown={uploading}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">Upload Documents</Typography>
          {!uploading && (
            <IconButton onClick={handleClose} size="small">
              <Close />
            </IconButton>
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* File Drop Zone */}
        <Paper
          variant="outlined"
          sx={{
            p: 4,
            textAlign: 'center',
            cursor: selectedFiles.length === 0 ? 'pointer' : 'default',
            bgcolor: 'grey.50',
            border: '2px dashed',
            borderColor: 'grey.300',
            mb: 3,
            '&:hover': selectedFiles.length === 0 ? {
              borderColor: 'primary.main',
              bgcolor: 'primary.50',
            } : {},
          }}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => selectedFiles.length === 0 && fileInputRef.current?.click()}
        >
          <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Drop files here or click to browse
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Supported formats: CSV, XLSX
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Maximum file size: 16MB per file
          </Typography>
        </Paper>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPT_ATTR}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        {/* Selected Files List */}
        {selectedFiles.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              Selected Files ({selectedFiles.length})
            </Typography>
            <List dense>
              {selectedFiles.map((fileData) => (
                <ListItem key={fileData.id} divider>
                  <ListItemIcon>
                    {getFileIcon(fileData.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={fileData.name}
                    secondary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip 
                          label={getFileTypeName(fileData.type)} 
                          size="small" 
                          color="primary" 
                          variant="outlined"
                        />
                        <Typography variant="caption" color="text.secondary">
                          {formatFileSize(fileData.size)}
                        </Typography>
                      </Stack>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton 
                      edge="end" 
                      size="small"
                      onClick={() => handleRemoveFile(fileData.id)}
                      disabled={uploading}
                    >
                      <Delete />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </Box>
        )}


        {/* Upload Progress */}
        {uploading && (
          <Box sx={{ mb: 2 }}>
            <LinearProgress 
              variant="determinate" 
              value={uploadProgress} 
              sx={{ mb: 1 }}
            />
            <Typography variant="body2" color="text.secondary">
              Uploading... {Math.round(uploadProgress)}%
            </Typography>
            {uploadStatus && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontStyle: 'italic' }}>
                {uploadStatus}
              </Typography>
            )}
          </Box>
        )}

        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit' }}>
              {error}
            </pre>
          </Alert>
        )}

        {/* CSV/XLSX Format Info */}
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>CSV & Excel File Format Requirements:</strong>
          </Typography>
          <Typography variant="body2" component="div" sx={{ mt: 1 }}>
            For CSV and Excel files, use these column headers for optimal processing:
            <br />
            <strong>Required columns:</strong> title, content
            <br />
            <strong>Optional columns:</strong> author, published_date, category, source_url, tags
            <br />
            <br />
            <strong>Example format:</strong>
            <br />
            <code style={{ backgroundColor: '#f5f5f5', padding: '2px 4px', fontSize: '0.85em' }}>
              title,content,author,published_date,category,source_url,tags
            </code>
            <br />
            <br />
            • Each row becomes a separate searchable document
            • Tags should be comma-separated within the cell (e.g., "ai,technology,news")
            • Dates should be in ISO format or common formats (YYYY-MM-DD)
          </Typography>
        </Alert>
      </DialogContent>

      <DialogActions>
        <Button 
          onClick={handleClose} 
          disabled={uploading}
        >
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={selectedFiles.length === 0 || uploading}
          startIcon={uploading ? <LinearProgress size={20} /> : <CloudUpload />}
        >
          {uploading ? 'Uploading...' : `Upload ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default UploadDocument;
