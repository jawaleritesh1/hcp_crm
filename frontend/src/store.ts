import { configureStore, createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

// Interaction Form Slice
export interface EntityOption {
  id: string;
  name: string;
}

export interface FollowUpItem {
  action_item: string;
  priority: string;
  due_date: string | null;
  reason: string | null;
}

export interface InteractionFormState {
  hcp: EntityOption | null;
  interactionDate: string;
  sentiment: string;
  summary: string;
  products: EntityOption[];
  followUps: FollowUpItem[];
}

const initialFormState: InteractionFormState = {
  hcp: null,
  interactionDate: '',
  sentiment: '',
  summary: '',
  products: [],
  followUps: [],
};

export const formSlice = createSlice({
  name: 'form',
  initialState: initialFormState,
  reducers: {
    updateForm: (state, action: PayloadAction<Partial<InteractionFormState>>) => {
      return { ...state, ...action.payload };
    },
    resetForm: () => initialFormState,
  },
});

// Chat Slice
export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
  isExtractionPreview?: boolean;
  extractionData?: Partial<InteractionFormState>;
  rawBackendData?: any;
}

export interface ChatState {
  threadId: string;
  messages: ChatMessage[];
  isProcessing: boolean;
}

const initialChatState: ChatState = {
  threadId: crypto.randomUUID(),
  messages: [
    {
      id: '1',
      sender: 'ai',
      text: 'Hello! I am your AI assistant. Tell me about your interaction.',
      timestamp: new Date().toISOString(),
    }
  ],
  isProcessing: false,
};

export const chatSlice = createSlice({
  name: 'chat',
  initialState: initialChatState,
  reducers: {
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },
    setProcessing: (state, action: PayloadAction<boolean>) => {
      state.isProcessing = action.payload;
    },
  },
});

export const { updateForm, resetForm } = formSlice.actions;
export const { addMessage, setProcessing } = chatSlice.actions;

export const store = configureStore({
  reducer: {
    form: formSlice.reducer,
    chat: chatSlice.reducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
