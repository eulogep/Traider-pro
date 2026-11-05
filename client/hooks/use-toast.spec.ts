// Non-regression: each useToast() call used to own its state, so toasts raised by a page
// never reached the <Toaster/> mounted in App. The store is now shared at module level.
import { afterEach, describe, expect, it, vi } from "vitest";
import { dismiss, getToastState, toast } from "./use-toast";

afterEach(() => vi.useRealTimers());

describe("shared toast store", () => {
  it("a toast raised anywhere is visible in the shared state, then dismissed", () => {
    const a = toast({ title: "Paramètres enregistrés", duration: 0 });
    const b = toast({ title: "Erreur", variant: "destructive", duration: 0 });
    expect(getToastState().toasts.map((t) => t.id)).toEqual(expect.arrayContaining([a, b]));
    dismiss(a);
    expect(getToastState().toasts.map((t) => t.id)).not.toContain(a);
    dismiss(b);
  });

  it("auto-dismisses after its duration", () => {
    vi.useFakeTimers();
    const id = toast({ title: "temp", duration: 1000 });
    expect(getToastState().toasts.some((t) => t.id === id)).toBe(true);
    vi.advanceTimersByTime(1001);
    expect(getToastState().toasts.some((t) => t.id === id)).toBe(false);
  });
});
