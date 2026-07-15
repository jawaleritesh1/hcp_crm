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
  Button,
  CircularProgress,
  InputAdornment,
  Chip,
  Divider,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import MicIcon from '@mui/icons-material/Mic';
import PersonIcon from '@mui/icons-material/Person';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import SearchIcon from '@mui/icons-material/Search';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import { addMessage, setProcessing, updateForm, acceptDuplicateExtraction, markCandidateSelected, toggleFollowUpChecklist } from '../store';
import type { RootState, InteractionFormState, EntityOption, HCPCandidateItem, UpdatedFieldInfo } from '../store';
import { crmApi } from '../api/crmApi';

const getFormDiff = (oldForm: InteractionFormState, newForm: Partial<InteractionFormState>): UpdatedFieldInfo[] => {
  const diffs: UpdatedFieldInfo[] = [];

  // 1. HCP
  if (newForm.hcp !== undefined) {
    const oldName = oldForm.hcp?.name || 'None';
    const newName = newForm.hcp?.name || 'None';
    if (oldName.toLowerCase() !== newName.toLowerCase()) {
      diffs.push({ field: 'hcp', label: 'HCP Name', oldValue: oldName, newValue: newName });
    }
  }

  // 2. Interaction Type
  if (newForm.interactionType !== undefined && newForm.interactionType !== oldForm.interactionType) {
    diffs.push({ field: 'interactionType', label: 'Interaction Type', oldValue: oldForm.interactionType, newValue: newForm.interactionType });
  }

  // 3. Date
  if (newForm.interactionDate !== undefined && newForm.interactionDate !== oldForm.interactionDate) {
    diffs.push({ field: 'interactionDate', label: 'Date', oldValue: oldForm.interactionDate || 'None', newValue: newForm.interactionDate });
  }

  // 4. Time
  if (newForm.interactionTime !== undefined && newForm.interactionTime !== oldForm.interactionTime) {
    diffs.push({ field: 'interactionTime', label: 'Time', oldValue: oldForm.interactionTime || 'None', newValue: newForm.interactionTime });
  }

  // 5. Attendees
  if (newForm.attendees !== undefined && newForm.attendees !== oldForm.attendees) {
    diffs.push({ field: 'attendees', label: 'Attendees', oldValue: oldForm.attendees || 'None', newValue: newForm.attendees });
  }

  // 6. Topics Discussed
  if (newForm.topicsDiscussed !== undefined && newForm.topicsDiscussed !== oldForm.topicsDiscussed) {
    diffs.push({ field: 'topicsDiscussed', label: 'Topics Discussed', oldValue: oldForm.topicsDiscussed || 'None', newValue: newForm.topicsDiscussed });
  }

  // 7. Sentiment
  if (newForm.sentiment !== undefined && newForm.sentiment !== oldForm.sentiment) {
    diffs.push({ field: 'sentiment', label: 'Sentiment', oldValue: oldForm.sentiment || 'None', newValue: newForm.sentiment });
  }

  // 8. Outcomes
  if (newForm.outcomes !== undefined && newForm.outcomes !== oldForm.outcomes) {
    diffs.push({ field: 'outcomes', label: 'Outcomes', oldValue: oldForm.outcomes || 'None', newValue: newForm.outcomes });
  }

  // 9. Materials Shared
  if (newForm.materialsShared !== undefined) {
    const oldMats = oldForm.materialsShared.map(p => p.name).sort().join(', ') || 'None';
    const newMats = newForm.materialsShared.map(p => p.name).sort().join(', ') || 'None';
    if (oldMats.toLowerCase() !== newMats.toLowerCase()) {
      diffs.push({ field: 'materialsShared', label: 'Materials Shared', oldValue: oldMats, newValue: newMats });
    }
  }

  // 10. Samples Distributed
  if (newForm.samplesDistributed !== undefined) {
    const oldSamps = oldForm.samplesDistributed.map(p => p.name).sort().join(', ') || 'None';
    const newSamps = newForm.samplesDistributed.map(p => p.name).sort().join(', ') || 'None';
    if (oldSamps.toLowerCase() !== newSamps.toLowerCase()) {
      diffs.push({ field: 'samplesDistributed', label: 'Samples Distributed', oldValue: oldSamps, newValue: newSamps });
    }
  }

  return diffs;
};

const AIChat: React.FC = () => {
  const [input, setInput] = useState('');
  const dispatch = useDispatch();
  const chatState = useSelector((state: RootState) => state.chat);
  const formState = useSelector((state: RootState) => state.form);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
      };

      recognition.onresult = (event: any) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          setInput(prev => {
            const separator = prev && !prev.endsWith(' ') ? ' ' : '';
            return prev + separator + finalTranscript.trim();
          });
        }
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error", event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const handleToggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.error("Failed to start speech recognition", err);
      }
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatState.messages]);

  // Parse backend response data into a form payload
  const buildFormPayload = (data: any): Partial<InteractionFormState> => {
    const hcpOption: EntityOption | null = data.hcp?.name ? {
      id: (data.hcp.id && data.hcp.id !== '00000000-0000-0000-0000-000000000000') ? data.hcp.id : '',
      name: data.hcp.name
    } : null;

    const materialsOptions: EntityOption[] = (data.materials_shared || [])
      .map((p: any) => ({
        id: (p.id && p.id !== '11111111-1111-1111-1111-111111111111') ? p.id : '',
        name: p.name
      }));

    const samplesOptions: EntityOption[] = (data.samples_distributed || [])
      .map((p: any) => ({
        id: (p.id && p.id !== '11111111-1111-1111-1111-111111111111') ? p.id : '',
        name: p.name
      }));

    const followUps = (data.follow_ups || []).map((f: any) => ({
      action_item: f.action_item,
      priority: f.priority,
      due_date: f.due_date || null,
      reason: f.reason || null
    }));

    return {
      hcp: hcpOption,
      interactionType: data.interaction_type || 'Meeting',
      interactionDate: data.interaction_date || new Date().toISOString().split('T')[0],
      interactionTime: data.interaction_time || '',
      attendees: data.attendees || '',
      topicsDiscussed: data.topics_discussed || '',
      materialsShared: materialsOptions,
      samplesDistributed: samplesOptions,
      sentiment: data.sentiment?.value || 'Neutral',
      outcomes: data.outcomes || '',
      aiSuggestedFollowUps: followUps
    };
  };

  const getUpdatedFollowUpsText = (text: string, oldHcpName: string, newHcpName: string): string => {
    if (!text || !oldHcpName || !newHcpName || oldHcpName.toLowerCase() === newHcpName.toLowerCase()) {
      return text;
    }
    const cleanOld = oldHcpName.replace(/^Dr\.\s*/i, '').replace(/^Dr\s*/i, '').trim();
    const cleanNew = newHcpName.replace(/^Dr\.\s*/i, '').replace(/^Dr\s*/i, '').trim();
    const oldLast = cleanOld.split(' ').pop() || '';
    const newLast = cleanNew.split(' ').pop() || '';

    let updatedText = text.replace(new RegExp(oldHcpName, 'gi'), newHcpName);
    updatedText = updatedText.replace(new RegExp(cleanOld, 'gi'), cleanNew);
    if (oldLast && newLast && oldLast.toLowerCase() !== newLast.toLowerCase()) {
      const escapedOldLast = oldLast.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
      updatedText = updatedText.replace(new RegExp('\\b' + escapedOldLast + '\\b', 'gi'), newLast);
    }
    return updatedText;
  };

  const handleSend = async () => {
    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (!input.trim()) return;
    
    const userMsg = input;
    setInput('');
    
    dispatch(addMessage({
      id: Date.now().toString(),
      sender: 'user',
      text: userMsg,
      timestamp: new Date().toISOString()
    }));
    
    dispatch(setProcessing(true));

    try {
      const response = await crmApi.processInteraction(userMsg, chatState.threadId);
      const data = response.extracted_data;
      const candidates: HCPCandidateItem[] = response.hcp_candidates || [];
      const hasAmbiguousCandidates = candidates.length > 0;

      // Detect if this was a simple edit (backend skipped enrichment)
      // Edits have no engagement/next_best_action data and no hcp_candidates
      const isEditResponse = data &&
        !hasAmbiguousCandidates &&
        data.engagement === null &&
        data.next_best_action === null;

      if (isEditResponse && data) {
        // ── EDIT RESPONSE: Update form immediately, no full preview card ──
        const formStatePayload = buildFormPayload(data);
        const diffs = getFormDiff(formState, formStatePayload);
        const hcpPendingName = data?.hcp?.pending_name;

        if (!hcpPendingName && !hasAmbiguousCandidates) {
          let finalPayload = { ...formStatePayload };
          const oldHcpName = formState.hcp?.name;
          const newHcpName = formStatePayload.hcp?.name;
          
          if (oldHcpName && newHcpName) {
            finalPayload.followUpsText = getUpdatedFollowUpsText(formState.followUpsText, oldHcpName, newHcpName);
          }
          dispatch(updateForm(finalPayload));
        }

        // Show compact field-change summary instead of full extraction preview
        dispatch(addMessage({
          id: (Date.now() + 1).toString(),
          sender: 'ai',
          text: response.explanation || 'Updated successfully.',
          timestamp: new Date().toISOString(),
          isEditSummary: true,
          extractionData: formStatePayload,
          rawBackendData: data,
          hcpCandidates: hasAmbiguousCandidates ? candidates : undefined,
          updatedFields: diffs
        }));

      } else {
        // ── LOG RESPONSE: Full explanation + extraction preview card ──
        dispatch(addMessage({
          id: (Date.now() + 1).toString(),
          sender: 'ai',
          text: response.explanation || 'Processed successfully.',
          timestamp: new Date().toISOString(),
          historyData: response.history_data && response.history_data.length > 0 ? response.history_data : undefined,
          followUpsChecklist: response.follow_ups_checklist && response.follow_ups_checklist.length > 0 ? response.follow_ups_checklist : undefined,
          hcpCandidates: hasAmbiguousCandidates ? candidates : undefined,
        }));

        if (data && (data.hcp?.name || data.materials_shared?.length > 0 || data.samples_distributed?.length > 0 || data.topics_discussed)) {
          const formStatePayload = buildFormPayload(data);
          const isDuplicate = data?.duplicate_warning?.duplicate_found;
          const hcpPendingName = data?.hcp?.pending_name;

          dispatch(addMessage({
            id: (Date.now() + 2).toString(),
            sender: 'ai',
            text: '',
            timestamp: new Date().toISOString(),
            isExtractionPreview: true,
            extractionData: formStatePayload,
            rawBackendData: data,
            isAccepted: false,
            hcpCandidates: hasAmbiguousCandidates ? candidates : undefined,
          }));

          if (!isDuplicate && !hasAmbiguousCandidates && !hcpPendingName) {
            dispatch(updateForm(formStatePayload));
          }
        }
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

  // Called when user selects a specific candidate from the candidate card
  const handleCandidateSelect = async (msgId: string, candidate: HCPCandidateItem, extractionData: Partial<InteractionFormState>) => {
    dispatch(markCandidateSelected(msgId));

    // Build a confirmation message to the backend so it stores the selection
    const confirmMsg = `I confirm the HCP is ${candidate.name}`;
    dispatch(addMessage({
      id: Date.now().toString(),
      sender: 'user',
      text: confirmMsg,
      timestamp: new Date().toISOString()
    }));

    dispatch(setProcessing(true));

    try {
      const response = await crmApi.processInteraction(confirmMsg, chatState.threadId);
      const data = response.extracted_data;

      dispatch(addMessage({
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: response.explanation || 'Updated.',
        timestamp: new Date().toISOString()
      }));

      if (data) {
        const formStatePayload = buildFormPayload(data);
        const oldHcpName = formState.hcp?.name;
        let finalPayload = {
          ...formStatePayload,
          hcp: { id: candidate.id, name: candidate.name }
        };
        if (oldHcpName && candidate.name) {
          finalPayload.followUpsText = getUpdatedFollowUpsText(formState.followUpsText, oldHcpName, candidate.name);
        }
        // Now the HCP is confirmed — update the form including HCP
        dispatch(updateForm(finalPayload));

        dispatch(addMessage({
          id: (Date.now() + 2).toString(),
          sender: 'ai',
          text: '',
          timestamp: new Date().toISOString(),
          isExtractionPreview: true,
          extractionData: finalPayload,
          rawBackendData: data,
          isAccepted: false,
        }));
      } else {
        const oldHcpName = formState.hcp?.name;
        let finalPayload = {
          ...extractionData,
          hcp: { id: candidate.id, name: candidate.name }
        };
        if (oldHcpName && candidate.name) {
          finalPayload.followUpsText = getUpdatedFollowUpsText(formState.followUpsText, oldHcpName, candidate.name);
        }
        // No new enrichment data — just update HCP in form from the candidate
        dispatch(updateForm(finalPayload));
      }
    } catch (error) {
      console.error(error);
    } finally {
      dispatch(setProcessing(false));
    }
  };

  // Called when user chooses "Create New HCP"
  const handleCreateNewHCP = async (msgId: string, pendingName: string, extractionData: Partial<InteractionFormState>) => {
    dispatch(markCandidateSelected(msgId));

    const confirmMsg = `Create new HCP`;
    dispatch(addMessage({
      id: Date.now().toString(),
      sender: 'user',
      text: confirmMsg,
      timestamp: new Date().toISOString()
    }));

    dispatch(setProcessing(true));

    try {
      const response = await crmApi.processInteraction(confirmMsg, chatState.threadId);
      dispatch(addMessage({
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: response.explanation || 'Confirmed.',
        timestamp: new Date().toISOString()
      }));

      // Update form with the new (unregistered) HCP name
      dispatch(updateForm({
        ...extractionData,
        hcp: { id: '', name: pendingName }
      }));
    } catch (error) {
      console.error(error);
    } finally {
      dispatch(setProcessing(false));
    }
  };

  const handleAcceptExtraction = (msgId: string, data: Partial<InteractionFormState>) => {
    dispatch(acceptDuplicateExtraction(msgId));
    dispatch(updateForm(data));
  };

  const handleSearchHCPHistorySelect = async (doctorName: string) => {
    const historyQuery = `Show history of meetings with ${doctorName}`;
    dispatch(addMessage({
      id: Date.now().toString(),
      sender: 'user',
      text: historyQuery,
      timestamp: new Date().toISOString()
    }));
    
    dispatch(setProcessing(true));
    try {
      const response = await crmApi.processInteraction(historyQuery, chatState.threadId);
      
      dispatch(addMessage({
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: response.explanation || 'Here is the history.',
        timestamp: new Date().toISOString(),
        historyData: response.history_data && response.history_data.length > 0 ? response.history_data : undefined,
        followUpsChecklist: response.follow_ups_checklist && response.follow_ups_checklist.length > 0 ? response.follow_ups_checklist : undefined,
      }));
    } catch (error) {
      console.error(error);
      dispatch(addMessage({
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: 'Failed to retrieve interaction history. Please try again.',
        timestamp: new Date().toISOString()
      }));
    } finally {
      dispatch(setProcessing(false));
    }
  };

  const handleFollowUpToggle = async (messageId: string, taskId: string, currentStatus: string) => {
    try {
      const nextStatus = currentStatus === 'PENDING' ? 'COMPLETED' : 'PENDING';
      dispatch(toggleFollowUpChecklist({ messageId, taskId, status: nextStatus }));
      await crmApi.updateFollowUpStatus(taskId, nextStatus);
    } catch (err) {
      console.error("Failed to toggle follow-up task status:", err);
      dispatch(toggleFollowUpChecklist({ messageId, taskId, status: currentStatus }));
    }
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
            
            {msg.isEditSummary && msg.extractionData ? (
              <Box sx={{ maxWidth: '85%' }}>
                <Paper elevation={0} sx={{ p: 1.5, bgcolor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 3, display: 'flex', flexDirection: 'column', gap: 0.75 }}>
                  <Typography variant="caption" color="success.dark" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontWeight: 'bold' }}>
                    <CheckCircleIcon fontSize="inherit" /> {msg.text || 'Form updated'}
                  </Typography>
                  
                  {msg.updatedFields && msg.updatedFields.length > 0 ? (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                      {msg.updatedFields.map((df, idx) => (
                        <Typography key={idx} variant="body2" sx={{ fontSize: '0.85rem' }}>
                          <Box component="span" sx={{ fontWeight: 'bold' }}>{df.label}:</Box>{' '}
                          <Box component="span" sx={{ textDecoration: 'line-through', color: 'text.secondary', mr: 0.5 }}>
                            {df.oldValue}
                          </Box>
                          ➔ <Box component="span" sx={{ fontWeight: 'bold', color: 'success.dark', ml: 0.5 }}>
                            {df.newValue}
                          </Box>
                        </Typography>
                      ))}
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      No form fields were changed.
                    </Typography>
                  )}
                  {/* Show candidate selection if ambiguous even in edit flow */}
                  {msg.hcpCandidates && msg.hcpCandidates.length > 0 && !msg.candidateSelected && (
                    <Box sx={{ mt: 0.5, p: 1, bgcolor: '#fff8e1', border: '1px solid #ffe082', borderRadius: 1.5 }}>
                      <Typography variant="caption" color="warning.dark" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.75 }}>
                        <SearchIcon fontSize="inherit" /> Select correct HCP
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                        {msg.hcpCandidates.map((candidate) => (
                          <Button key={candidate.id} variant="outlined" size="small" color="warning"
                            onClick={() => handleCandidateSelect(msg.id, candidate, msg.extractionData!)}
                            sx={{ textTransform: 'none', justifyContent: 'flex-start', py: 0.5 }}>
                            <Box>
                              <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block' }}>{candidate.name}</Typography>
                              <Typography variant="caption" color="text.secondary">{candidate.specialty}</Typography>
                            </Box>
                          </Button>
                        ))}
                        <Button variant="outlined" size="small" color="secondary"
                          onClick={() => handleCreateNewHCP(msg.id, msg.rawBackendData?.hcp?.pending_name || msg.extractionData?.hcp?.name || '', msg.extractionData!)}
                          sx={{ textTransform: 'none', justifyContent: 'flex-start', py: 0.5 }}>
                          <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Create New HCP</Typography>
                        </Button>
                      </Box>
                    </Box>
                  )}
                </Paper>
              </Box>
            ) : msg.isExtractionPreview && msg.extractionData ? (
              <Card variant="outlined" sx={{ maxWidth: '90%', borderColor: 'secondary.light', bgcolor: '#fdfbfd', borderRadius: 3, mb: 1 }}>
                <CardContent sx={{ pb: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Typography variant="subtitle2" color="secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                    <CheckCircleIcon fontSize="small" /> Extraction Preview
                  </Typography>
                  
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                      HCP: {msg.extractionData.hcp?.name || 'Unknown'}
                    </Typography>
                  </Box>

                  <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Interaction Type:</Box> {msg.extractionData.interactionType || 'Meeting'}</Typography>
                  
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Date:</Box> {msg.extractionData.interactionDate}</Typography>
                    {msg.extractionData.interactionTime && (
                      <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Time:</Box> {msg.extractionData.interactionTime}</Typography>
                    )}
                  </Box>

                  {msg.extractionData.attendees && (
                    <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Attendees:</Box> {msg.extractionData.attendees}</Typography>
                  )}

                  <Box>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                      <Box component="span" sx={{ fontWeight: 'bold', mr: 0.5 }}>Materials Shared:</Box> 
                      {msg.extractionData.materialsShared?.length ? msg.extractionData.materialsShared.map(p => p.name).join(', ') : 'None'}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                      <Box component="span" sx={{ fontWeight: 'bold', mr: 0.5 }}>Samples Distributed:</Box> 
                      {msg.extractionData.samplesDistributed?.length ? msg.extractionData.samplesDistributed.map(p => p.name).join(', ') : 'None'}
                    </Typography>
                  </Box>

                  {msg.extractionData.outcomes && (
                    <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Outcomes:</Box> {msg.extractionData.outcomes}</Typography>
                  )}

                  <Typography variant="body2"><Box component="span" sx={{ fontWeight: 'bold' }}>Sentiment:</Box> {msg.extractionData.sentiment}</Typography>

                  {/* ── HCP Candidate Selection UI ── */}
                  {msg.hcpCandidates && msg.hcpCandidates.length > 0 && !msg.candidateSelected && (
                    <Box sx={{ mt: 1.5, p: 1.5, bgcolor: '#fff8e1', border: '1px solid #ffe082', borderRadius: 2 }}>
                      <Typography variant="body2" color="warning.dark" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                        <SearchIcon fontSize="small" /> Select the correct Healthcare Professional
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                        The form will only update after you choose one of the options below.
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {msg.hcpCandidates.map((candidate) => (
                          <Button
                            key={candidate.id}
                            variant="outlined"
                            size="small"
                            color="warning"
                            onClick={() => handleCandidateSelect(msg.id, candidate, msg.extractionData!)}
                            sx={{ textTransform: 'none', justifyContent: 'flex-start', gap: 1 }}
                          >
                            <PersonIcon fontSize="small" />
                            <Box>
                              <Typography variant="body2" sx={{ fontWeight: 'bold', lineHeight: 1.2 }}>{candidate.name}</Typography>
                              <Typography variant="caption" color="text.secondary">{candidate.specialty}</Typography>
                            </Box>
                          </Button>
                        ))}
                        <Divider sx={{ my: 0.5 }} />
                        <Button
                          variant="outlined"
                          size="small"
                          color="secondary"
                          onClick={() => handleCreateNewHCP(
                            msg.id, 
                            msg.rawBackendData?.hcp?.pending_name || msg.extractionData?.hcp?.name || '',
                            msg.extractionData!
                          )}
                          sx={{ textTransform: 'none', justifyContent: 'flex-start', gap: 1 }}
                        >
                          <PersonAddIcon fontSize="small" />
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 'bold', lineHeight: 1.2 }}>Create New HCP</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {msg.rawBackendData?.hcp?.pending_name ? `Register "${msg.rawBackendData.hcp.pending_name}" as new` : 'Register as new Healthcare Professional'}
                            </Typography>
                          </Box>
                        </Button>
                      </Box>
                    </Box>
                  )}

                  {msg.hcpCandidates && msg.hcpCandidates.length > 0 && msg.candidateSelected && (
                    <Box sx={{ mt: 1, p: 1, bgcolor: '#e8f5e9', borderRadius: 2, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CheckCircleIcon fontSize="small" color="success" />
                      <Typography variant="caption" color="success.dark" sx={{ fontWeight: 'bold' }}>
                        Healthcare Professional confirmed. Form updated.
                      </Typography>
                    </Box>
                  )}
                  {/* ────────────────────────────── */}

                  {msg.rawBackendData?.duplicate_warning?.duplicate_found && (
                    <Box sx={{ mt: 1, p: 1.5, bgcolor: '#fff4e5', border: '1px solid #ffd8a8', borderRadius: 2 }}>
                      <Typography variant="body2" color="warning.dark" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
                        <WarningAmberIcon fontSize="small" sx={{ mr: 0.5 }} />
                        Possible Duplicate Detected
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, mb: 1 }}>
                        {msg.rawBackendData.duplicate_warning.recommendation}
                      </Typography>
                      
                      {!msg.isAccepted ? (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1.5 }}>
                          <Button size="small" variant="outlined" color="warning" onClick={() => alert("Navigating to existing interaction...")} sx={{ textTransform: 'none' }}>
                            Open Existing
                          </Button>
                          <Button size="small" variant="outlined" color="warning" onClick={() => alert("Switching to update mode...")} sx={{ textTransform: 'none' }}>
                            Update Existing
                          </Button>
                          <Button size="small" variant="contained" color="warning" disableElevation onClick={() => handleAcceptExtraction(msg.id, msg.extractionData!)} sx={{ textTransform: 'none' }}>
                            Create New Interaction
                          </Button>
                        </Box>
                      ) : (
                        <Typography variant="caption" color="success.dark" sx={{ display: 'flex', alignItems: 'center', mt: 1, fontWeight: 'bold' }}>
                          <CheckCircleIcon fontSize="inherit" sx={{ mr: 0.5 }} /> Proceeding with new interaction
                        </Typography>
                      )}
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

                  {msg.extractionData.topicsDiscussed && (
                    <Box sx={{ mt: 1, p: 1.5, bgcolor: 'rgba(0,0,0,0.03)', borderRadius: 2 }}>
                      <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                        "{msg.extractionData.topicsDiscussed}"
                      </Typography>
                    </Box>
                  )}

                  {msg.extractionData.aiSuggestedFollowUps && msg.extractionData.aiSuggestedFollowUps.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>AI Suggested Follow-ups:</Typography>
                      <Box component="ul" sx={{ m: 0, pl: 2, typography: 'body2' }}>
                        {msg.extractionData.aiSuggestedFollowUps.map((fu: any, i: number) => {
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
                  whiteSpace: 'pre-wrap',
                  width: (msg.historyData || msg.followUpsChecklist) ? '100%' : 'auto'
                }}
              >
                <Typography variant="body2" sx={{ lineHeight: 1.6 }}>{msg.text}</Typography>

                {/* Render Search Results Candidates */}
                {msg.hcpCandidates && msg.hcpCandidates.length > 0 && (
                  <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {msg.hcpCandidates.map((candidate) => (
                      <Button
                        key={candidate.id}
                        variant="outlined"
                        size="small"
                        color="secondary"
                        onClick={() => handleSearchHCPHistorySelect(candidate.name)}
                        sx={{ textTransform: 'none', justifyContent: 'flex-start', py: 0.75, border: '1px solid #e0d0e0', borderRadius: 2 }}
                      >
                        <PersonIcon fontSize="small" sx={{ mr: 1, color: 'secondary.main' }} />
                        <Box sx={{ textAlign: 'left' }}>
                          <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'text.primary', fontSize: '0.85rem' }}>{candidate.name}</Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.75rem' }}>{candidate.specialty}</Typography>
                        </Box>
                      </Button>
                    ))}
                  </Box>
                )}

                {/* Render Timeline History Card */}
                {msg.historyData && msg.historyData.length > 0 && (
                  <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 1.5, width: '100%' }}>
                    {msg.historyData.map((h: any) => (
                      <Box key={h.id} sx={{ p: 1.5, bgcolor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 2.5 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                          <Chip 
                            label={h.interaction_type || 'Visit'} 
                            size="small" 
                            color="primary" 
                            variant="soft" 
                            sx={{ height: 20, fontSize: '0.7rem', fontWeight: 'bold' }} 
                          />
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'medium' }}>
                            📅 {h.interaction_date} {h.interaction_time ? `at ${h.interaction_time}` : ''}
                          </Typography>
                        </Box>
                        {h.topics_discussed && (
                          <Typography variant="body2" sx={{ fontWeight: 'bold', mt: 0.75, fontSize: '0.85rem', color: 'text.primary' }}>
                            Topics: {h.topics_discussed}
                          </Typography>
                        )}
                        {h.outcomes && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, fontStyle: 'italic' }}>
                            Outcomes: {h.outcomes}
                          </Typography>
                        )}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1, pt: 1, borderTop: '1px dashed #e2e8f0' }}>
                          <Typography variant="caption" color="text.secondary">
                            👥 Attendees: {h.attendees || 'None'}
                          </Typography>
                          <Typography variant="caption" sx={{ 
                            fontWeight: 'bold', 
                            color: h.sentiment === 'Positive' ? 'success.dark' : h.sentiment === 'Negative' ? 'error.dark' : 'warning.dark' 
                          }}>
                            Sentiment: {h.sentiment}
                          </Typography>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                )}

                {/* Render Interactive Follow-up Checklist */}
                {msg.followUpsChecklist && msg.followUpsChecklist.length > 0 && (
                  <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 1.2, width: '100%' }}>
                    {msg.followUpsChecklist.map((task: any) => (
                      <Box key={task.id} sx={{ 
                        p: 1.2, 
                        bgcolor: task.status === 'COMPLETED' ? '#f0fdf4' : '#fff',
                        border: '1px solid',
                        borderColor: task.status === 'COMPLETED' ? '#bbf7d0' : '#e2e8f0', 
                        borderRadius: 2.5,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 1
                      }}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={task.status === 'COMPLETED'}
                              onChange={() => handleFollowUpToggle(msg.id, task.id, task.status)}
                              color="success"
                              size="small"
                              sx={{ py: 0 }}
                            />
                          }
                          label={
                            <Box sx={{ ml: -0.5 }}>
                              <Typography variant="body2" sx={{ 
                                fontWeight: 'bold', 
                                fontSize: '0.85rem',
                                textDecoration: task.status === 'COMPLETED' ? 'line-through' : 'none',
                                color: task.status === 'COMPLETED' ? 'text.secondary' : 'text.primary'
                              }}>
                                {task.action_item}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.75rem' }}>
                                For {task.hcp_name} • Due: {task.due_date ? task.due_date.substring(0, 10) : 'No due date'}
                              </Typography>
                            </Box>
                          }
                          sx={{ m: 0 }}
                        />
                        <Chip
                          label={task.priority}
                          size="small"
                          sx={{ 
                            height: 20, 
                            fontSize: '0.7rem',
                            fontWeight: 'bold',
                            bgcolor: task.priority === 'High' || task.priority === 'Critical' ? '#fee2e2' : '#f1f5f9',
                            color: task.priority === 'High' || task.priority === 'Critical' ? '#ef4444' : '#64748b'
                          }}
                        />
                      </Box>
                    ))}
                  </Box>
                )}
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
          multiline
          maxRows={4}
          placeholder="Type or dictate your notes..."
          variant="outlined"
          size="small"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (!chatState.isProcessing) {
                handleSend();
              }
            }
          }}
          slotProps={{
            input: {
              endAdornment: (
                <InputAdornment position="end" sx={{ gap: 0.5 }}>
                  <IconButton 
                    color={isRecording ? "error" : "default"} 
                    onClick={handleToggleRecording}
                    disabled={chatState.isProcessing}
                    sx={{
                      animation: isRecording ? 'pulse 1.5s infinite' : 'none',
                      '@keyframes pulse': {
                        '0%': { opacity: 1 },
                        '50%': { opacity: 0.4 },
                        '100%': { opacity: 1 },
                      }
                    }}
                  >
                    <MicIcon />
                  </IconButton>
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
