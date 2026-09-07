# APRAS-55 — Reorganizar navegação com menu lateral colapsável agrupado por áreas funcionais

> **One deliverable, one PR, zero authorization regression.**
> Reorganize the frontend application's navigation from an overloaded 30-item flat
> horizontal navigation bar into a modern, responsive, collapsible lateral sidebar
> grouped into seven cohesive functional areas. Keep the top header clean, uncluttered,
> and focused on global identity and session controls. Preserve the declaration order
> of `NAV_ITEMS` and all `ROUTE_ACCESS` mappings to guarantee strict compatibility
> with `RootRedirect` fallback logic and permission gating.

---

## 1. Scope

### In Scope

1. **Collapsible Lateral Sidebar (`Sidebar.tsx`)**:
   - Fixed left sidebar on desktop (`md:` breakpoint, ≥ 768px) supporting two modes:
     - **Expanded mode** (`w-64`, 256px): displays application brand, collapsible functional group headers, route icons, and localized route title labels.
     - **Collapsed mode (Icon rail)** (`w-20`, 80px): compact rail displaying centered icons with hover tooltips/labels and visual group dividers, hiding text labels and group expansion chevrons.
   - User expansion/collapse preference toggled via header/sidebar button and persisted in `localStorage` under key `"apras_sidebar_collapsed"`.
   - Active route detection (`location.pathname === item.path`) highlighted with distinct background tint (`bg-primary/10`), active text color (`text-primary font-semibold`), and a vertical active indicator pill.
   - Accordion behavior for individual functional groups in expanded mode (allowing users to expand or collapse specific sections, with state managed in context).

2. **Mobile Off-Canvas Drawer**:
   - On viewports < 768px (`< md:`), the desktop fixed rail is hidden.
   - Sidebar behaves as an off-canvas drawer (`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw]`), overlaid atop a backdrop overlay (`bg-background/80 backdrop-blur-sm`).
   - Triggered by a prominent hamburger toggle button (`Menu` icon, `aria-label="Abrir menu"`) located on the left side of the top header.
   - Dismissed automatically upon clicking the backdrop overlay, clicking the drawer close button (`X` icon), or clicking any navigation link (`onNavigate`).

3. **Logical Functional Grouping (`NAV_GROUPS` in `routeAccess.ts`)**:
   - Organize all 30 navigation routes into 7 functional domains:
     - `operations` ("Operações" / "Operations"): `/dashboard`, `/categories`, `/projects`, `/purchases`, `/assets`.
     - `access` ("Acessos & Segurança" / "Gate & Security"): `/gate`, `/gate-monitor`, `/authorizations`, `/packages`, `/admin/access-control`.
     - `community` ("Comunidade & Convivência" / "Community & Social"): `/announcements`, `/documents`, `/reservations`, `/spaces`, `/voting`, `/occurrences`, `/feedback`.
     - `infractions` ("Infrações & Regras" / "Infractions & Rules"): `/my-infractions`, `/infractions`, `/infraction-rules`.
     - `registry` ("Cadastros" / "Registry"): `/lots`, `/users/contact-info`.
     - `financial` ("Financeiro & Planos" / "Financial & Plans"): `/finance`, `/subscription`.
     - `administration` ("Sistema" / "System"): `/admin/users`, `/admin/roles`, `/admin/photo-approvals`, `/admin/modules`, `/admin/plans`, `/admin/subscriptions`.
   - Every single route from `NAV_ITEMS` must be included in exactly one group (30 routes total: 5 + 5 + 7 + 3 + 2 + 2 + 6 = 30).

4. **Dynamic Empty Group Omission**:
   - Evaluate visible items dynamically using the simulated permission evaluator (`useCanShowMenuPredicate`).
   - If the active user has zero permissions to view any item in a given group, that entire group section and its header are completely omitted from the rendered DOM.

5. **Streamlined Top Header (`Navbar.tsx`)**:
   - Remove the flat horizontal scroll list of 30 navigation links from the top header.
   - Retain all global user and session controls:
     - Mobile drawer hamburger toggle button (`< md:`).
     - Desktop sidebar collapse/expand toggle button (`≥ md:`).
     - Compact mobile branding icon (`< md:`).
     - Multi-tenant switcher combobox (`<select>` rendered when `tenants.length >= 2`).
     - Role simulation controls (`SimulationControls` rendered when user holds `roles:update`).
     - Language switcher toggle buttons (`PT` / `EN`).
     - Authenticated user information (`user.full_name` and role badge pills).
     - Logout button (`t("common.logout")`).

6. **Adaptive Main Content Layout (`AppLayoutContent` in `App.tsx`)**:
   - Adjust left margin of main container (`AppLayoutContent`) and top header based on sidebar state:
     - Authenticated + Desktop Expanded: `md:ml-64`.
     - Authenticated + Desktop Collapsed: `md:ml-20`.
     - Mobile or Unauthenticated: `ml-0`.
   - Animate transitions smoothly with Tailwind `transition-all duration-300 ease-in-out`.

7. **Sidebar Context & Hook (`SidebarContext.tsx`, `useSidebar.ts`)**:
   - Centralized React context managing `isCollapsed`, `isMobileOpen`, and `collapsedGroups`.

8. **Internationalization (i18n)**:
   - Add localized group title strings under `nav.groups.*` and toggle button aria-labels in `en.json` and `pt.json`.

---

### Explicitly Not in Scope

- **No backend changes**: zero API endpoint, database schema, migration, or backend model alterations.
- **No changes to authorization logic or permissions**: `useCanAccess`, `useCanShowMenu`, `useCanOpenPath`, and `ROUTE_ACCESS` mappings remain structurally identical.
- **No changes to `NAV_ITEMS` declaration order**: `RootRedirect` relies on the exact declaration order of `NAV_ITEMS` for fallback landing resolution (`(canOpen(landing) && landing) || (canOpen("/dashboard") && "/dashboard") || NAV_ITEMS.find((item) => canOpen(item.path))?.path || "/welcome"`). The array order must not be modified.
- **No nested submenus beyond two levels**: navigation follows a clean 2-level hierarchy: functional groups containing flat route links.

---

## 2. Background & Problem Analysis

### 2.1 The Flat Navbar Overflow Issue

As APRAS expanded across operational features (tasks, categories, lots, visitors, gatehouse, occurrences, packages, voting, feedback, reservations, spaces, documents, projects, announcements, finance, assets, purchases, contact info, admin users, admin roles, photo approvals, access control, gate monitor, tenant modules, subscriptions, plans, infractions, infraction rules, my infractions), `NAV_ITEMS` grew to **30 distinct items**.

Rendering 30 text links horizontally in `<nav className="flex items-center space-x-4 overflow-x-auto">` caused:
1. **Severe horizontal overflow and layout clipping**: requiring endless horizontal scrolling on standard screens (1080p, 1440p) to find administration or infraction links.
2. **Cognitive overload**: related domain concepts (e.g. `gate`, `gate-monitor`, `access-control`, `authorizations`) were dispersed in arbitrary insertion order.
3. **Broken mobile experience**: navigating 30 items in a tiny scroll container on touch devices is error-prone and frustrating.

### 2.2 Navigation Architecture Invariants

`frontend/src/features/user-administration/access/routeAccess.ts` serves as the single source of truth for frontend access and navigation:
1. `ROUTE_ACCESS`: Maps every protected route path to its `AccessRule`.
2. `NAV_ITEMS`: Maps paths to display labels and access rules.
3. `RootRedirect` (`frontend/src/App.tsx`):
   ```typescript
   const target =
     (canOpen(landing) && landing) ||
     (canOpen("/dashboard") && "/dashboard") ||
     NAV_ITEMS.find((item) => canOpen(item.path))?.path ||
     "/welcome";
   ```
   If `NAV_ITEMS` were reordered, the fallback target for restricted users would change, breaking tests and user expectations.
4. `routeAccess.test.ts`: Pins the invariant that every `NAV_ITEMS` entry matches `ROUTE_ACCESS[item.path]`.

---

## 3. Detailed Approach

### 3.1 Data Structures: `NavGroup` and `NAV_GROUPS`

In `frontend/src/features/user-administration/access/routeAccess.ts`:

```typescript
export interface NavGroup {
  id: string;
  titleKey: string;
  itemPaths: readonly string[];
}

export interface NavItem {
  path: string;
  labelKey: string;
  access: AccessRule;
  iconName: string;
}
```

The 7 groups and their route mappings:

```typescript
export const NAV_GROUPS: readonly NavGroup[] = [
  {
    id: "operations",
    titleKey: "nav.groups.operations",
    itemPaths: [
      "/dashboard",
      "/categories",
      "/projects",
      "/purchases",
      "/assets",
    ],
  },
  {
    id: "access",
    titleKey: "nav.groups.access",
    itemPaths: [
      "/gate",
      "/gate-monitor",
      "/authorizations",
      "/packages",
      "/admin/access-control",
    ],
  },
  {
    id: "community",
    titleKey: "nav.groups.community",
    itemPaths: [
      "/announcements",
      "/documents",
      "/reservations",
      "/spaces",
      "/voting",
      "/occurrences",
      "/feedback",
    ],
  },
  {
    id: "infractions",
    titleKey: "nav.groups.infractions",
    itemPaths: [
      "/my-infractions",
      "/infractions",
      "/infraction-rules",
    ],
  },
  {
    id: "registry",
    titleKey: "nav.groups.registry",
    itemPaths: [
      "/lots",
      "/users/contact-info",
    ],
  },
  {
    id: "financial",
    titleKey: "nav.groups.financial",
    itemPaths: [
      "/finance",
      "/subscription",
    ],
  },
  {
    id: "administration",
    titleKey: "nav.groups.administration",
    itemPaths: [
      "/admin/users",
      "/admin/roles",
      "/admin/photo-approvals",
      "/admin/modules",
      "/admin/plans",
      "/admin/subscriptions",
    ],
  },
];
```

#### Verification of 30-route coverage:
- Operations (5): `/dashboard`, `/categories`, `/projects`, `/purchases`, `/assets`
- Access (5): `/gate`, `/gate-monitor`, `/authorizations`, `/packages`, `/admin/access-control`
- Community (7): `/announcements`, `/documents`, `/reservations`, `/spaces`, `/voting`, `/occurrences`, `/feedback`
- Infractions (3): `/my-infractions`, `/infractions`, `/infraction-rules`
- Registry (2): `/lots`, `/users/contact-info`
- Financial (2): `/finance`, `/subscription`
- Administration (6): `/admin/users`, `/admin/roles`, `/admin/photo-approvals`, `/admin/modules`, `/admin/plans`, `/admin/subscriptions`
- **Total: 30 routes (100% of NAV_ITEMS, no duplicates, no omissions)**.

`NAV_ITEMS` adds `iconName: string` (e.g. `"CheckSquare"`, `"Building"`, `"ShieldCheck"`) to each item in its exact original order.

### 3.2 State Management: `SidebarContext`

Create `frontend/src/features/user-administration/context/SidebarContext.tsx`:
- Local storage key: `"apras_sidebar_collapsed"`.
- Initializes `isCollapsed` from `localStorage.getItem("apras_sidebar_collapsed") === "true"`.
- Writes changes back to `localStorage` in an effect.
- Provides `isMobileOpen`, `toggleMobile`, `closeMobile`.
- Provides `collapsedGroups: Record<string, boolean>` and `toggleGroup: (groupId: string) => void`.

Create hook wrapper `frontend/src/features/user-administration/context/useSidebar.ts`:
```typescript
import { useContext } from "react";
import { SidebarContext, type SidebarContextValue } from "./SidebarContext";

export const useSidebar = (): SidebarContextValue => {
  return useContext(SidebarContext);
};
```

### 3.3 Dynamic Filter Helper: `useCanShowMenuPredicate`

In `frontend/src/features/user-administration/access/useCanAccess.ts`, expose a predicate hook:
```typescript
export const useCanShowMenuPredicate = (): ((rule?: AccessRule) => boolean) => {
  const set = useEffectivePermissionSet();
  const isSuperuser = useIsSuperuser();
  return (rule?: AccessRule) => evaluate(rule, set, isSuperuser);
};
```
This enables bulk filtering of group items without invoking individual React hooks inside loops.

### 3.4 Sidebar Component Architecture (`Sidebar.tsx`)

`frontend/src/features/user-administration/components/Sidebar.tsx`:

1. **Icon Mapping**:
   Maps icon names from `NAV_ITEMS` to Lucide React components:
   `CheckSquare`, `Tag`, `Building`, `UserCheck`, `ShieldCheck`, `BookOpen`, `Package`, `Vote`, `MessageSquare`, `CalendarDays`, `MapPin`, `FolderArchive`, `HardHat`, `Megaphone`, `DollarSign`, `Boxes`, `ShoppingCart`, `Phone`, `Users`, `Shield`, `Camera`, `KeyRound`, `Tv`, `Sliders`, `CreditCard`, `Sparkles`, `Building2`, `FileWarning`, `Scale`, `AlertCircle`.

2. **Group Pre-filtering (Empty Group Omission)**:
   ```typescript
   const canShow = useCanShowMenuPredicate();

   const groupsWithVisibleItems = NAV_GROUPS.map((group) => {
     const items = group.itemPaths
       .map((path) => NAV_ITEMS.find((it) => it.path === path))
       .filter((it): it is NavItem => Boolean(it))
       .filter((it) => canShow(it.access));
     return { group, visibleItems: items };
   }).filter(({ visibleItems }) => visibleItems.length > 0);
   ```
   If `visibleItems.length === 0`, the group is excluded entirely from rendering.

3. **Desktop Layout**:
   - `aside[aria-label="Menu principal"]`
   - Fixed position: `fixed inset-y-0 left-0 z-30 hidden md:block transition-all duration-300 ease-in-out`
   - Width: `isCollapsed ? "w-20" : "w-64"`
   - Top branding bar with application logo, title (hidden when collapsed), and collapse/expand toggle button (`PanelLeftClose` / `PanelLeftOpen`).
   - Scrollable area: `flex-1 overflow-y-auto overflow-x-hidden p-3 space-y-1`.
   - Items: In expanded mode, show icon + title + active left border pill; in collapsed mode, show centered icon with `title` tooltip and active pill.

4. **Mobile Drawer Layout**:
   - Rendered when `isMobileOpen === true`.
   - Backdrop overlay: `fixed inset-0 z-50 md:hidden bg-background/80 backdrop-blur-sm transition-opacity`.
   - Slide-in container: `fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] shadow-2xl animate-in slide-in-from-left duration-200`.
   - Close button (`X` icon) in drawer header.
   - Automatically calls `closeMobile` when any link is clicked or when the backdrop is clicked.

### 3.5 Top Header Simplification (`Navbar.tsx`)

`frontend/src/features/user-administration/components/Navbar.tsx`:
- Renders `<Sidebar />` inside fragment.
- Header element receives adaptive margin: `isCollapsed ? "md:ml-20" : "md:ml-64"`.
- Left side:
  - Mobile hamburger toggle (`<button aria-label="Abrir menu" onClick={toggleMobile} className="md:hidden ...">`).
  - Desktop collapse/expand toggle (`<button onClick={toggleCollapsed} className="hidden md:flex ...">`).
  - Mobile logo.
- Right side:
  - Multi-tenant switcher dropdown (`tenants.length >= 2`).
  - Role simulation controls (`canSimulate = usePermissionSet().has("roles:update")`).
  - Language toggle (`PT` / `EN`).
  - User name and role tags.
  - Logout button.
- Clean and free of all 30 horizontal navigation links.

### 3.6 Layout Adjustment in `App.tsx`

In `frontend/src/App.tsx`:
- Wrap router tree in `<SidebarProvider>`.
- Wrap main element in `AppLayoutContent`:
  ```typescript
  const AppLayoutContent: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { isAuthenticated } = useAuth();
    const { isCollapsed } = useSidebar();
    return (
      <div
        className={cn(
          "min-h-screen flex flex-col bg-background text-foreground transition-all duration-300 ease-in-out",
          isAuthenticated && (isCollapsed ? "md:ml-20" : "md:ml-64"),
        )}
      >
        <SimulationBanner />
        <main className="flex-1">{children}</main>
      </div>
    );
  };
  ```

### 3.7 Localization (i18n)

Add keys in `frontend/src/i18n/locales/pt.json`:
```json
"nav": {
  "collapseMenu": "Recolher menu",
  "expandMenu": "Expandir menu",
  "groups": {
    "operations": "Operações",
    "access": "Acessos & Segurança",
    "community": "Comunidade & Convivência",
    "infractions": "Infrações & Regras",
    "registry": "Cadastros",
    "financial": "Financeiro & Planos",
    "administration": "Sistema"
  }
}
```

Add keys in `frontend/src/i18n/locales/en.json`:
```json
"nav": {
  "collapseMenu": "Collapse menu",
  "expandMenu": "Expand menu",
  "groups": {
    "operations": "Operations",
    "access": "Gate & Security",
    "community": "Community & Social",
    "infractions": "Infractions & Rules",
    "registry": "Registry",
    "financial": "Financial & Plans",
    "administration": "System"
  }
}
```

---

## 4. Test Strategy

1. **Unit Tests for Sidebar (`Sidebar.test.tsx`)**:
   - **Group Rendering & Permission Gating**: Verify that users with partial permissions only see groups that contain accessible items, and that empty groups are completely absent from the DOM.
   - **Desktop Collapse/Expand & LocalStorage**: Verify clicking the collapse button shrinks the sidebar to `w-20`, toggles button text to "Expandir menu", and stores `"true"` in `localStorage.getItem("apras_sidebar_collapsed")`. Verify clicking expand restores `"false"`.
   - **Accordion Sections**: Verify expanding/collapsing group accordions updates `aria-expanded` and hides/shows group item links.
   - **Active Link Styling**: Verify the current path (`/dashboard`) receives `text-primary` and active background styling.
   - **Mobile Drawer Behavior**: Verify hamburger opens the mobile drawer, clicking backdrop or close button calls `closeMobile`, and clicking any navigation link triggers navigation and closes the mobile drawer.

2. **Integration & Regression Tests**:
   - Existing Navbar permission tests (`Navbar.permissions.test.tsx`, `Navbar.modules.test.tsx`, `Navbar.tenantAdmin.test.tsx`).
   - `routeAccess.test.ts` verifying all 30 routes match `ROUTE_ACCESS`.
   - `RootRedirect.test.tsx` verifying fallback chain remains unaffected.
   - Full Vitest suite passing (144 test files, 1319+ tests).

---

## 5. Expected Results

- [ ] ER-1: The horizontal flat list of 30 navigation links is removed from `Navbar.tsx`, replaced by a responsive lateral sidebar (`Sidebar.tsx`) grouped into 7 functional areas (`NAV_GROUPS`).
- [ ] ER-2: All 30 navigation routes from `NAV_ITEMS` are mapped into `NAV_GROUPS` with zero omissions and zero duplicates, preserving the original array declaration order and `ROUTE_ACCESS` entries of `NAV_ITEMS`.
- [ ] ER-3: On desktop (≥ 768px), the sidebar supports expanded (`w-64`) and collapsed icon-rail (`w-20`) modes, toggled via UI button and persisting state in `localStorage` under key `"apras_sidebar_collapsed"`.
- [ ] ER-4: On mobile (< 768px), the sidebar operates as an off-canvas drawer opened via a hamburger toggle button in the header and closed by link selection, backdrop click, or close button.
- [ ] ER-5: Functional groups containing zero accessible items for the active user/simulated profile are automatically omitted from the rendered DOM without orphan headers or dividers.
- [ ] ER-6: The top header (`Navbar.tsx`) retains the tenant switcher combobox, role simulation controls, language switcher, user info, and logout button, adjusting its margin dynamically to match desktop sidebar expansion state.
- [ ] ER-7: Active routes are highlighted visually (`bg-primary/10 text-primary` and vertical indicator pill) and all group titles and menu controls support both `pt` and `en` locales.
- [ ] ER-8: All existing frontend unit and integration tests pass without regression (144 test files, 1319+ tests).
