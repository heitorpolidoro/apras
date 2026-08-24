import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import TaskDashboard from "./features/task-management/components/TaskDashboard";
import CategoriesPage from "./features/task-management/components/CategoriesPage";
import { LotsPage } from "./features/lot-management/components/LotsPage";
import LoginPage from "./features/user-administration/pages/LoginPage";
import SignupPage from "./features/user-administration/pages/SignupPage";
import ForgotPasswordPage from "./features/user-administration/pages/ForgotPasswordPage";
import ResetPasswordPage from "./features/user-administration/pages/ResetPasswordPage";
import AdminUserDashboard from "./features/user-administration/pages/AdminUserDashboard";
import ProtectedRoute from "./features/user-administration/components/ProtectedRoute";
import { AuthProvider } from "./features/user-administration/context/AuthContext";
import { SimulationProvider } from "./features/user-administration/context/SimulationContext";
import Navbar from "./features/user-administration/components/Navbar";
import SimulationBanner from "./features/user-administration/components/SimulationBanner";
import { UserRole } from "./types/auth";
import "./App.css";

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
                  <ProtectedRoute>
                    <TaskDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/categories"
                element={
                  <ProtectedRoute>
                    <CategoriesPage />
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
                path="/admin/users"
                element={
                  <ProtectedRoute requiredRole={UserRole.ADMINISTRATOR}>
                    <AdminUserDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/"
                element={<Navigate to="/dashboard" replace />}
              />
            </Routes>
          </div>
        </BrowserRouter>
      </SimulationProvider>
    </AuthProvider>
  );
}

export default App;
