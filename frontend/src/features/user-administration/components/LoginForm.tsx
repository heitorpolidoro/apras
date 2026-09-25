import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import apiClient from "../../../api/client";
import { parseApiError } from "../../../api/errors";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { AlertModal } from "../../../components/ui/alert-modal";

interface LoginFormProps {
  /**
   * What happens once `AuthContext.login` has resolved.
   *
   * A prop rather than a hard-coded `navigate`, because the two callers want
   * different things and neither is a special case of the other: `/login`
   * honours `location.state.from`, while `/c/<slug>` runs its own slug
   * resolution and navigates from there (APRAS-74). Optional, because "do
   * nothing and let the page re-render" is a legitimate answer — it is
   * exactly what the branded entry does, since flipping `isAuthenticated`
   * puts that page back into its readiness gate.
   */
  onSuccess?: () => void;
  /**
   * Mirrors the remember-me checkbox out to the page.
   *
   * `LoginPage`'s development-only quick-login sends the same `remember_me`
   * the form is showing, and the checkbox lives here. Reporting the value is
   * what keeps the two in step without lifting the field into a controlled
   * prop that the branded page would then have to own for no reason.
   */
  onRememberMeChange?: (remember: boolean) => void;
  /** Disables submit while an alternative sign-in affordance is in flight. */
  busy?: boolean;
}

/**
 * The credential form: e-mail, password, remember-me, and the one
 * `POST /auth/login` in this application.
 *
 * Extracted from `LoginPage` by APRAS-74 so `/login` and `/c/<slug>` render
 * the *same* component rather than two forms that have to be kept in step.
 * The submit sequence — `POST /auth/login?remember_me=…` with a multipart
 * body, then `AuthContext.login(token, remember)` — exists in this file and
 * nowhere else; `LoginPage`'s three existing test files are the proof the
 * extraction changed no behaviour.
 *
 * The "esqueceu a senha?" link travels with the password field because it is
 * part of that field's label row, and the branded screen needs it for the
 * same reason `/login` does. The signup prompt, the page chrome and the
 * dev-users picker stay on `LoginPage`.
 */
const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  onRememberMeChange,
  busy = false,
}) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { t } = useTranslation();
  const { login } = useAuth();

  const handleRememberMe = (checked: boolean) => {
    setRememberMe(checked);
    onRememberMeChange?.(checked);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

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
      onSuccess?.();
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
      setIsSubmitting(false);
    }
  };

  const disabled = isSubmitting || busy;

  return (
    <>
      <AlertModal
        open={!!error}
        onClose={() => setError(null)}
        variant="destructive"
        title="Erro"
        message={error ?? ""}
      />

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
          <div className="flex justify-between items-center">
            <Label htmlFor="password">{t("login.password")}</Label>
            <Link to="/forgot-password" className="text-xs text-primary-text hover:underline">
              Esqueceu a senha?
            </Link>
          </div>
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
            onChange={(e) => handleRememberMe(e.target.checked)}
            className="rounded border-input"
          />
          <span className="text-sm text-muted-foreground">
            {t("login.rememberMe")}
          </span>
        </label>

        <Button type="submit" disabled={disabled} className="w-full mt-1">
          {isSubmitting ? t("login.submitting") : t("login.submit")}
        </Button>
      </form>
    </>
  );
};

export default LoginForm;
