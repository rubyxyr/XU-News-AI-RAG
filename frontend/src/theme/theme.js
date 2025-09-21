import { createTheme } from '@mui/material/styles';

// Custom color palette
const colors = {
  primary: {
    main: '#1976D2',
    light: '#42A5F5',
    dark: '#1565C0',
    contrastText: '#ffffff',
  },
  secondary: {
    main: '#388E3C',
    light: '#66BB6A',
    dark: '#2E7D32',
    contrastText: '#ffffff',
  },
  accent: {
    orange: '#F57C00',
    purple: '#7B1FA2',
    teal: '#00796B',
  },
  gray: {
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#EEEEEE',
    300: '#E0E0E0',
    400: '#BDBDBD',
    500: '#9E9E9E',
    600: '#757575',
    700: '#616161',
    800: '#424242',
    900: '#212121',
  },
  semantic: {
    success: '#4CAF50',
    warning: '#FF9800',
    error: '#F44336',
    info: '#2196F3',
  },
};

// Create custom theme
export const theme = createTheme({
  palette: {
    primary: colors.primary,
    secondary: colors.secondary,
    success: {
      main: colors.semantic.success,
    },
    warning: {
      main: colors.semantic.warning,
    },
    error: {
      main: colors.semantic.error,
    },
    info: {
      main: colors.semantic.info,
    },
    background: {
      default: colors.gray[50],
      paper: '#ffffff',
    },
    text: {
      primary: colors.gray[900],
      secondary: colors.gray[700],
    },
    divider: colors.gray[300],
    action: {
      hover: 'rgba(25, 118, 210, 0.04)',
      selected: 'rgba(25, 118, 210, 0.08)',
    },
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
      lineHeight: 1.2,
      letterSpacing: '-0.01562em',
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      lineHeight: 1.2,
      letterSpacing: '-0.00833em',
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
      lineHeight: 1.2,
      letterSpacing: '0em',
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.235,
      letterSpacing: '0.00735em',
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
      lineHeight: 1.334,
      letterSpacing: '0em',
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 500,
      lineHeight: 1.6,
      letterSpacing: '0.0075em',
    },
    body1: {
      fontSize: '1rem',
      fontWeight: 400,
      lineHeight: 1.5,
      letterSpacing: '0.00938em',
    },
    body2: {
      fontSize: '0.875rem',
      fontWeight: 400,
      lineHeight: 1.43,
      letterSpacing: '0.01071em',
    },
    button: {
      fontSize: '0.875rem',
      fontWeight: 500,
      lineHeight: 1.75,
      letterSpacing: '0.02857em',
      textTransform: 'none',
    },
    caption: {
      fontSize: '0.75rem',
      fontWeight: 400,
      lineHeight: 1.66,
      letterSpacing: '0.03333em',
    },
    overline: {
      fontSize: '0.75rem',
      fontWeight: 400,
      lineHeight: 2.66,
      letterSpacing: '0.08333em',
      textTransform: 'uppercase',
    },
  },
  spacing: 8, // Base spacing unit (8px)
  shape: {
    borderRadius: 8,
  },
  shadows: [
    'none',
    '0px 1px 2px rgba(0, 0, 0, 0.05)',
    '0px 2px 4px rgba(0, 0, 0, 0.05)',
    '0px 4px 8px rgba(0, 0, 0, 0.05)',
    '0px 8px 16px rgba(0, 0, 0, 0.05)',
    '0px 16px 32px rgba(0, 0, 0, 0.05)',
    '0px 32px 64px rgba(0, 0, 0, 0.05)',
    // ... additional shadows
    ...Array(18).fill('0px 32px 64px rgba(0, 0, 0, 0.05)'),
  ],
  components: {
    // MuiCssBaseline
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarColor: '#6b6b6b #2b2b2b',
          '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
            borderRadius: '8px',
            backgroundColor: colors.gray[400],
            minHeight: '24px',
            border: '2px solid',
            borderColor: colors.gray[50],
          },
          '&::-webkit-scrollbar-thumb:focus, & *::-webkit-scrollbar-thumb:focus': {
            backgroundColor: colors.gray[500],
          },
          '&::-webkit-scrollbar-thumb:active, & *::-webkit-scrollbar-thumb:active': {
            backgroundColor: colors.gray[500],
          },
          '&::-webkit-scrollbar-thumb:hover, & *::-webkit-scrollbar-thumb:hover': {
            backgroundColor: colors.gray[500],
          },
          '&::-webkit-scrollbar-corner, & *::-webkit-scrollbar-corner': {
            backgroundColor: colors.gray[50],
          },
        },
      },
    },
    // MuiButton
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          padding: '8px 16px',
          fontSize: '0.875rem',
          fontWeight: 500,
          boxShadow: 'none',
          textTransform: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
          },
          '&:active': {
            boxShadow: '0px 1px 2px rgba(0, 0, 0, 0.1)',
          },
        },
        containedPrimary: {
          background: `linear-gradient(135deg, ${colors.primary.main} 0%, ${colors.primary.dark} 100%)`,
          '&:hover': {
            background: `linear-gradient(135deg, ${colors.primary.dark} 0%, ${colors.primary.dark} 100%)`,
          },
        },
      },
    },
    // MuiCard
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.05)',
          border: `1px solid ${colors.gray[200]}`,
          '&:hover': {
            boxShadow: '0px 4px 16px rgba(0, 0, 0, 0.1)',
          },
        },
      },
    },
    // MuiPaper
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        elevation1: {
          boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.05)',
        },
      },
    },
    // MuiTextField
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: '8px',
            '& fieldset': {
              borderColor: colors.gray[300],
            },
            '&:hover fieldset': {
              borderColor: colors.primary.main,
            },
            '&.Mui-focused fieldset': {
              borderColor: colors.primary.main,
              borderWidth: '2px',
            },
          },
        },
      },
    },
    // MuiChip
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: '16px',
          fontSize: '0.75rem',
          height: '28px',
        },
        colorPrimary: {
          backgroundColor: colors.primary.light,
          color: '#ffffff',
          '&:hover': {
            backgroundColor: colors.primary.main,
          },
        },
      },
    },
    // MuiAppBar
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#ffffff',
          color: colors.gray[900],
          boxShadow: '0px 1px 4px rgba(0, 0, 0, 0.05)',
          borderBottom: `1px solid ${colors.gray[200]}`,
        },
      },
    },
    // MuiDrawer
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: `1px solid ${colors.gray[200]}`,
          backgroundColor: '#ffffff',
        },
      },
    },
    // MuiListItem
    MuiListItem: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          margin: '2px 8px',
          '&.Mui-selected': {
            backgroundColor: colors.primary.main,
            color: '#ffffff',
            '&:hover': {
              backgroundColor: colors.primary.dark,
            },
            '& .MuiListItemIcon-root': {
              color: '#ffffff',
            },
          },
          '&:hover': {
            backgroundColor: colors.gray[100],
            borderRadius: '8px',
          },
        },
      },
    },
    // MuiTab
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontSize: '0.875rem',
          fontWeight: 500,
          minHeight: '48px',
        },
      },
    },
    // MuiDataGrid
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: `1px solid ${colors.gray[200]}`,
          borderRadius: '8px',
          '& .MuiDataGrid-cell': {
            borderBottom: `1px solid ${colors.gray[200]}`,
          },
          '& .MuiDataGrid-columnHeaders': {
            backgroundColor: colors.gray[50],
            borderBottom: `1px solid ${colors.gray[300]}`,
          },
          '& .MuiDataGrid-row:hover': {
            backgroundColor: colors.gray[50],
          },
        },
      },
    },
  },
});

// Custom theme extensions
theme.custom = {
  colors,
  layout: {
    headerHeight: '64px',
    sidebarWidth: '280px',
    sidebarCollapsedWidth: '80px',
  },
  zIndex: {
    sidebar: 1200,
    header: 1300,
    modal: 1400,
    tooltip: 1500,
    notification: 1600,
  },
};

export default theme;
