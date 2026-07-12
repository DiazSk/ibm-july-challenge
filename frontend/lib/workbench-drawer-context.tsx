"use client";

import { createContext, useContext, useState } from "react";

interface WorkbenchDrawerContextValue {
  open: boolean;
  setOpen: (v: boolean) => void;
}

const WorkbenchDrawerContext = createContext<WorkbenchDrawerContextValue | null>(null);

export function WorkbenchDrawerProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <WorkbenchDrawerContext.Provider value={{ open, setOpen }}>
      {children}
    </WorkbenchDrawerContext.Provider>
  );
}

export function useWorkbenchDrawer() {
  const ctx = useContext(WorkbenchDrawerContext);
  if (!ctx) throw new Error("useWorkbenchDrawer must be used within WorkbenchDrawerProvider");
  return ctx;
}
