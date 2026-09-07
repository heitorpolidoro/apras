# APRAS-56 — Criar Dashboard Geral e migrar tarefas para /tasks

> **One deliverable, one PR, zero authorization regression.**
> Migrate the task management interface from `/dashboard` to `/tasks`, maintain a backward-compatibility redirect from `/dashboard` to `/tasks`, establish a new General Dashboard (`GeneralDashboardPage.tsx`) mounted at `/` as the primary home overview for authenticated users with active tenant context, and update sidebar navigation and `RootRedirect` accordingly.

---

## 1. Scope

### In Scope

1. **Migrate Task Management to `/tasks`**:
   - Update `App.tsx` routes to mount `TaskDashboard` under `/tasks` with `requiredAccess={ROUTE_ACCESS["/tasks"]}`.
   - Maintain backward compatibility for existing bookmarks and deep links by redirecting `/dashboard` to `/tasks` (`<Route path="/dashboard" element={<Navigate to="/tasks" replace />} />`).
   - In `frontend/src/features/user-administration/access/routeAccess.ts`:
     - Update `ROUTE_ACCESS`: add `"/tasks": { module: "tasks", landingRedirect: true }` (preserving `landingRedirect` so a role like PORTEIRO or GUEST directly visiting `/tasks` still redirects to their preferred landing page when accessible). Keep `"/dashboard": { module: "tasks", landingRedirect: true }` so any access check evaluating `/dashboard` succeeds consistently with `/tasks`.
     - Update `NAV_ITEMS`: update the "Tarefas" item path from `"/dashboard"` to `"/tasks"`, with `labelKey: "nav.tasks"`, `iconName: "CheckSquare"`, and `access: ROUTE_ACCESS["/tasks"]`.
     - Update `NAV_GROUPS`: in the `operations` group (`id: "operations"`), replace `"/dashboard"` with `"/tasks"` (`itemPaths: ["/tasks", "/categories", "/projects", "/purchases", "/assets"]`).
   - Update back-to-dashboard links in administrative pages (`AdminUserDashboard.tsx`, `ContactInfoDashboard.tsx`) to link to `/` (or `/tasks` if explicitly returning to operational tasks, but standard is home `/`).
   - In `backend/app/schemas/role.py` and `frontend/src/features/user-administration/pages/RoleDetailPage.tsx`:
     - Support `/tasks` in `LANDING_PATHS`: add `"/tasks"` alongside `"/dashboard"` (keeping `"/dashboard"` in the frozenset for backward-compatibility with previously seeded rows), ensuring no 422 error on role updates and keeping backend tests green.

2. **Create New General Dashboard (`GeneralDashboardPage.tsx`)**:
   - Location: `frontend/src/features/dashboard/components/GeneralDashboardPage.tsx`.
   - Accessible at route `/` for authenticated callers.
   - Guarded by `<ProtectedRoute>`: accessible to any authenticated user (carries no module permission constraint, registering `/` in `AUTHENTICATED_ONLY_PATHS`).
   - Layout & Styling:
     - Header / Welcome banner:
       - Greeting to the current user with full name (`user.full_name`).
       - Active condominium/tenant name (`actingTenant?.name` via `useTenant()`).
       - Active role pill/badges or profile summary.
     - Summary quick-access cards / module shortcuts:
       - Clean, responsive card grid matching APRAS styling (`bg-card`, border, rounded corners, hover effect, icon, localized title and description, link to route).
       - Overview cards for key system modules:
         1. **Tarefas** (`/tasks`, icon `CheckSquare`, gated by module `"tasks"`).
         2. **Portaria & Visitantes** (`/gate` or `/authorizations`, icon `ShieldCheck` / `UserCheck`, gated by `"gate"` or `"authorizations"`).
         3. **Encomendas** (`/packages`, icon `Package`, gated by module `"packages"`).
         4. **Livro de Ocorrências** (`/occurrences`, icon `BookOpen`, gated by module `"occurrences"`).
         5. **Reservas de Espaços** (`/reservations`, icon `CalendarDays`, gated by module `"reservations"`).
         6. **Comunicados** (`/announcements`, icon `Megaphone`, gated by module `"announcements"`).
         7. **Financeiro** (`/finance`, icon `DollarSign`, gated by module `"finance"`).
         8. **Infrações** (`/infractions` or `/my-infractions`, icon `FileWarning`, gated by module `"infractions"`).
       - Cards are rendered conditionally based on whether the module is enabled for the tenant and accessible to the current user (using `useCanShowMenu` / `useCanOpenPath`), so a user only sees cards for features they can access.
   - Clean, modern, responsive APRAS design with Tailwind CSS matching existing features (Finance, Announcements, etc.).

3. **Sidebar Navigation Integration ("Início" / "Home")**:
   - In `Sidebar.tsx`:
     - Render an "Início" / "Home" navigation link at the top of the sidebar navigation list (above the functional groups, or as a standalone top item) pointing to `/` with the `Home` Lucide icon.
     - Active when `location.pathname === "/"`.
     - Supports collapsed desktop mode (icon with tooltip) and expanded mode (icon + localized label).
     - Clicking it in mobile drawer automatically calls `closeMobile`.
   - Localized label: `"nav.home"` ("Início" in `pt.json`, "Home" in `en.json`).

4. **Update `RootRedirect` Fallback Behavior**:
   - In `frontend/src/App.tsx`:
     - If the user has a specific preferred `landing_path` configured on their role (e.g. PORTEIRO -> `/gate`, GUEST -> `/welcome`) AND that landing route is accessible (`canOpen(landing)`), redirect to that `landing_path`.
     - Otherwise, authenticated callers without a specific overriding landing path stay on `/` and render the `GeneralDashboardPage`.
     - Architecture:
       - Route at `/` is wrapped in `<ProtectedRoute>`:
         ```tsx
         <Route
           path="/"
           element={
             <ProtectedRoute>
               <RootRedirect />
             </ProtectedRoute>
           }
         />
         ```
       - Inside `RootRedirect`:
         ```tsx
         const landing = data?.landing_path ?? null;
         if (landing && landing !== "/" && canOpen(landing)) {
           return <Navigate to={landing} replace />;
         }
         return <GeneralDashboardPage />;
         ```
         This ensures:
         - Unauthenticated users are redirected to `/login` by `ProtectedRoute`.
         - Role-pinned users (like PORTEIRO -> `/gate`, GUEST -> `/welcome`) are redirected to their accessible landing.
         - General users land directly on `/` and see the General Dashboard without any redirect hop!

5. **Internationalization (i18n)**:
   - Add localized keys in `frontend/src/i18n/locales/pt.json` and `frontend/src/i18n/locales/en.json` for:
     - `"nav.home"`: "Início" / "Home"
     - `"dashboard.general.*"`: welcome messages, tenant banner labels, quick action titles and card descriptions.

---

### Explicitly Not in Scope

- **No backend database schema migrations**: no new SQLModel models or Alembic migrations are required.
- **No changes to core permissions or authorization model**: `ROUTE_PERMISSIONS`, `PERMISSIONS`, `deps.get_effective_permissions` remain untouched.
- **No live complex backend metrics aggregation API**: the General Dashboard provides layout, tenant context banner, and module overview shortcut cards. Dedicated aggregated metrics widgets (e.g. live count of pending tasks, uncollected packages) can be connected in future feature-specific tasks.

---

## 2. Technical Architecture & Invariants

### 2.1 Route Map & `ROUTE_ACCESS` Changes

In `frontend/src/features/user-administration/access/routeAccess.ts`:

```typescript
export const ROUTE_ACCESS: Record<string, AccessRule> = {
  // Tasks management moved to /tasks
  "/tasks": { module: "tasks", landingRedirect: true },
  // Backward compatibility alias for /dashboard
  "/dashboard": { module: "tasks", landingRedirect: true },
  "/categories": { module: "categories", landingRedirect: true },
  ...
};

export const AUTHENTICATED_ONLY_PATHS: readonly string[] = ["/welcome", "/"];
```

### 2.2 `NAV_ITEMS` and `NAV_GROUPS` Synchronisation

In `frontend/src/features/user-administration/access/routeAccess.ts`:

1. In `NAV_GROUPS`, the `operations` group references `"/tasks"` instead of `"/dashboard"`:
```typescript
{
  id: "operations",
  titleKey: "nav.groups.operations",
  itemPaths: [
    "/tasks",
    "/categories",
    "/projects",
    "/purchases",
    "/assets",
  ],
}
```

2. In `NAV_ITEMS`:
```typescript
{ path: "/tasks", labelKey: "nav.tasks", iconName: "CheckSquare" },
```
The declaration position of the task entry remains in the exact same place in `NAV_ITEMS` (simply updated from `"/dashboard"` to `"/tasks"`), preserving the relative ordering for any fallback resolution.

3. Coverage Invariant:
`routeAccess.test.ts` asserts that `NAV_GROUPS` itemPaths (30 items) match `NAV_ITEMS` paths (30 items) with zero duplicates and zero omissions. Updating `"/dashboard"` -> `"/tasks"` in both keeps this test strictly 100% green.

### 2.3 `LANDING_PATHS` Allowlist

In `backend/app/schemas/role.py`:
```python
LANDING_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/dashboard",
        "/tasks",
        "/gate",
        "/welcome",
        "/announcements",
        "/occurrences",
    }
)
```
And in `frontend/src/features/user-administration/pages/RoleDetailPage.tsx`:
```typescript
const LANDING_PATHS = [
  "/",
  "/tasks",
  "/dashboard",
  "/gate",
  "/welcome",
  "/announcements",
  "/occurrences",
] as const;
```
Keeping `"/dashboard"` in the frozenset preserves compatibility with any existing role configurations or tests, while adding `"/tasks"` and `"/"`.

### 2.4 `RootRedirect` Implementation

In `frontend/src/App.tsx`:
```tsx
export const RootRedirect: React.FC = () => {
  const { data } = useMyPermissions();
  const set = usePermissionSet();
  const canOpen = useCanOpenPath();

  if (set.isLoading) return <Spinner />;

  const landing = data?.landing_path ?? null;

  // If user has a specific landing configured that is accessible and not root, redirect to it
  if (landing && landing !== "/" && canOpen(landing)) {
    return <Navigate to={landing} replace />;
  }

  // Otherwise render General Dashboard directly
  return <GeneralDashboardPage />;
};
```

And in `App.tsx` routes:
```tsx
<Route
  path="/tasks"
  element={
    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/tasks"]}>
      <TaskDashboard />
    </ProtectedRoute>
  }
/>
<Route
  path="/dashboard"
  element={<Navigate to="/tasks" replace />}
/>
<Route
  path="/"
  element={
    <ProtectedRoute>
      <RootRedirect />
    </ProtectedRoute>
  }
/>
```

---

## 3. General Dashboard UI Design (`GeneralDashboardPage.tsx`)

### 3.1 Header / Context Banner
- Greeting: "Olá, {user.full_name}" (localized with time of day or welcome message).
- Condominium/Tenant info: Displays active tenant name (`actingTenant?.name` with a building icon) and role/profile tags.
- Quick summary subtext: "Bem-vindo ao painel central do seu condomínio."

### 3.2 Quick-Access Shortcut Grid
Grid of responsive cards (`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6`):
1. **Tarefas**: View and manage condominium tasks and activities (`/tasks`).
2. **Portaria & Acessos**: Manage guest authorizations and gatehouse check-ins (`/gate` or `/authorizations`).
3. **Encomendas**: Track incoming and picked-up resident packages (`/packages`).
4. **Livro de Ocorrências**: Register and follow up occurrences (`/occurrences`).
5. **Reservas**: Book common areas and amenities (`/reservations`).
6. **Comunicados**: Read internal notices and announcements (`/announcements`).
7. **Financeiro**: Financial statements, balance, and accountability (`/finance`).
8. **Infrações**: Consult rules and infraction processes (`/infractions` or `/my-infractions`).

Each card includes:
- Distinctive accent icon in themed background container (`bg-primary/10 text-primary`, etc.).
- Module Title and brief descriptive caption.
- Clickable link navigating to the module route.
- Hover transition with subtle border highlight and shadow elevation.

---

## 4. Test Strategy

1. **Unit & Integration Tests for `GeneralDashboardPage`**:
   - Verify that the page renders the welcome banner with the user's name and active tenant name.
   - Verify that shortcut cards are displayed for enabled modules.
   - Verify that cards for modules disabled in the active tenant or without permission are not shown.

2. **Route Access & Migration Tests (`routeAccess.test.ts`)**:
   - Verify that `ROUTE_ACCESS["/tasks"]` is defined and matches `{ module: "tasks", landingRedirect: true }`.
   - Verify that `NAV_ITEMS` has 30 items with `/tasks` present and `/dashboard` absent from `NAV_ITEMS`.
   - Verify that `NAV_GROUPS` covers all 30 items in `NAV_ITEMS` with zero duplicates and zero omissions.
   - Verify `/` is in `AUTHENTICATED_ONLY_PATHS`.

3. **Routing & Redirection Tests (`RootRedirect.test.tsx`, `RootRedirect.landing.test.tsx`, `AppRouting.smoke.test.tsx`)**:
   - Verify navigating to `/dashboard` redirects to `/tasks`.
   - Verify that a user with role landing `/gate` (e.g. PORTEIRO) landing on `/` redirects to `/gate`.
   - Verify that a user with role landing `/welcome` (e.g. GUEST) landing on `/` redirects to `/welcome`.
   - Verify that a standard user without special landing landing on `/` renders `GeneralDashboardPage` directly without redirect loops.
   - Verify unauthenticated visit to `/` or `/tasks` redirects to `/login`.

4. **Backend Allowlist Tests (`test_landing_path.py`)**:
   - Verify `LANDING_PATHS` accepts `"/tasks"` and `"/"` along with the existing paths.

---

## 5. Expected Results

- [ ] ER-1: The task management view is migrated to `/tasks` in `App.tsx`, `NAV_ITEMS`, and `NAV_GROUPS` under the Operations group, and accessing `/dashboard` seamlessly redirects to `/tasks`.
- [ ] ER-2: A new General Dashboard component (`GeneralDashboardPage.tsx`) is created and rendered at `/` for authenticated callers, featuring a welcome banner with user/tenant context and responsive shortcut cards for active modules.
- [ ] ER-3: The lateral `Sidebar.tsx` includes an "Início" / "Home" navigation entry pointing to `/` with the `Home` icon, properly supporting expanded, collapsed, and mobile drawer states.
- [ ] ER-4: `RootRedirect` preserves role-specific landing paths (`/gate` for PORTEIRO, `/welcome` for GUEST) when accessible, while rendering the General Dashboard directly at `/` for standard authenticated users.
- [ ] ER-5: `ROUTE_ACCESS` correctly defines rules for `/tasks` and `/dashboard`, and `routeAccess.test.ts` validates 100% coverage across all 30 navigation items in `NAV_GROUPS` without drift or omissions.
- [ ] ER-6: Backend `LANDING_PATHS` in `role.py` and frontend `RoleDetailPage.tsx` support `/tasks` and `/` without validation errors.
- [ ] ER-7: Complete internationalization support for `"nav.home"` and `"dashboard.general.*"` in both `pt.json` and `en.json` with identical key-set parity.
- [ ] ER-8: All frontend and backend unit, integration, and smoke tests pass without regressions.
