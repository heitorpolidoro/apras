import React, { useState, useEffect } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import apiClient from "../../../api/client";
import { AlertModal } from "../../../components/ui/alert-modal";
import LoginForm from "../components/LoginForm";
import type { User } from "../../../types/auth";

/**
 * `/login`: the page chrome around the shared `LoginForm`.
 *
 * APRAS-74 moved the credential fields, the error modal and the
 * `POST /auth/login` + `AuthContext.login` sequence into
 * `components/LoginForm.tsx`, so `/c/<slug>` renders the same form rather
 * than a second copy of it. What stays here is what is genuinely this page's:
 * the app name and subtitle, the deep-link navigation off
 * `location.state.from`, the post-signup success modal, the signup prompt and
 * the development-only quick-login picker.
 */
const LoginPage: React.FC = () => {
  const [rememberMe, setRememberMe] = useState(false);
  const [devError, setDevError] = useState<string | null>(null);
  const [isDevLoading, setIsDevLoading] = useState(false);
  const [devUsers, setDevUsers] = useState<User[]>([]);

  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // The dev-login picker exists only in development builds; the endpoint
    // answers 404 in production, and the browser logs every failed XHR even
    // when the promise is caught, so the request must not be made at all.
    if (!import.meta.env.DEV) return;
    void apiClient
      .get<User[]>("/auth/dev-users")
      .then((res) => {
        setDevUsers(res.data);
      })
      .catch(() => {
        setDevUsers([]);
      });
  }, []);

  const from = location.state?.from?.pathname || "/";
  const successMessage = location.state?.message;

  /**
   * Handle quick login for development environment
   */
  const handleDevLogin = async (selectedEmail: string) => {
    setDevError(null);
    setIsDevLoading(true);
    try {
      const response = await apiClient.post("/auth/dev-login", null, {
        params: { email: selectedEmail, remember_me: rememberMe },
      });
      await login(response.data.access_token, rememberMe);
      navigate(from, { replace: true });
    } catch {
      setDevError("Dev login failed");
    } finally {
      setIsDevLoading(false);
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

          <AlertModal
            open={!!successMessage}
            onClose={() => {}}
            variant="success"
            title="Sucesso"
            message={successMessage ?? ""}
          />

          <AlertModal
            open={!!devError}
            onClose={() => setDevError(null)}
            variant="destructive"
            title="Erro"
            message={devError ?? ""}
          />

          <LoginForm
            onSuccess={() => navigate(from, { replace: true })}
            onRememberMeChange={setRememberMe}
            busy={isDevLoading}
          />

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
                    disabled={isDevLoading}
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
