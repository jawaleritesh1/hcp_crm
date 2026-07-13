import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  Box, 
  TextField, 
  IconButton, 
  Typography, 
  Paper, 
  Avatar, 
  Card, 
  CardContent,
  CardActions,
  Button,
  CircularProgress,
  InputAdornment
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import PersonIcon from '@mui/icons-material/Person';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { addMessage, setProcessing, updateForm } from '../store';
import type { RootState, InteractionFormState, EntityOption } from '../store';
import { crmApi } from '../api/crmApi';

const AIChat: React.FC = () => {
  const [input, setInput] = useState('');
  const dispatch = useDispatch();
  const chatState = useSelector((state: RootState) => state.chat);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatState.messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMsg = input;
    setInput('');
    
    // Add user message
    dispatch(addMessage({
      id: Date.now().toString(),
      sender: 'user',
      text: userMsg,
      timestamp: new Date().toISOString()
    }));
    
    dispatch(setProcessing(true));

    try {
      // Connect to real backend LangGraph
      const response = await crmApi.processInteraction(userMsg, chatState.threadId);
      
      // Add AI explanation
      dispatch(addMessage({
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: response.explanation || 'Processed successfully.',
        timestamp: new Date().toISOString()
      }));

      // Parse extracted data to map to Form State
      const data = response.extracted_data;
      if (data && (data.hcp?.name || data.products?.length > 0)) {
        
        const hcpOption: EntityOption | null = (data.hcp?.name && data.hcp?.id && data.hcp.id !== '00000000-0000-0000-0000-000000000000') ? {
          id: data.hcp.id,
          name: data.hcp.name
        } : null;

        const productOptions: EntityOption[] = (data.products || [])
          .filter((p: any) => p.id && p.id !== '11111111-1111-1111-1111-111111111111')
          .map((p: any) => ({
            id: p.id,
            name: p.name
          }));

        const followUps = (data.follow_ups || []).map((f: any) => ({
          action_item: f.action_item,
          priority: f.priority,
          due_date: f.due_date || null,
          reason: f.reason || null
        }));

        const formStatePayload: Partial<InteractionFormState> = {
          hcp: hcpOption,
          interactionDate: data.interaction_date || new Date().toISOString().split('T')[0],
          sentiment: data.sentiment?.value || 'Neutral',
          summary: data.summary || '',
          products: productOptions,
          followUps: followUps
        };

        dispatch(addMessage({
          id: (Date.now() + 2).toString(),
          sender: 'ai',
          text: '',
          timestamp: new Date().toISOString(),
          isExtractionPreview: true,
          extractionData: formStatePayload,
          rawBackendData: data
        }));
      }
    } catch (error) {
      console.error(error);
      dispatch(addMessage({
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: 'I experienced an error connecting to the server. Please try again.',
        timestamp: new Date().toISOString()
      }));
    } finally {
      dispatch(setProcessing(false));
    }
  };

  const handleAcceptExtraction = (data: Partial<InteractionFormState>) => {
    dispatch(updateForm(data));
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages Area */}
      <Box sx={{ flexGrow: 1, p: 2, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {chatState.messages.map((msg) => (
          <Box 
            key={msg.id} 
            sx={{ 
              display: 'flex', 
              flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row',
              alignItems: 'flex-start',
              gap: 1
            }}
          >
            <Avatar sx={{ bgcolor: msg.sender === 'user' ? 'primary.main' : 'secondary.main', width: 32, height: 32 }}>
              {msg.sender === 'user' ? <PersonIcon fontSize="small" /> : <AutoAwesomeIcon fontSize="small" />}
            </Avatar>
            
            {msg.isExtractionPreview && msg.extractionData ? (
              <Card variant="outlined" sx={{ maxWidth: '90%', borderColor: 'secondary.light', bgcolor: '#fdfbfd', borderRadius: 3, mb: 1 }}>
                <CardContent sx={{ pb: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Typography variant="subtitle2" color="secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                    <CheckCircleIcon fontSize="small" /> Extraction Preview
                  </Typography>
                  
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                      HCP: {msg.extractionData.hcp?.name || 'Unknown'} 
                      {msg.rawBackendData?.hcp?.confidence < 0.90 && (
                        <Typography component="span" variant="caption" color="warning.main" sx={{ display: 'inline-flex', alignItems: 'center', ml: 1, fontWeight: 'medium' }}>
                          <WarningAmberIcon fontSize="inherit" sx={{ mr: 0.5 }} /> Low confidence
                        </Typography>
                      )}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                      <Box component="span" sx={{ fontWeight: 'bold', mr: 0.5 }}>Products:</Box> 
                      {msg.extractionData.products?.length ? msg.extractionData.products.map(p => p.name).join(', ') : 'None'}
                      {msg.rawBackendData?.products?.some((p: any) => p.confidence < 0.90) && (
                        <Typography component="span" variant="caption" color="warning.main" sx={{ display: 'inline-flex', alignItems: 'center', ml: 1, fontWeight: 'medium' }}>
                          <WarningAmberIcon fontSize="inherit" sx={{ mr: 0.5 }} /> Low confidence
                        </Typography>
                      )}
                    </Typography>
                  </Box>

                  <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Date:</Box> {msg.extractionData.interactionDate}</Typography>
                  <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Sentiment:</Box> {msg.extractionData.sentiment}</Typography>
                  
                  {msg.rawBackendData?.duplicate_warning?.duplicate_found && (
                    <Box sx={{ mt: 1, p: 1.5, bgcolor: '#fff4e5', border: '1px solid #ffd8a8', borderRadius: 2 }}>
                      <Typography variant="body2" color="warning.dark" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
                        <WarningAmberIcon fontSize="small" sx={{ mr: 0.5 }} />
                        Possible Duplicate Detected
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                        {msg.rawBackendData.duplicate_warning.recommendation}
                      </Typography>
                    </Box>
                  )}

                  {msg.rawBackendData?.engagement && (
                    <Box sx={{ mt: 1, p: 1, bgcolor: '#e8f5e9', borderRadius: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                        Engagement Score: {msg.rawBackendData.engagement.score}/100
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        | Interest: {msg.rawBackendData.engagement.interest_level}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        | Readiness: {msg.rawBackendData.engagement.prescription_readiness}
                      </Typography>
                    </Box>
                  )}

                  {msg.rawBackendData?.next_best_action && (
                    <Box sx={{ mt: 1, p: 1.5, bgcolor: '#e3f2fd', borderRadius: 2 }}>
                      <Typography variant="body2" color="primary.dark" sx={{ fontWeight: 'bold' }}>
                        💡 Next Best Action
                      </Typography>
                      <Typography variant="caption" sx={{ display: 'block', mt: 0.5, fontWeight: 'medium' }}>
                        {msg.rawBackendData.next_best_action.action}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {msg.rawBackendData.next_best_action.rationale}
                      </Typography>
                    </Box>
                  )}

                  {msg.extractionData.summary && (
                    <Box sx={{ mt: 1, p: 1.5, bgcolor: 'rgba(0,0,0,0.03)', borderRadius: 2 }}>
                      <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                        "{msg.extractionData.summary}"
                      </Typography>
                    </Box>
                  )}

                  {msg.extractionData.followUps && msg.extractionData.followUps.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>Follow-ups:</Typography>
                      <Box component="ul" sx={{ m: 0, pl: 2, typography: 'body2' }}>
                        {msg.extractionData.followUps.map((fu: any, i: number) => {
                           const rawFu = msg.rawBackendData?.follow_ups?.[i];
                           return (
                             <li key={i}>
                               <Box component="span" sx={{ fontWeight: 'medium' }}>{fu.action_item}</Box> 
                               {fu.due_date ? ` (Due: ${fu.due_date})` : ''}
                               {rawFu?.priority && (
                                 <Typography component="span" variant="caption" sx={{ ml: 1, px: 1, py: 0.2, bgcolor: rawFu.priority === 'High' || rawFu.priority === 'Critical' ? '#ffebee' : '#f5f5f5', color: rawFu.priority === 'High' || rawFu.priority === 'Critical' ? '#c62828' : 'text.secondary', borderRadius: 1 }}>
                                   {rawFu.priority}
                                 </Typography>
                               )}
                               {rawFu?.priority_reason && (
                                 <Typography variant="caption" color="text.secondary" sx={{ display: 'block', pl: 2, fontStyle: 'italic' }}>
                                   Reason: {rawFu.priority_reason}
                                 </Typography>
                               )}
                             </li>
                           );
                        })}
                      </Box>
                    </Box>
                  )}
                </CardContent>
                <CardActions sx={{ pt: 0, pb: 2, px: 2 }}>
                  <Button size="small" color="secondary" variant="contained" disableElevation onClick={() => handleAcceptExtraction(msg.extractionData!)} sx={{ borderRadius: 2, textTransform: 'none', px: 2 }}>
                    Accept & Populate Form
                  </Button>
                </CardActions>
              </Card>
            ) : (
              <Paper 
                elevation={0} 
                sx={{ 
                  p: 2, 
                  maxWidth: '85%', 
                  bgcolor: msg.sender === 'user' ? 'primary.main' : 'background.paper',
                  color: msg.sender === 'user' ? 'primary.contrastText' : 'text.primary',
                  borderRadius: 3,
                  border: msg.sender === 'ai' ? '1px solid #e0e0e0' : 'none',
                  whiteSpace: 'pre-wrap'
                }}
              >
                <Typography variant="body2" sx={{ lineHeight: 1.6 }}>{msg.text}</Typography>
              </Paper>
            )}
          </Box>
        ))}
        
        {chatState.isProcessing && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 5 }}>
            <CircularProgress size={16} color="secondary" />
            <Typography variant="caption" color="text.secondary">Analyzing interaction...</Typography>
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box sx={{ p: 2, borderTop: '1px solid #e0e0e0', bgcolor: 'background.paper' }}>
        <TextField
          fullWidth
          placeholder="Type or dictate your notes..."
          variant="outlined"
          size="small"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !chatState.isProcessing && handleSend()}
          slotProps={{
            input: {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton color="secondary" onClick={handleSend} disabled={!input.trim() || chatState.isProcessing}>
                    <SendIcon />
                  </IconButton>
                </InputAdornment>
              )
            }
          }}
        />
      </Box>
    </Box>
  );
};

export default AIChat;
