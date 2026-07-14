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
  interactionType: string;
  interactionDate: string;
  interactionTime: string;
  attendees: string;
  topicsDiscussed: string;
  materialsShared: EntityOption[];
  samplesDistributed: EntityOption[];
  sentiment: string;
  outcomes: string;
  followUpsText: string;
  aiSuggestedFollowUps: FollowUpItem[];
}

const initialFormState: InteractionFormState = {
  hcp: null,
  interactionType: 'Meeting',
  interactionDate: '',
  interactionTime: '',
  attendees: '',
  topicsDiscussed: '',
  materialsShared: [],
  samplesDistributed: [],
  sentiment: '',
  outcomes: '',
  followUpsText: '',
  aiSuggestedFollowUps: [],
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
export interface HCPCandidateItem {
  id: string;
  name: string;
  specialty: string;
}

export interface UpdatedFieldInfo {
  field: string;
  label: string;
  oldValue: string;
  newValue: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
  isExtractionPreview?: boolean;
  isEditSummary?: boolean;
  extractionData?: Partial<InteractionFormState>;
  rawBackendData?: any;
  isAccepted?: boolean;
  hcpCandidates?: HCPCandidateItem[];
  candidateSelected?: boolean;
  updatedFields?: UpdatedFieldInfo[];
  historyData?: any[];
  followUpsChecklist?: any[];
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
    acceptDuplicateExtraction: (state, action: PayloadAction<string>) => {
      const msg = state.messages.find(m => m.id === action.payload);
      if (msg) {
        msg.isAccepted = true;
      }
    },
    markCandidateSelected: (state, action: PayloadAction<string>) => {
      const msg = state.messages.find(m => m.id === action.payload);
      if (msg) {
        msg.candidateSelected = true;
      }
    },
    toggleFollowUpChecklist: (state, action: PayloadAction<{ messageId: string, taskId: string, status: string }>) => {
      const msg = state.messages.find(m => m.id === action.payload.messageId);
      if (msg && msg.followUpsChecklist) {
        const task = msg.followUpsChecklist.find(t => t.id === action.payload.taskId);
        if (task) {
          task.status = action.payload.status;
        }
      }
    },
  },
});

export const { updateForm, resetForm } = formSlice.actions;
export const { addMessage, setProcessing, acceptDuplicateExtraction, markCandidateSelected, toggleFollowUpChecklist } = chatSlice.actions;

export const store = configureStore({
  reducer: {
    form: formSlice.reducer,
    chat: chatSlice.reducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
