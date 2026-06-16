import React, { useState, useEffect } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import apiClient from "../../../api/client";
import { parseApiError } from "../../../api/errors";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Alert, AlertDescription } from "../../../components/ui/alert";
import type { User } from "../../../types/auth";

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [devUsers, setDevUsers] = useState<User[]>([]);

  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Fetch dev users if available (endpoint returns 404 in production)
    void apiClient
      .get<User[]>("/auth/dev-users")
      .then((res) => {
        setDevUsers(res.data);
      })
      .catch(() => {
        setDevUsers([]);
      });
  }, []);

  const from = location.state?.from?.pathname || "/dashboard";
  const successMessage = location.state?.message;

  /**
   * Handle quick login for development environment
   */
  const handleDevLogin = async (selectedEmail: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const response = await apiClient.post("/auth/dev-login", null, {
        params: { email: selectedEmail, remember_me: rememberMe },
      });
      await login(response.data.access_token, rememberMe);
      navigate(from, { replace: true });
    } catch {
      setError("Dev login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const response = await apiClient.post(
        `/auth/login?remember_me=${rememberMe}`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );

      await login(response.data.access_token, rememberMe);
      navigate(from, { replace: true });
    } catch (err) {
      const apiError = err as { response?: { data?: { detail?: unknown } } };
      const detail = apiError.response?.data?.detail;
      if (detail === "Inactive user") {
        setError(t("login.pendingApproval"));
      } else {
        setError(parseApiError(err, t, {
          validationError: "login.validationError",
          genericError: "login.genericError",
        }));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary tracking-tight">
            {t("common.appName")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t("common.appSubtitle")}
          </p>
        </div>

        <div className="rounded-xl border bg-card shadow-sm p-6">
          <h2 className="text-lg font-semibold text-foreground mb-5">
            {t("login.heading")}
          </h2>

          {successMessage && (
            <Alert variant="success" className="mb-4">
              <AlertDescription>{successMessage}</AlertDescription>
            </Alert>
          )}

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">{t("login.email")}</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="your@email.com"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">{t("login.password")}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded border-input"
              />
              <span className="text-sm text-muted-foreground">
                {t("login.rememberMe")}
              </span>
            </label>

            <Button type="submit" disabled={isLoading} className="w-full mt-1">
              {isLoading ? t("login.submitting") : t("login.submit")}
            </Button>
          </form>

          {devUsers.length > 0 && (
            <div className="mt-6 pt-6 border-t border-dashed">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">
                Login Rápido (Desenvolvimento)
              </p>
              <div className="flex flex-wrap gap-2">
                {devUsers.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => handleDevLogin(u.email)}
                    disabled={isLoading}
                    className="text-xs px-2.5 py-1.5 rounded-md bg-primary/5 hover:bg-primary/10 text-primary border border-primary/20 transition-colors"
                  >
                    {u.full_name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="text-center text-sm text-muted-foreground mt-5">
            {t("login.signupPrompt")}{" "}
            <Link
              to="/signup"
              className="text-primary font-medium hover:underline"
            >
              {t("login.signupLink")}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
