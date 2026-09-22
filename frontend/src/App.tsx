import type React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import TaskDashboard from "./features/task-management/components/TaskDashboard";
import GeneralDashboardPage from "./features/dashboard/components/GeneralDashboardPage";
import CategoriesPage from "./features/task-management/components/CategoriesPage";
import { LotsPage } from "./features/lot-management/components/LotsPage";
import LoginPage from "./features/user-administration/pages/LoginPage";
import SignupPage from "./features/user-administration/pages/SignupPage";
import ForgotPasswordPage from "./features/user-administration/pages/ForgotPasswordPage";
import ResetPasswordPage from "./features/user-administration/pages/ResetPasswordPage";
import AcceptInvitationPage from "./features/user-administration/pages/AcceptInvitationPage";
import BrandedEntryPage from "./features/user-administration/pages/BrandedEntryPage";
import AdminUserDashboard from "./features/user-administration/pages/AdminUserDashboard";
import ContactInfoDashboard from "./features/user-administration/pages/ContactInfoDashboard";
import GuestWelcomePage from "./features/user-administration/pages/GuestWelcomePage";
import ProtectedRoute from "./features/user-administration/components/ProtectedRoute";
import { AuthProvider, useAuth } from "./features/user-administration/context/AuthContext";
import { SimulationProvider } from "./features/user-administration/context/SimulationContext";
import { TenantProvider } from "./features/user-administration/context/TenantContext";
import { SidebarProvider } from "./features/user-administration/context/SidebarContext";
import { useSidebar } from "./features/user-administration/context/useSidebar";
import { cn } from "./lib/utils";
import Navbar from "./features/user-administration/components/Navbar";
import SimulationBanner from "./features/user-administration/components/SimulationBanner";
import { VisitorAuthPage } from "./features/visitor-management/components/VisitorAuthPage";
import { GatekeeperDashboard } from "./features/visitor-management/components/GatekeeperDashboard";
import { OccurrenceBookPage } from "./features/occurrence-management/components/OccurrenceBookPage";
import { PackageStatusPage } from "./features/package-management/components/PackageStatusPage";
import { FeedbackChannelPage } from "./features/feedback-management/components/FeedbackChannelPage";
import { DocumentCenterPage } from "./features/document-management/components/DocumentCenterPage";
import { ConstructionTrackerPage } from "./features/project-management/components/ConstructionTrackerPage";
import { AnnouncementFeedPage } from "./features/announcement-feed/components/AnnouncementFeedPage";
import { FinanceDashboardPage } from "./features/finance/components/FinanceDashboardPage";
import PhotoApprovalQueuePage from "./features/media-management/components/PhotoApprovalQueuePage";
import { AccessControlPage } from "./features/access-control/components/AccessControlPage";
import { GateMonitorPage } from "./features/access-control/components/GateMonitorPage";
import ReservableSpacesPage from "./features/space-reservation-management/components/ReservableSpacesPage";
import SpaceBookingPage from "./features/space-reservation-management/components/SpaceBookingPage";
import AssemblyVotingPage from "./features/assembly-voting/components/AssemblyVotingPage";
import AssetsInventoryPage from "./features/asset-management/components/AssetsInventoryPage";
import PurchaseRequestsPage from "./features/purchase-management/components/PurchaseRequestsPage";
import RolesAdminPage from "./features/user-administration/pages/RolesAdminPage";
import RoleDetailPage from "./features/user-administration/pages/RoleDetailPage";
import TenantModulesPage from "./features/user-administration/pages/TenantModulesPage";
import SubscriptionPage from "./features/user-administration/pages/SubscriptionPage";
import TenantProfilePage from "./features/user-administration/pages/TenantProfilePage";
import PlansAdminPage from "./features/user-administration/pages/PlansAdminPage";
import TenantSubscriptionsPage from "./features/user-administration/pages/TenantSubscriptionsPage";
import TenantsAdminPage from "./features/user-administration/pages/TenantsAdminPage";
import InfractionsPage from "./features/infraction-management/pages/InfractionsPage";
import InfractionRulesPage from "./features/infraction-management/pages/InfractionRulesPage";
import MyInfractionsPage from "./features/infraction-management/pages/MyInfractionsPage";
import { ROUTE_ACCESS } from "./features/user-administration/access/routeAccess";
import { usePermissionSet } from "./features/user-administration/access/useCanAccess";
import { Spinner } from "./components/ui/spinner";
import TenantBrandTheme from "./components/TenantBrandTheme";
import "./App.css";

/**
 * Where "/" lands the caller: the general dashboard, for everybody.
 *
 * APRAS-57 removed the per-role landing preference — first an enum switch,
 * then a column on the role row — so this component no longer chooses a
 * destination and issues no navigation at all. It only holds the render
 * while the permission set is still settling, exactly as `ProtectedRoute`
 * does: navigating away here would unmount the component before the
 * dashboard's own gating could run.
 */
export const RootRedirect: React.FC = () => {
  const set = usePermissionSet();

  if (set.isLoading) return <Spinner />;

  return <GeneralDashboardPage />;
};

const AppLayoutContent: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
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

function App() {
  return (
    <AuthProvider>
      {/* Inside AuthProvider (it reads `user`/`isAuthenticated`) and outside
          SimulationProvider/BrowserRouter (the acting tenant is not a routing
          or simulation concern). It uses useQueryClient, which is satisfied
          because App is always rendered inside a QueryClientProvider. */}
      <TenantProvider>
        {/* Renders nothing; injects the acting condominium's colours into
            `document.head` (APRAS-68). Inside TenantProvider so a tenant
            switch re-themes, and outside BrowserRouter because a theme is
            not a routing concern — it applies to every screen at once. */}
        <TenantBrandTheme />
        <SimulationProvider>
          <SidebarProvider>
            <BrowserRouter>
              <div className="App min-h-screen bg-background">
                <Navbar />
                <AppLayoutContent>
                  <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route
                  path="/forgot-password"
                  element={<ForgotPasswordPage />}
                />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                {/* APRAS-72 D5: the URL APRAS-71 mails, outside
                    ProtectedRoute like the four public routes above. It gets
                    no ROUTE_ACCESS, NAV_ITEMS or NAV_GROUPS entry for the
                    same reason they do not. */}
                <Route path="/invite" element={<AcceptInvitationPage />} />
                {/* APRAS-74 D2: the condominium's own front door. Public, so
                    no ProtectedRoute and no requiredAccess — an anonymous
                    visitor is exactly who it is for. It gets no ROUTE_ACCESS,
                    NAV_ITEMS or NAV_GROUPS entry for the same reason the five
                    public routes above do not. The `/c/` prefix is
                    deliberate: a bare `/<slug>` would collide with every
                    route in this table. */}
                <Route path="/c/:slug" element={<BrandedEntryPage />} />

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
                  path="/categories"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/categories"]}>
                      <CategoriesPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/welcome"
                  element={
                    <ProtectedRoute>
                      <GuestWelcomePage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/lots"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/lots"]}>
                      <LotsPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/authorizations"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/authorizations"]}>
                      <VisitorAuthPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/gate"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/gate"]}>
                      <GatekeeperDashboard />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/occurrences"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/occurrences"]}>
                      <OccurrenceBookPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/feedback"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/feedback"]}>
                      <FeedbackChannelPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/documents"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/documents"]}>
                      <DocumentCenterPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/projects"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/projects"]}>
                      <ConstructionTrackerPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/announcements"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/announcements"]}>
                      <AnnouncementFeedPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/finance"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/finance"]}>
                      <FinanceDashboardPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/users"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/users"]}>
                      <AdminUserDashboard />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/users/contact-info"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/users/contact-info"]}>
                      <ContactInfoDashboard />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/photo-approvals"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/photo-approvals"]}>
                      <PhotoApprovalQueuePage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/access-control"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/access-control"]}>
                      <AccessControlPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/gate-monitor"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/gate-monitor"]}>
                      <GateMonitorPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/spaces"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/spaces"]}>
                      <ReservableSpacesPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/reservations"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/reservations"]}>
                      <SpaceBookingPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/packages"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/packages"]}>
                      <PackageStatusPage />
                    </ProtectedRoute>
                  }
                />

                {/* APRAS-44. Three surfaces, three different rules: the
                    management list, the catalogue + ladder editor, and the
                    resident's own view. None of them is a `{ module }` rule --
                    see the reasoning in `routeAccess.ts`. */}
                <Route
                  path="/infractions"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/infractions"]}>
                      <InfractionsPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/infraction-rules"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/infraction-rules"]}
                    >
                      <InfractionRulesPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/my-infractions"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/my-infractions"]}
                    >
                      <MyInfractionsPage />
                    </ProtectedRoute>
                  }
                />

                {/* Voting is closed to PORTEIRO and GUEST: they never vote,
                    in either modality (APRAS-33). */}
                <Route
                  path="/voting"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/voting"]}>
                      <AssemblyVotingPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/assets"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/assets"]}>
                      <AssetsInventoryPage />
                    </ProtectedRoute>
                  }
                />

                {/* Purchase quotations are an internal board/manager workflow:
                    supplier prices under negotiation are not published to
                    residents (APRAS-37). */}
                <Route
                  path="/purchases"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/purchases"]}>
                      <PurchaseRequestsPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/roles"
                  element={
                    <ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/roles"]}>
                      <RolesAdminPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/modules"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/admin/modules"]}
                    >
                      <TenantModulesPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/tenant-profile"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/admin/tenant-profile"]}
                    >
                      <TenantProfilePage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/subscription"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/subscription"]}
                    >
                      <SubscriptionPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/tenants"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/admin/tenants"]}
                    >
                      <TenantsAdminPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/plans"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/admin/plans"]}
                    >
                      <PlansAdminPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/subscriptions"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/admin/subscriptions"]}
                    >
                      <TenantSubscriptionsPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/admin/roles/:roleId"
                  element={
                    <ProtectedRoute
                      requiredAccess={ROUTE_ACCESS["/admin/roles/:roleId"]}
                    >
                      <RoleDetailPage />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <RootRedirect />
                    </ProtectedRoute>
                  }
                />
              </Routes>
            </AppLayoutContent>
          </div>
        </BrowserRouter>
      </SidebarProvider>
    </SimulationProvider>
  </TenantProvider>
</AuthProvider>
  );
}

export default App;

