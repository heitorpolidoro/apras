import type React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import TaskDashboard from "./features/task-management/components/TaskDashboard";
import CategoriesPage from "./features/task-management/components/CategoriesPage";
import { LotsPage } from "./features/lot-management/components/LotsPage";
import LoginPage from "./features/user-administration/pages/LoginPage";
import SignupPage from "./features/user-administration/pages/SignupPage";
import ForgotPasswordPage from "./features/user-administration/pages/ForgotPasswordPage";
import ResetPasswordPage from "./features/user-administration/pages/ResetPasswordPage";
import AdminUserDashboard from "./features/user-administration/pages/AdminUserDashboard";
import ContactInfoDashboard from "./features/user-administration/pages/ContactInfoDashboard";
import GuestWelcomePage from "./features/user-administration/pages/GuestWelcomePage";
import ProtectedRoute from "./features/user-administration/components/ProtectedRoute";
import { AuthProvider, useAuth } from "./features/user-administration/context/AuthContext";
import { SimulationProvider } from "./features/user-administration/context/SimulationContext";
import Navbar from "./features/user-administration/components/Navbar";
import SimulationBanner from "./features/user-administration/components/SimulationBanner";
import { VisitorAuthPage } from "./features/visitor-management/components/VisitorAuthPage";
import { GatekeeperDashboard } from "./features/visitor-management/components/GatekeeperDashboard";
import { OccurrenceBookPage } from "./features/occurrence-management/components/OccurrenceBookPage";
import { DocumentCenterPage } from "./features/document-management/components/DocumentCenterPage";
import { ConstructionTrackerPage } from "./features/project-management/components/ConstructionTrackerPage";
import { AnnouncementFeedPage } from "./features/announcement-feed/components/AnnouncementFeedPage";
import { FinanceDashboardPage } from "./features/finance/components/FinanceDashboardPage";
import PhotoApprovalQueuePage from "./features/media-management/components/PhotoApprovalQueuePage";
import { AccessControlPage } from "./features/access-control/components/AccessControlPage";
import { GateMonitorPage } from "./features/access-control/components/GateMonitorPage";
import { UserRole } from "./types/auth";
import "./App.css";

/**
 * Root-redirect target. Uses the user's real role (never the simulated
 * role from useEffectiveIdentity/SimulationContext): an active GUEST goes
 * to /welcome, everyone else (including the brief isLoading window where
 * `user` is still undefined) goes to /dashboard as before.
 */
export const RootRedirect: React.FC = () => {
  const { user } = useAuth();
  return (
    <Navigate to={user?.role === UserRole.GUEST ? "/welcome" : "/dashboard"} replace />
  );
};

function App() {
  return (
    <AuthProvider>
      <SimulationProvider>
        <BrowserRouter>
          <div className="App">
            <Navbar />
            <SimulationBanner />
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route
                path="/forgot-password"
                element={<ForgotPasswordPage />}
              />
              <Route path="/reset-password" element={<ResetPasswordPage />} />

              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute requiredMenu="tasks">
                    <TaskDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/categories"
                element={
                  <ProtectedRoute requiredMenu="categories">
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
                  <ProtectedRoute>
                    <LotsPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/authorizations"
                element={
                  <ProtectedRoute>
                    <VisitorAuthPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/gate"
                element={
                  <ProtectedRoute>
                    <GatekeeperDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/occurrences"
                element={
                  <ProtectedRoute>
                    <OccurrenceBookPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/documents"
                element={
                  <ProtectedRoute>
                    <DocumentCenterPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/projects"
                element={
                  <ProtectedRoute>
                    <ConstructionTrackerPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/announcements"
                element={
                  <ProtectedRoute>
                    <AnnouncementFeedPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/finance"
                element={
                  <ProtectedRoute
                    requiredRoles={[
                      UserRole.ADMINISTRATOR,
                      UserRole.DIRECTOR,
                      UserRole.MANAGER,
                      UserRole.RESIDENT,
                    ]}
                  >
                    <FinanceDashboardPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute requiredRole={UserRole.ADMINISTRATOR}>
                    <AdminUserDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/users/contact-info"
                element={
                  <ProtectedRoute
                    requiredRoles={[UserRole.ADMINISTRATOR, UserRole.MANAGER]}
                  >
                    <ContactInfoDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin/photo-approvals"
                element={
                  <ProtectedRoute requiredRole={UserRole.DIRECTOR}>
                    <PhotoApprovalQueuePage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin/access-control"
                element={
                  <ProtectedRoute
                    requiredRoles={[UserRole.ADMINISTRATOR, UserRole.DIRECTOR]}
                  >
                    <AccessControlPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/gate-monitor"
                element={
                  <ProtectedRoute
                    requiredRoles={[
                      UserRole.ADMINISTRATOR,
                      UserRole.DIRECTOR,
                      UserRole.MANAGER,
                    ]}
                  >
                    <GateMonitorPage />
                  </ProtectedRoute>
                }
              />

              <Route path="/" element={<RootRedirect />} />
            </Routes>
          </div>
        </BrowserRouter>
      </SimulationProvider>
    </AuthProvider>
  );
}

export default App;
