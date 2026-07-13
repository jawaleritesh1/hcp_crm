import React from 'react';
import { Box, Container, Paper, Typography, AppBar, Toolbar } from '@mui/material';
import InteractionForm from './components/InteractionForm';
import AIChat from './components/AIChat';

const App: React.FC = () => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Header */}
      <AppBar position="static" color="primary" elevation={1}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            HCP Log Interaction
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content Area */}
      <Container maxWidth={false} sx={{ flexGrow: 1, p: 3, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, height: '100%', m: 0, width: '100%' }}>
          
          {/* Left Panel: Structured Interaction Form */}
          <Box sx={{ flex: '1 1 50%', height: '100%', minWidth: '300px', pb: 2 }}>
            <Paper 
              elevation={2} 
              sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column', 
                overflow: 'hidden',
                border: '1px solid #e0e0e0'
              }}
            >
              <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', bgcolor: '#fafafa' }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }} color="text.primary">
                  Interaction Details
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Review and save interaction log.
                </Typography>
              </Box>
              <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
                <InteractionForm />
              </Box>
            </Paper>
          </Box>

          {/* Right Panel: AI Chat Assistant */}
          <Box sx={{ flex: '1 1 40%', height: '100%', minWidth: '300px', pb: 2 }}>
            <Paper 
              elevation={2} 
              sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column', 
                overflow: 'hidden',
                border: '1px solid #e0e0e0',
              }}
            >
              <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', bgcolor: '#f3e5f5' }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }} color="secondary.main">
                  AI Assistant
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Dictate or type interaction notes here.
                </Typography>
              </Box>
              <Box sx={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
                <AIChat />
              </Box>
            </Paper>
          </Box>

        </Box>
      </Container>

      {/* Footer */}
      <Box sx={{ p: 1.5, bgcolor: 'background.paper', borderTop: '1px solid #e0e0e0', textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Status: Ready to log interactions
        </Typography>
      </Box>
    </Box>
  );
};

export default App;
