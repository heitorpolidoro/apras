import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  NAV_GROUPS,
  NAV_ITEMS,
  type NavItem,
  type NavGroup,
} from "../access/routeAccess";
import { useCanShowMenuPredicate } from "../access/useCanAccess";
import { useSidebar } from "../context/useSidebar";
import { cn } from "../../../lib/utils";
import {
  Home,
  CheckSquare,
  Tag,
  Building,
  UserCheck,
  ShieldCheck,
  BookOpen,
  Package,
  Vote,
  MessageSquare,
  CalendarDays,
  MapPin,
  FolderArchive,
  HardHat,
  Megaphone,
  DollarSign,
  Boxes,
  ShoppingCart,
  Phone,
  Users,
  Shield,
  Camera,
  KeyRound,
  Tv,
  Sliders,
  CreditCard,
  Sparkles,
  Building2,
  FileWarning,
  Scale,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  X,
  type LucideIcon,
} from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  CheckSquare,
  Tag,
  Building,
  UserCheck,
  ShieldCheck,
  BookOpen,
  Package,
  Vote,
  MessageSquare,
  CalendarDays,
  MapPin,
  FolderArchive,
  HardHat,
  Megaphone,
  DollarSign,
  Boxes,
  ShoppingCart,
  Phone,
  Users,
  Shield,
  Camera,
  KeyRound,
  Tv,
  Sliders,
  CreditCard,
  Sparkles,
  Building2,
  FileWarning,
  Scale,
  AlertCircle,
};

const SidebarItemLink: React.FC<{
  item: NavItem;
  isCollapsed: boolean;
  onNavigate?: () => void;
}> = ({ item, isCollapsed, onNavigate }) => {
  const location = useLocation();
  const { t } = useTranslation();

  const isActive = location.pathname === item.path;
  const IconComponent = ICON_MAP[item.iconName] || CheckSquare;
  const label = t(item.labelKey);

  return (
    <Link
      to={item.path}
      onClick={onNavigate}
      title={isCollapsed ? label : undefined}
      aria-label={label}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group relative",
        isActive
          ? "bg-primary/10 text-primary font-semibold"
          : "text-muted-foreground hover:bg-accent/60 hover:text-foreground font-medium",
        isCollapsed ? "justify-center px-2 py-2.5" : "",
      )}
    >
      <IconComponent
        className={cn(
          "size-4.5 shrink-0 transition-transform group-hover:scale-110",
          isActive
            ? "text-primary"
            : "text-muted-foreground group-hover:text-foreground",
        )}
      />
      {!isCollapsed && (
        <span className={cn("truncate", isActive && "text-primary")}>
          {label}
        </span>
      )}
      {isActive && (
        <div
          className={cn(
            "absolute left-0 top-1.5 bottom-1.5 w-1 bg-primary rounded-r-full",
            isCollapsed && "left-0.5",
          )}
        />
      )}
    </Link>
  );
};

const SidebarHomeLink: React.FC<{
  isCollapsed: boolean;
  onNavigate?: () => void;
}> = ({ isCollapsed, onNavigate }) => {
  const location = useLocation();
  const { t } = useTranslation();

  const isActive = location.pathname === "/";
  const label = t("nav.home");

  return (
    <Link
      to="/"
      onClick={onNavigate}
      title={isCollapsed ? label : undefined}
      aria-label={label}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group relative",
        isActive
          ? "bg-primary/10 text-primary font-semibold"
          : "text-muted-foreground hover:bg-accent/60 hover:text-foreground font-medium",
        isCollapsed ? "justify-center px-2 py-2.5" : "",
      )}
    >
      <Home
        className={cn(
          "size-4.5 shrink-0 transition-transform group-hover:scale-110",
          isActive
            ? "text-primary"
            : "text-muted-foreground group-hover:text-foreground",
        )}
      />
      {!isCollapsed && (
        <span className={cn("truncate", isActive && "text-primary")}>
          {label}
        </span>
      )}
      {isActive && (
        <div
          className={cn(
            "absolute left-0 top-1.5 bottom-1.5 w-1 bg-primary rounded-r-full",
            isCollapsed && "left-0.5",
          )}
        />
      )}
    </Link>
  );
};

const SidebarGroupSection: React.FC<{
  group: NavGroup;
  visibleItems: NavItem[];
  isCollapsed: boolean;
  isGroupCollapsed: boolean;
  onToggleGroup: () => void;
  onNavigate?: () => void;
}> = ({
  group,
  visibleItems,
  isCollapsed,
  isGroupCollapsed,
  onToggleGroup,
  onNavigate,
}) => {
  const { t } = useTranslation();

  if (visibleItems.length === 0) return null;

  return (
    <div className="py-1">
      {/* Group Header */}
      {!isCollapsed ? (
        <button
          type="button"
          onClick={onToggleGroup}
          aria-expanded={!isGroupCollapsed}
          className="w-full flex items-center justify-between px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground/80 hover:text-foreground transition-colors group"
        >
          <span className="truncate">{t(group.titleKey)}</span>
          <span className="text-muted-foreground/50 group-hover:text-foreground">
            {isGroupCollapsed ? (
              <ChevronRight className="size-3.5" />
            ) : (
              <ChevronDown className="size-3.5" />
            )}
          </span>
        </button>
      ) : (
        <div className="my-1.5 border-t border-border/50 mx-2" />
      )}

      {/* Items list */}
      {(!isGroupCollapsed || isCollapsed) && (
        <div className="mt-0.5 space-y-0.5">
          {visibleItems.map((item) => (
            <SidebarItemLink
              key={item.path}
              item={item}
              isCollapsed={isCollapsed}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const Sidebar: React.FC = () => {
  const { t } = useTranslation();
  const {
    isCollapsed,
    toggleCollapsed,
    isMobileOpen,
    closeMobile,
    collapsedGroups,
    toggleGroup,
  } = useSidebar();
  const canShow = useCanShowMenuPredicate();

  // Pre-calculate visible items for each group to avoid empty group headers
  const groupsWithVisibleItems = NAV_GROUPS.map((group) => {
    const items = group.itemPaths
      .map((path) => NAV_ITEMS.find((it) => it.path === path))
      .filter((it): it is NavItem => Boolean(it))
      .filter((it) => canShow(it.access));
    return {
      group,
      visibleItems: items,
    };
  }).filter(({ visibleItems }) => visibleItems.length > 0);

  const sidebarContent = (isMobileView: boolean) => {
    const collapsed = isMobileView ? false : isCollapsed;

    return (
      <div className="flex flex-col h-full bg-card border-r border-border/50 select-none">
        {/* Sidebar Brand / Header */}
        <div
          className={cn(
            "flex items-center justify-between h-16 px-4 border-b border-border/40 shrink-0",
            collapsed && "justify-center px-2",
          )}
        >
          <Link
            to="/"
            onClick={isMobileView ? closeMobile : undefined}
            className="flex items-center gap-2.5 hover:opacity-85 transition-opacity"
            title={t("common.appName")}
          >
            <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <div className="size-4 rounded-full bg-primary" />
            </div>
            {!collapsed && (
              <span className="text-lg font-black tracking-tight text-primary">
                {t("common.appName")}
              </span>
            )}
          </Link>

          {isMobileView ? (
            <button
              type="button"
              onClick={closeMobile}
              aria-label={t("common.close")}
              className="p-1.5 rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              <X className="size-5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={toggleCollapsed}
              aria-label={
                collapsed ? t("nav.expandMenu") : t("nav.collapseMenu")
              }
              title={collapsed ? t("nav.expandMenu") : t("nav.collapseMenu")}
              className="p-1.5 rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              {collapsed ? (
                <PanelLeftOpen className="size-4.5" />
              ) : (
                <PanelLeftClose className="size-4.5" />
              )}
            </button>
          )}
        </div>

        {/* Scrollable Navigation Groups */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-1">
          <div className="mb-2">
            <SidebarHomeLink
              isCollapsed={collapsed}
              onNavigate={isMobileView ? closeMobile : undefined}
            />
          </div>
          {groupsWithVisibleItems.map(({ group, visibleItems }) => (
            <SidebarGroupSection
              key={group.id}
              group={group}
              visibleItems={visibleItems}
              isCollapsed={collapsed}
              isGroupCollapsed={!!collapsedGroups[group.id]}
              onToggleGroup={() => toggleGroup(group.id)}
              onNavigate={isMobileView ? closeMobile : undefined}
            />
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Desktop Sidebar (visible on md and up) */}
      <aside
        aria-label="Menu principal"
        className={cn(
          "hidden md:block fixed inset-y-0 left-0 z-30 transition-all duration-300 ease-in-out",
          isCollapsed ? "w-20" : "w-64",
        )}
      >
        {sidebarContent(false)}
      </aside>

      {/* Mobile Drawer Overlay (visible on < md when isMobileOpen) */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-50 md:hidden bg-background/80 backdrop-blur-sm transition-opacity"
          onClick={closeMobile}
        >
          <div
            className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] shadow-2xl animate-in slide-in-from-left duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent(true)}
          </div>
        </div>
      )}
    </>
  );
};

export default Sidebar;
