import { useCallback, useEffect, useState } from "react";

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
}

let toastCount = 0;

// Module-level store shared by every useToast() caller (pages AND the <Toaster/>).
let memoryState: ToastState = { toasts: [] };
const listeners = new Set<(s: ToastState) => void>();

function setState(update: (prev: ToastState) => ToastState) {
  memoryState = update(memoryState);
  listeners.forEach((l) => l(memoryState));
}

/** Read-only snapshot of the shared store (used by tests). */
export function getToastState(): ToastState {
  return memoryState;
}

export function dismiss(toastId: string) {
  setState((prev) => ({ toasts: prev.toasts.filter((t) => t.id !== toastId) }));
}

export function toast({
  title,
  description,
  variant = "default",
  duration = 5000,
}: Omit<Toast, "id">) {
  const id = (++toastCount).toString();
  const newToast: Toast = { id, title, description, variant, duration };
  setState((prev) => ({ toasts: [...prev.toasts, newToast] }));
  if (duration > 0) setTimeout(() => dismiss(id), duration); // auto dismiss
  return id;
}

export function useToast() {
  const [state, setLocal] = useState<ToastState>(memoryState);

  useEffect(() => {
    listeners.add(setLocal);
    return () => {
      listeners.delete(setLocal);
    };
  }, []);

  const dismissAll = useCallback(() => setState(() => ({ toasts: [] })), []);

  return {
    toast,
    dismiss,
    dismissAll,
    toasts: state.toasts,
  };
}
