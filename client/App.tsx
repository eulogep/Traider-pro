import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { SettingsProvider } from "@/lib/settingsContext";
import Index from "./pages/Index";
import Dashboard from "./pages/Dashboard";
import Trading from "./pages/Trading";
import Optimizer from "./pages/Optimizer";
import Backtest from "./pages/Backtest";
import Research from "./pages/Research";
import EaAudit from "./pages/EaAudit";
import BotAnalysis from "./pages/BotAnalysis";
import Automation from "./pages/Automation";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <SettingsProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "") || undefined}>
          <AppShell>
            <Routes>
              <Route path="/" element={<Index />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/trading" element={<Trading />} />
              <Route path="/optimizer" element={<Optimizer />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/research" element={<Research />} />
              <Route path="/ea-audit" element={<EaAudit />} />
              <Route path="/bot-analysis" element={<BotAnalysis />} />
              <Route path="/automation" element={<Automation />} />
              <Route path="/settings" element={<Settings />} />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </AppShell>
        </BrowserRouter>
      </TooltipProvider>
    </SettingsProvider>
  </QueryClientProvider>
);

export default App;
