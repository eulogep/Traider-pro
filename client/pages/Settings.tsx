import { Settings as SettingsIcon } from "lucide-react";
import Placeholder from "./Placeholder";

export default function Settings() {
  return (
    <Placeholder
      title="System Settings"
      description="Configure your AI Trader Optimizer settings, MT5 connections, risk parameters, notification preferences, and trading automation rules."
      icon={SettingsIcon}
    />
  );
}
