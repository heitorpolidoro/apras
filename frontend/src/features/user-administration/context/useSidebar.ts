import { useContext } from "react";
import { SidebarContext, type SidebarContextValue } from "./SidebarContext";

export const useSidebar = (): SidebarContextValue => {
  return useContext(SidebarContext);
};

export type { SidebarContextValue };
