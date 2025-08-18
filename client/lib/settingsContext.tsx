import React, { createContext, useContext, useReducer, useEffect } from 'react';

export interface AppSettings {
  // Appearance
  darkMode: boolean;
  colorTheme: 'professional' | 'high-contrast' | 'colorblind' | 'minimal';
  chartStyle: 'candlestick' | 'line' | 'bar' | 'area';
  dashboardLayout: 'grid' | 'list' | 'compact' | 'detailed';
  
  // Regional
  language: string;
  timezone: string;
  currency: string;
  numberFormat: 'us' | 'eu' | 'space';
  
  // Trading
  defaultRisk: number;
  defaultStopLoss: number;
  defaultTakeProfit: number;
  defaultPositionSize: 'auto' | 'fixed' | 'percent';
  slippageTolerance: number;
  oneClickTrading: boolean;
  
  // AI Settings
  aiSignalValidation: boolean;
  aiConfidenceThreshold: number;
  optimizationFrequency: 'realtime' | 'hourly' | 'daily' | 'weekly' | 'manual';
  modelSelection: 'auto' | 'xgboost' | 'lstm' | 'ensemble';
  learningMode: boolean;
  
  // MT5 Connection
  mt5Server: string;
  mt5Login: string;
  mt5Password: string;
  enableEA: boolean;
  allowAutoTrading: boolean;
  realtimeDataFeed: boolean;
  updateFrequency: number;
  
  // Notifications
  tradeExecution: boolean;
  profitLossTargets: boolean;
  aiSignals: boolean;
  systemErrors: boolean;
  marketNews: boolean;
  inAppNotifications: boolean;
  emailAlerts: boolean;
  pushNotifications: boolean;
  emailAddress: string;
  phoneNumber: string;
  telegramToken: string;
  
  // Security
  twoFactorAuth: boolean;
  sessionTimeout: number;
  ipWhitelist: boolean;
  allowedIPs: string;
  
  // Backup
  automaticBackups: boolean;
  backupFrequency: 'hourly' | 'daily' | 'weekly' | 'monthly';
  backupLocation: 'cloud' | 'local' | 'both';
}

const defaultSettings: AppSettings = {
  // Appearance
  darkMode: true,
  colorTheme: 'professional',
  chartStyle: 'candlestick',
  dashboardLayout: 'grid',
  
  // Regional
  language: 'en',
  timezone: 'utc',
  currency: 'usd',
  numberFormat: 'us',
  
  // Trading
  defaultRisk: 2,
  defaultStopLoss: 50,
  defaultTakeProfit: 100,
  defaultPositionSize: 'auto',
  slippageTolerance: 3,
  oneClickTrading: true,
  
  // AI Settings
  aiSignalValidation: true,
  aiConfidenceThreshold: 75,
  optimizationFrequency: 'daily',
  modelSelection: 'auto',
  learningMode: true,
  
  // MT5 Connection
  mt5Server: 'mt5.demo-server.com:443',
  mt5Login: '12345678',
  mt5Password: 'demo123',
  enableEA: true,
  allowAutoTrading: true,
  realtimeDataFeed: true,
  updateFrequency: 1000,
  
  // Notifications
  tradeExecution: true,
  profitLossTargets: true,
  aiSignals: true,
  systemErrors: true,
  marketNews: false,
  inAppNotifications: true,
  emailAlerts: true,
  pushNotifications: true,
  emailAddress: 'trader@example.com',
  phoneNumber: '',
  telegramToken: '',
  
  // Security
  twoFactorAuth: true,
  sessionTimeout: 30,
  ipWhitelist: false,
  allowedIPs: '',
  
  // Backup
  automaticBackups: true,
  backupFrequency: 'daily',
  backupLocation: 'cloud',
};

type SettingsAction = 
  | { type: 'UPDATE_SETTING'; key: keyof AppSettings; value: any }
  | { type: 'LOAD_SETTINGS'; settings: Partial<AppSettings> }
  | { type: 'RESET_SETTINGS' }
  | { type: 'EXPORT_SETTINGS' }
  | { type: 'IMPORT_SETTINGS'; settings: Partial<AppSettings> };

interface SettingsState {
  settings: AppSettings;
  loading: boolean;
  error: string | null;
  lastSaved: Date | null;
}

const initialState: SettingsState = {
  settings: defaultSettings,
  loading: false,
  error: null,
  lastSaved: null,
};

function settingsReducer(state: SettingsState, action: SettingsAction): SettingsState {
  switch (action.type) {
    case 'UPDATE_SETTING':
      const newSettings = {
        ...state.settings,
        [action.key]: action.value
      };
      
      // Save to localStorage
      localStorage.setItem('aiTraderSettings', JSON.stringify(newSettings));
      
      return {
        ...state,
        settings: newSettings,
        lastSaved: new Date(),
        error: null,
      };
      
    case 'LOAD_SETTINGS':
      return {
        ...state,
        settings: { ...state.settings, ...action.settings },
        loading: false,
        error: null,
      };
      
    case 'RESET_SETTINGS':
      localStorage.setItem('aiTraderSettings', JSON.stringify(defaultSettings));
      return {
        ...state,
        settings: defaultSettings,
        lastSaved: new Date(),
        error: null,
      };
      
    case 'EXPORT_SETTINGS':
      const dataStr = JSON.stringify(state.settings, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `ai-trader-settings-${new Date().toISOString().split('T')[0]}.json`;
      link.click();
      URL.revokeObjectURL(url);
      
      return state;
      
    case 'IMPORT_SETTINGS':
      const importedSettings = { ...state.settings, ...action.settings };
      localStorage.setItem('aiTraderSettings', JSON.stringify(importedSettings));
      
      return {
        ...state,
        settings: importedSettings,
        lastSaved: new Date(),
        error: null,
      };
      
    default:
      return state;
  }
}

interface SettingsContextType {
  state: SettingsState;
  updateSetting: (key: keyof AppSettings, value: any) => void;
  resetSettings: () => void;
  exportSettings: () => void;
  importSettings: (settings: Partial<AppSettings>) => void;
  saveSettings: () => Promise<void>;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(settingsReducer, initialState);

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('aiTraderSettings');
    if (savedSettings) {
      try {
        const parsedSettings = JSON.parse(savedSettings);
        dispatch({ type: 'LOAD_SETTINGS', settings: parsedSettings });
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    }
  }, []);

  // Apply theme changes to document
  useEffect(() => {
    const { darkMode, colorTheme } = state.settings;
    
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    // Apply color theme
    document.documentElement.setAttribute('data-theme', colorTheme);
  }, [state.settings.darkMode, state.settings.colorTheme]);

  const updateSetting = (key: keyof AppSettings, value: any) => {
    dispatch({ type: 'UPDATE_SETTING', key, value });
  };

  const resetSettings = () => {
    dispatch({ type: 'RESET_SETTINGS' });
  };

  const exportSettings = () => {
    dispatch({ type: 'EXPORT_SETTINGS' });
  };

  const importSettings = (settings: Partial<AppSettings>) => {
    dispatch({ type: 'IMPORT_SETTINGS', settings });
  };

  const saveSettings = async (): Promise<void> => {
    try {
      // In a real app, this would make an API call to save settings
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(state.settings),
      });
      
      if (!response.ok) {
        throw new Error('Failed to save settings');
      }
      
      console.log('Settings saved successfully');
    } catch (error) {
      console.error('Failed to save settings:', error);
      // Still save locally even if API fails
      localStorage.setItem('aiTraderSettings', JSON.stringify(state.settings));
    }
  };

  const value: SettingsContextType = {
    state,
    updateSetting,
    resetSettings,
    exportSettings,
    importSettings,
    saveSettings,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}

// Hook for specific setting
export function useSetting<K extends keyof AppSettings>(key: K): [AppSettings[K], (value: AppSettings[K]) => void] {
  const { state, updateSetting } = useSettings();
  
  return [
    state.settings[key],
    (value: AppSettings[K]) => updateSetting(key, value)
  ];
}
