import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface HCP {
  id: string;
  first_name: string;
  last_name: string;
  specialty: string;
}

export interface Product {
  id: string;
  name: string;
  therapeutic_area: string;
}

export interface InteractionPayload {
  hcp_id: string;
  summary: string;
  sentiment: string;
  interaction_date: string;
  product_ids: string[];
  follow_ups: any[];
}

export const crmApi = {
  getHCPs: async (): Promise<HCP[]> => {
    const response = await apiClient.get('/hcps');
    return response.data;
  },

  searchHCPs: async (query: string): Promise<HCP[]> => {
    if (!query) return [];
    const response = await apiClient.get(`/hcps/search?q=${query}`);
    return response.data;
  },
  
  searchProducts: async (query: string): Promise<Product[]> => {
    if (!query) return [];
    const response = await apiClient.get(`/products/search?q=${query}`);
    return response.data;
  },

  createHCP: async (firstName: string, lastName: string, specialty: string): Promise<any> => {
    const response = await apiClient.post('/hcps', { first_name: firstName, last_name: lastName, specialty });
    return response.data;
  },

  saveInteraction: async (payload: InteractionPayload): Promise<any> => {
    const response = await apiClient.post('/interactions', payload);
    return response.data;
  },

  processInteraction: async (message: string, threadId: string): Promise<any> => {
    const response = await apiClient.post('/ai/process-interaction', { message, thread_id: threadId });
    return response.data;
  },

  getFollowUps: async (): Promise<any[]> => {
    const response = await apiClient.get('/follow-ups');
    return response.data;
  },

  updateFollowUpStatus: async (followUpId: string, status: 'PENDING' | 'COMPLETED'): Promise<any> => {
    const response = await apiClient.patch(`/follow-ups/${follow_up_id}`, { status });
    return response.data;
  }
};
