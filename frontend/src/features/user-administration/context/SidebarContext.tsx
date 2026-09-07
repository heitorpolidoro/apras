import React, { createContext, useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "apras_sidebar_collapsed";

interface SidebarContextValue {
  isCollapsed: boolean;
  toggleCollapsed: () => void;
  setIsCollapsed: (value: boolean | ((prev: boolean) => boolean)) => void;
  isMobileOpen: boolean;
  toggleMobile: () => void;
  closeMobile: () => void;
  collapsedGroups: Record<string, boolean>;
  toggleGroup: (groupId: string) => void;
}

const defaultContextValue: SidebarContextValue = {
  isCollapsed: false,
  toggleCollapsed: () => {},
  setIsCollapsed: () => {},
  isMobileOpen: false,
  toggleMobile: () => {},
  closeMobile: () => {},
  collapsedGroups: {},
  toggleGroup: () => {},
};

const SidebarContext = createContext<SidebarContextValue>(defaultContextValue);

export const SidebarProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [isCollapsed, setIsCollapsedState] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored === "true";
    } catch {
      return false;
    }
  });

  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(isCollapsed));
    } catch {
      // Ignore storage write errors (e.g. private mode)
    }
  }, [isCollapsed]);

  const toggleCollapsed = useCallback(() => {
    setIsCollapsedState((prev) => !prev);
  }, []);

  const setIsCollapsed = useCallback(
    (value: boolean | ((prev: boolean) => boolean)) => {
      setIsCollapsedState(value);
    },
    [],
  );

  const toggleMobile = useCallback(() => {
    setIsMobileOpen((prev) => !prev);
  }, []);

  const closeMobile = useCallback(() => {
    setIsMobileOpen(false);
  }, []);

  const toggleGroup = useCallback((groupId: string) => {
    setCollapsedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  }, []);

  return (
    <SidebarContext.Provider
      value={{
        isCollapsed,
        toggleCollapsed,
        setIsCollapsed,
        isMobileOpen,
        toggleMobile,
        closeMobile,
        collapsedGroups,
        toggleGroup,
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
};

export { SidebarContext };
export type { SidebarContextValue };
