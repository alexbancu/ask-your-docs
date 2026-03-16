import { createContext, useContext } from "react";

interface DemoContextValue {
  demoSlug: string;
}

const DemoContext = createContext<DemoContextValue>({ demoSlug: "acme-corp" });

export const DemoProvider = DemoContext.Provider;

export function useDemo(): DemoContextValue {
  return useContext(DemoContext);
}
