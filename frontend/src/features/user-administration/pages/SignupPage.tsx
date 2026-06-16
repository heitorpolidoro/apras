import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import apiClient from "../../../api/client";
import { parseApiError } from "../../../api/errors";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Alert, AlertDescription } from "../../../components/ui/alert";

const SignupPage: React.FC = () => {
  const [formData, setFormData] = useState({
    email: "",
    full_name: "",
    password: "",
    confirm_password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (formData.password !== formData.confirm_password) {
      setError(t("signup.passwordMismatch"));
      return;
    }

    if (formData.password.length < 8) {
      setError(t("signup.passwordTooShort"));
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.post("/auth/signup", {
        email: formData.email,
        full_name: formData.full_name,
        password: formData.password,
      });

      navigate("/login", {
        state: { message: t("signup.success") },
      });
    } catch (err) {
      setError(parseApiError(err, t, {
        validationError: "signup.validationError",
        genericError: "signup.genericError",
      }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4 py-8">
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
          <h2 className="text-lg font-semibold text-foreground mb-1">
            {t("signup.heading")}
          </h2>
          <p className="text-xs text-muted-foreground mb-5">
            {t("signup.passwordHint")}
          </p>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="full_name">{t("signup.fullName")}</Label>
              <Input
                id="full_name"
                name="full_name"
                type="text"
                value={formData.full_name}
                onChange={handleChange}
                required
                placeholder={t("signup.fullNamePlaceholder")}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">{t("signup.email")}</Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                placeholder="your@email.com"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">{t("signup.password")}</Label>
              <Input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
                autoComplete="new-password"
                placeholder="••••••••"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="confirm_password">
                {t("signup.confirmPassword")}
              </Label>
              <Input
                id="confirm_password"
                name="confirm_password"
                type="password"
                value={formData.confirm_password}
                onChange={handleChange}
                required
                autoComplete="new-password"
                placeholder="••••••••"
              />
            </div>

            <Button type="submit" disabled={isLoading} className="w-full mt-1">
              {isLoading ? t("signup.submitting") : t("signup.submit")}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-5">
            {t("signup.loginPrompt")}{" "}
            <Link
              to="/login"
              className="text-primary font-medium hover:underline"
            >
              {t("signup.loginLink")}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;
