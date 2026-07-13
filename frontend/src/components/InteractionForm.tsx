import { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useSelector, useDispatch } from 'react-redux';
import { 
  Box, 
  TextField, 
  Button, 
  Typography, 
  Autocomplete, 
  Chip,
  MenuItem,
  Divider,
  Stack,
  Snackbar,
  Alert
} from '@mui/material';
import type { RootState, InteractionFormState, EntityOption } from '../store';
import { resetForm } from '../store';
import { crmApi } from '../api/crmApi';

const sentimentOptions = ['Positive', 'Neutral', 'Negative'];

const InteractionForm = () => {
  const dispatch = useDispatch();
  const formState = useSelector((state: RootState) => state.form);
  
  const [hcpOptions, setHcpOptions] = useState<EntityOption[]>([]);
  const [productOptions, setProductOptions] = useState<EntityOption[]>([]);
  const [loadingHCP, setLoadingHCP] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(false);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

  const { control, handleSubmit, reset } = useForm<InteractionFormState>({
    defaultValues: formState,
    values: formState
  });

  const searchHCPs = async (query: string) => {
    if (!query || query.length < 2) {
      setHcpOptions([]);
      return;
    }
    setLoadingHCP(true);
    try {
      const hcps = await crmApi.searchHCPs(query);
      const mapped = hcps.map(h => ({ id: h.id, name: `Dr. ${h.first_name} ${h.last_name} - ${h.specialty}` }));
      
      const cleanName = query.replace(/^Dr\.\s*/i, '').replace(/^Dr\s*/i, '').trim();
      const hasExact = mapped.some(m => m.name.toLowerCase().includes(cleanName.toLowerCase()));
      
      if (!hasExact) {
        mapped.push({
          id: 'new',
          name: `Add 'Dr. ${cleanName}' as a new HCP`,
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

  const onSubmit = async (data: InteractionFormState) => {
    if (!data.hcp) {
      setToast({ open: true, message: 'Please select an HCP.', severity: 'error' });
      return;
    }

    setIsSubmitting(true);
    try {
      let hcpId = data.hcp.id;
      
      if (hcpId === 'new') {
        const rawName = (data.hcp as any).customName || data.hcp.name.replace(/^Add\s+'/i, '').replace(/'\s+as\s+a\s+new\s+HCP$/i, '').replace(/^Dr\.\s*/i, '').trim();
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
        summary: data.summary,
        sentiment: data.sentiment || 'Neutral',
        interaction_date: data.interactionDate || new Date().toISOString().split('T')[0],
        product_ids: data.products.map(p => p.id),
        follow_ups: data.followUps
      };

      await crmApi.saveInteraction(payload);
      setToast({ open: true, message: 'Interaction Saved Successfully!', severity: 'success' });
      dispatch(resetForm());
      reset();
    } catch (error) {
      console.error(error);
      setToast({ open: true, message: 'Failed to save interaction.', severity: 'error' });
    }
    setIsSubmitting(false);
  };

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
        <Box>
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
                onInputChange={(_, newInputValue) => {
                  searchHCPs(newInputValue);
                }}
                loading={loadingHCP}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="HCP Name"
                    variant="outlined"
                    error={!!error}
                    helperText={error?.message}
                    size="small"
                  />
                )}
              />
            )}
          />
        </Box>
        <Box>
          <Controller
            name="interactionDate"
            control={control}
            rules={{ required: 'Date is required' }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                fullWidth
                label="Interaction Date"
                type="date"
                variant="outlined"
                slotProps={{ inputLabel: { shrink: true } }}
                error={!!error}
                helperText={error?.message}
                size="small"
              />
            )}
          />
        </Box>
        
        <Box sx={{ gridColumn: '1 / -1' }}>
          <Controller
            name="products"
            control={control}
            render={({ field }) => (
              <Autocomplete
                {...field}
                multiple
                options={productOptions}
                getOptionLabel={(option) => option.name}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                onChange={(_, newValue) => field.onChange(newValue)}
                onInputChange={(_, newInputValue) => {
                  searchProducts(newInputValue);
                }}
                loading={loadingProducts}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="outlined"
                    label="Products Discussed"
                    placeholder="Search Products..."
                    size="small"
                  />
                )}
              />
            )}
          />
        </Box>

        <Box>
          <Controller
            name="sentiment"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                select
                fullWidth
                label="Sentiment"
                variant="outlined"
                size="small"
              >
                {sentimentOptions.map((option) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
        </Box>

        <Box sx={{ gridColumn: '1 / -1' }}>
          <Controller
            name="summary"
            control={control}
            rules={{ required: 'Summary is required' }}
            render={({ field, fieldState: { error } }) => (
              <TextField
                {...field}
                fullWidth
                label="Interaction Summary"
                multiline
                rows={4}
                variant="outlined"
                error={!!error}
                helperText={error?.message}
              />
            )}
          />
        </Box>

        <Box sx={{ gridColumn: '1 / -1' }}>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>Follow-ups</Typography>
          <Controller
            name="followUps"
            control={control}
            render={({ field }) => (
              <Stack spacing={1}>
                {field.value?.length > 0 ? field.value.map((fu, idx) => (
                  <Chip 
                    key={idx} 
                    label={`${fu.action_item}${fu.due_date ? ` (Due: ${fu.due_date})` : ''}`}
                    onDelete={() => {
                      const newArr = [...field.value];
                      newArr.splice(idx, 1);
                      field.onChange(newArr);
                    }}
                    color="secondary"
                    variant="outlined"
                  />
                )) : <Typography variant="caption" color="text.secondary">No follow-ups added.</Typography>}
              </Stack>
            )}
          />
        </Box>
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
  );
};

export default InteractionForm;
