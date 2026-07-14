import React, { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useSelector, useDispatch } from 'react-redux';
import { 
  Box, 
  TextField, 
  Button, 
  Typography, 
  Autocomplete, 
  MenuItem,
  RadioGroup,
  FormControlLabel,
  Radio,
  Snackbar,
  Alert,
  Paper,
  InputAdornment,
  IconButton
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SentimentSatisfiedAltIcon from '@mui/icons-material/SentimentSatisfiedAlt';
import SentimentNeutralIcon from '@mui/icons-material/SentimentNeutral';
import SentimentDissatisfiedIcon from '@mui/icons-material/SentimentDissatisfied';
import type { RootState, InteractionFormState, EntityOption, FollowUpItem } from '../store';
import { resetForm } from '../store';
import { crmApi } from '../api/crmApi';

const interactionTypes = ['Meeting', 'Phone Call', 'Video Call', 'Email'];

const SectionTitle = ({ title }: { title: string }) => (
  <Typography variant="subtitle2" sx={{ fontWeight: 600, bgcolor: '#f8f9fa', p: 1, borderRadius: 1, mb: 2, mt: 1 }}>
    {title}
  </Typography>
);

const InteractionForm = () => {
  const dispatch = useDispatch();
  const formState = useSelector((state: RootState) => state.form);
  
  const [hcpOptions, setHcpOptions] = useState<EntityOption[]>([]);
  const [savedHCPs, setSavedHCPs] = useState<EntityOption[]>([]);
  const [productOptions, setProductOptions] = useState<EntityOption[]>([]);
  const [loadingHCP, setLoadingHCP] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(false);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

  const fetchSavedHCPs = async () => {
    try {
      const hcps = await crmApi.getHCPs();
      const mapped = hcps.map(h => ({ id: h.id, name: `Dr. ${h.first_name} ${h.last_name} - ${h.specialty}` }));
      setSavedHCPs(mapped);
      setHcpOptions(mapped);
    } catch (e) {
      console.error("Failed to load saved HCPs", e);
    }
  };

  useEffect(() => {
    fetchSavedHCPs();
  }, []);

  const { control, handleSubmit, reset, watch, setValue } = useForm<InteractionFormState>({
    defaultValues: formState,
    values: formState
  });

  const followUpsText = watch('followUpsText');

  const searchHCPs = async (query: string) => {
    if (!query || query.trim().length === 0) {
      setHcpOptions(savedHCPs);
      return;
    }
    
    const cleanName = query.replace(/^Dr\.\s*/i, '').replace(/^Dr\s*/i, '').trim();
    
    if (query.trim().length < 2) {
      // Filter locally from the saved list to keep responsiveness
      const filtered = savedHCPs.filter(h => h.name.toLowerCase().includes(cleanName.toLowerCase()));
      // Always add an option to create new even for short query
      if (cleanName && !filtered.some(m => m.name.toLowerCase().includes(cleanName.toLowerCase()))) {
        filtered.push({
          id: 'new',
          name: `Dr. ${cleanName}`,
          isNewOption: true,
          customName: cleanName
        } as any);
      }
      setHcpOptions(filtered);
      return;
    }

    setLoadingHCP(true);
    try {
      const hcps = await crmApi.searchHCPs(query);
      const mapped = hcps.map(h => ({ id: h.id, name: `Dr. ${h.first_name} ${h.last_name} - ${h.specialty}` }));
      
      const hasExact = mapped.some(m => m.name.toLowerCase().includes(cleanName.toLowerCase()));
      
      if (!hasExact && cleanName) {
        mapped.push({
          id: 'new',
          name: `Dr. ${cleanName}`,
          isNewOption: true,
          customName: cleanName
        } as any);
      }
      setHcpOptions(mapped);
    } catch (e) {
      console.error(e);
    }
    setLoadingHCP(false);
  };

  const searchProducts = async (query: string) => {
    if (!query || query.length < 2) {
      setProductOptions([]);
      return;
    }
    setLoadingProducts(true);
    try {
      const products = await crmApi.searchProducts(query);
      setProductOptions(products.map(p => ({ id: p.id, name: p.name })));
    } catch (e) {
      console.error(e);
    }
    setLoadingProducts(false);
  };

  const appendSuggestedFollowUp = (fu: FollowUpItem) => {
    const newText = followUpsText ? `${followUpsText}\n- ${fu.action_item}` : `- ${fu.action_item}`;
    setValue('followUpsText', newText);
  };

  const onSubmit = async (data: InteractionFormState) => {
    if (!data.hcp || !data.hcp.id) {
      setToast({ open: true, message: 'Please select a valid HCP from the list or add as new.', severity: 'error' });
      return;
    }

    setIsSubmitting(true);
    try {
      let hcpId = data.hcp.id;
      
      if (hcpId === 'new') {
        const rawName = (data.hcp as any).customName || data.hcp.name.replace(/^Dr\.\s*/i, '').trim();
        const words = rawName.split(/\s+/);
        let firstName = 'Dr.';
        let lastName = rawName;
        if (words.length > 1) {
          firstName = words[0];
          lastName = words.slice(1).join(' ');
        }
        
        const newHCP = await crmApi.createHCP(firstName, lastName, 'General Practice');
        hcpId = newHCP.id;
      }

      const payload = {
        hcp_id: hcpId,
        interaction_type: data.interactionType,
        interaction_date: data.interactionDate || new Date().toISOString().split('T')[0],
        interaction_time: data.interactionTime,
        attendees: data.attendees,
        topics_discussed: data.topicsDiscussed,
        materials_shared: data.materialsShared.map(p => p.id).filter(id => id),
        samples_distributed: data.samplesDistributed.map(p => p.id).filter(id => id),
        sentiment: data.sentiment || 'Neutral',
        outcomes: data.outcomes,
        follow_ups_text: data.followUpsText
      };

      await crmApi.saveInteraction(payload);
      setToast({ open: true, message: 'Interaction Saved Successfully!', severity: 'success' });
      fetchSavedHCPs(); // Refresh options list with any newly added HCP
      dispatch(resetForm());
      reset();
    } catch (error) {
      console.error(error);
      setToast({ open: true, message: 'Failed to save interaction.', severity: 'error' });
    }
    setIsSubmitting(false);
  };

  return (
    <Paper elevation={0} variant="outlined" sx={{ p: 0, border: 'none' }}>
      <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate sx={{ display: 'flex', flexDirection: 'column' }}>
        
        <SectionTitle title="Interaction Details" />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, mb: 3 }}>
          <Controller
            name="hcp"
            control={control}
            rules={{ required: 'HCP is required' }}
            render={({ field, fieldState: { error } }) => (
              <Autocomplete
                {...field}
                options={hcpOptions}
                getOptionLabel={(option) => option.name}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                onChange={(_, newValue) => field.onChange(newValue)}
                onInputChange={(_, newInputValue) => searchHCPs(newInputValue)}
                loading={loadingHCP}
                renderOption={(props, option) => (
                  <li {...props} key={option.id}>
                    {(option as any).isNewOption ? `Add '${option.name}' as a new HCP` : option.name}
                  </li>
                )}
                renderInput={(params) => (
                  <TextField {...params} label="HCP Name" placeholder="Search or select HCP..." variant="outlined" error={!!error} helperText={error?.message} size="small" />
                )}
              />
            )}
          />
          <Controller
            name="interactionType"
            control={control}
            render={({ field }) => (
              <TextField {...field} select fullWidth label="Interaction Type" variant="outlined" size="small">
                {interactionTypes.map((option) => (
                  <MenuItem key={option} value={option}>{option}</MenuItem>
                ))}
              </TextField>
            )}
          />
          <Controller
            name="interactionDate"
            control={control}
            rules={{ required: 'Date is required' }}
            render={({ field, fieldState: { error } }) => (
              <TextField {...field} fullWidth label="Date" type="date" variant="outlined" slotProps={{ inputLabel: { shrink: true } }} error={!!error} helperText={error?.message} size="small" />
            )}
          />
          <Controller
            name="interactionTime"
            control={control}
            render={({ field }) => (
              <TextField {...field} fullWidth label="Time" type="time" variant="outlined" slotProps={{ inputLabel: { shrink: true } }} size="small" />
            )}
          />
          <Box sx={{ gridColumn: '1 / -1' }}>
            <Controller
              name="attendees"
              control={control}
              render={({ field }) => (
                <TextField {...field} fullWidth label="Attendees" placeholder="Enter names or search..." variant="outlined" size="small" />
              )}
            />
          </Box>
          <Box sx={{ gridColumn: '1 / -1' }}>
            <Controller
              name="topicsDiscussed"
              control={control}
              render={({ field }) => (
                <TextField 
                  {...field} 
                  fullWidth 
                  label="Topics Discussed" 
                  placeholder="Enter key discussion points..." 
                  multiline 
                  rows={3} 
                  variant="outlined"
                  slotProps={{
                    input: {
                      endAdornment: (
                        <InputAdornment position="end" sx={{ alignSelf: 'flex-end', mb: 1 }}>
                          <IconButton size="small"><MicIcon fontSize="small" /></IconButton>
                        </InputAdornment>
                      )
                    }
                  }}
                />
              )}
            />
            <Button variant="outlined" color="inherit" size="small" startIcon={<AutoAwesomeIcon />} sx={{ mt: 1, textTransform: 'none', bgcolor: '#f8f9fa' }}>
              Summarize from Voice Note (Requires Consent)
            </Button>
          </Box>
        </Box>

        <SectionTitle title="Materials Shared / Samples Distributed" />
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2, mb: 3 }}>
          <Controller
            name="materialsShared"
            control={control}
            render={({ field }) => (
              <Autocomplete
                {...field}
                multiple
                options={productOptions}
                getOptionLabel={(option) => option.name}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                onChange={(_, newValue) => field.onChange(newValue)}
                onInputChange={(_, newInputValue) => searchProducts(newInputValue)}
                loading={loadingProducts}
                renderInput={(params) => (
                  <TextField {...params} variant="outlined" label="Materials Shared" placeholder="Search/Add" size="small" />
                )}
              />
            )}
          />
          <Controller
            name="samplesDistributed"
            control={control}
            render={({ field }) => (
              <Autocomplete
                {...field}
                multiple
                options={productOptions}
                getOptionLabel={(option) => option.name}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                onChange={(_, newValue) => field.onChange(newValue)}
                onInputChange={(_, newInputValue) => searchProducts(newInputValue)}
                loading={loadingProducts}
                renderInput={(params) => (
                  <TextField {...params} variant="outlined" label="Samples Distributed" placeholder="Add Sample" size="small" />
                )}
              />
            )}
          />
        </Box>

        <SectionTitle title="Observed/Inferred HCP Sentiment" />
        <Box sx={{ mb: 3 }}>
          <Controller
            name="sentiment"
            control={control}
            render={({ field }) => (
              <RadioGroup {...field} row sx={{ gap: 4 }}>
                <FormControlLabel value="Positive" control={<Radio color="success" />} label={<Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}><SentimentSatisfiedAltIcon color="success" /> Positive</Box>} />
                <FormControlLabel value="Neutral" control={<Radio color="info" />} label={<Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}><SentimentNeutralIcon color="info" /> Neutral</Box>} />
                <FormControlLabel value="Negative" control={<Radio color="error" />} label={<Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}><SentimentDissatisfiedIcon color="error" /> Negative</Box>} />
              </RadioGroup>
            )}
          />
        </Box>

        <SectionTitle title="Outcomes" />
        <Box sx={{ mb: 3 }}>
          <Controller
            name="outcomes"
            control={control}
            render={({ field }) => (
              <TextField {...field} fullWidth placeholder="Key outcomes or agreements..." multiline rows={2} variant="outlined" />
            )}
          />
        </Box>

        <SectionTitle title="Follow-up Actions" />
        <Box sx={{ mb: 3 }}>
          <Controller
            name="followUpsText"
            control={control}
            render={({ field }) => (
              <TextField {...field} fullWidth placeholder="Enter next steps or tasks..." multiline rows={3} variant="outlined" />
            )}
          />
          {formState.aiSuggestedFollowUps && formState.aiSuggestedFollowUps.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary" fontWeight="bold">AI Suggested Follow-ups:</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                {formState.aiSuggestedFollowUps.map((fu, idx) => (
                  <Typography 
                    key={idx} 
                    variant="caption" 
                    color="primary.main" 
                    sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                    onClick={() => appendSuggestedFollowUp(fu)}
                  >
                    + {fu.action_item} {fu.due_date ? `(Due: ${fu.due_date})` : ''}
                  </Typography>
                ))}
              </Box>
            </Box>
          )}
        </Box>
        
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
          <Button variant="outlined" color="inherit" sx={{ mr: 2 }} onClick={() => reset()}>
            Reset Form
          </Button>
          <Button type="submit" variant="contained" color="primary" disableElevation disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save Interaction'}
          </Button>
        </Box>

        <Snackbar open={toast.open} autoHideDuration={6000} onClose={() => setToast({ ...toast, open: false })}>
          <Alert onClose={() => setToast({ ...toast, open: false })} severity={toast.severity} sx={{ width: '100%' }}>
            {toast.message}
          </Alert>
        </Snackbar>
      </Box>
    </Paper>
  );
};

export default InteractionForm;
