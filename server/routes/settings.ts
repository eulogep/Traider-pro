import { RequestHandler } from "express";
import { z } from "zod";
import fs from "fs/promises";
import path from "path";

// Settings validation schema
const SettingsSchema = z.object({
  // Appearance
  darkMode: z.boolean(),
  colorTheme: z.enum([
    "professional",
    "high-contrast",
    "colorblind",
    "minimal",
  ]),
  chartStyle: z.enum(["candlestick", "line", "bar", "area"]),
  dashboardLayout: z.enum(["grid", "list", "compact", "detailed"]),

  // Regional
  language: z.string(),
  timezone: z.string(),
  currency: z.string(),
  numberFormat: z.enum(["us", "eu", "space"]),

  // Trading
  defaultRisk: z.number().min(0.1).max(10),
  defaultStopLoss: z.number().positive(),
  defaultTakeProfit: z.number().positive(),
  defaultPositionSize: z.enum(["auto", "fixed", "percent"]),
  slippageTolerance: z.number().min(0),
  oneClickTrading: z.boolean(),

  // AI Settings
  aiSignalValidation: z.boolean(),
  aiConfidenceThreshold: z.number().min(50).max(95),
  optimizationFrequency: z.enum([
    "realtime",
    "hourly",
    "daily",
    "weekly",
    "manual",
  ]),
  modelSelection: z.enum(["auto", "xgboost", "lstm", "ensemble"]),
  learningMode: z.boolean(),

  // MT5 Connection
  mt5Server: z.string(),
  mt5Login: z.string(),
  mt5Password: z.string(),
  enableEA: z.boolean(),
  allowAutoTrading: z.boolean(),
  realtimeDataFeed: z.boolean(),
  updateFrequency: z.number().positive(),

  // Notifications
  tradeExecution: z.boolean(),
  profitLossTargets: z.boolean(),
  aiSignals: z.boolean(),
  systemErrors: z.boolean(),
  marketNews: z.boolean(),
  inAppNotifications: z.boolean(),
  emailAlerts: z.boolean(),
  pushNotifications: z.boolean(),
  emailAddress: z.string().email().optional().or(z.literal("")),
  phoneNumber: z.string().optional(),
  telegramToken: z.string().optional(),

  // Security
  twoFactorAuth: z.boolean(),
  sessionTimeout: z.number().min(0),
  ipWhitelist: z.boolean(),
  allowedIPs: z.string().optional(),

  // Backup
  automaticBackups: z.boolean(),
  backupFrequency: z.enum(["hourly", "daily", "weekly", "monthly"]),
  backupLocation: z.enum(["cloud", "local", "both"]),
});

const SETTINGS_FILE = path.join(process.cwd(), "data", "settings.json");

// Ensure data directory exists
async function ensureDataDir() {
  try {
    await fs.mkdir(path.dirname(SETTINGS_FILE), { recursive: true });
  } catch (error) {
    console.error("Failed to create data directory:", error);
  }
}

// Get settings
export const getSettings: RequestHandler = async (req, res) => {
  try {
    await ensureDataDir();

    try {
      const data = await fs.readFile(SETTINGS_FILE, "utf-8");
      const settings = JSON.parse(data);
      res.json(settings);
    } catch (error) {
      // File doesn't exist, return default settings
      res.json({});
    }
  } catch (error) {
    console.error("Error reading settings:", error);
    res.status(500).json({ error: "Failed to read settings" });
  }
};

// Save settings
export const saveSettings: RequestHandler = async (req, res) => {
  try {
    // Validate the request body
    const validationResult = SettingsSchema.safeParse(req.body);

    if (!validationResult.success) {
      return res.status(400).json({
        error: "Invalid settings data",
        details: validationResult.error.issues,
      });
    }

    await ensureDataDir();

    // Save settings to file
    await fs.writeFile(
      SETTINGS_FILE,
      JSON.stringify(validationResult.data, null, 2),
    );

    res.json({ success: true, message: "Settings saved successfully" });
  } catch (error) {
    console.error("Error saving settings:", error);
    res.status(500).json({ error: "Failed to save settings" });
  }
};

// Reset settings
export const resetSettings: RequestHandler = async (req, res) => {
  try {
    await ensureDataDir();

    // Delete the settings file
    try {
      await fs.unlink(SETTINGS_FILE);
    } catch (error) {
      // File might not exist, that's okay
    }

    res.json({ success: true, message: "Settings reset successfully" });
  } catch (error) {
    console.error("Error resetting settings:", error);
    res.status(500).json({ error: "Failed to reset settings" });
  }
};

// Backup settings
export const backupSettings: RequestHandler = async (req, res) => {
  try {
    await ensureDataDir();

    try {
      const data = await fs.readFile(SETTINGS_FILE, "utf-8");
      const settings = JSON.parse(data);

      const timestamp = new Date().toISOString().split("T")[0];
      const filename = `ai-trader-settings-${timestamp}.json`;

      res.setHeader("Content-Type", "application/json");
      res.setHeader(
        "Content-Disposition",
        `attachment; filename="${filename}"`,
      );
      res.send(JSON.stringify(settings, null, 2));
    } catch (error) {
      res.status(404).json({ error: "No settings found to backup" });
    }
  } catch (error) {
    console.error("Error backing up settings:", error);
    res.status(500).json({ error: "Failed to backup settings" });
  }
};
