import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import apiClient from "../../../api/client";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Alert, AlertDescription } from "../../../components/ui/alert";

const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [token, setToken] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const t = searchParams.get("token");
    setToken(t);
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!token) {
      setError("Token de redefinição de senha ausente ou inválido. Solicite um novo link.");
      return;
    }

    if (newPassword.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.post("/auth/reset-password", {
        token,
        new_password: newPassword,
      });
      setSuccess(true);
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate("/login");
      }, 3000);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "Falha ao redefinir a senha. O link pode ter expirado."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const isTokenMissing = !token;

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary tracking-tight">APRAS</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Defina sua nova senha
          </p>
        </div>

        <div className="rounded-xl border bg-card shadow-sm p-6">
          <h2 className="text-lg font-semibold text-foreground mb-5">
            Nova Senha
          </h2>

          {isTokenMissing ? (
            <div className="space-y-4">
              <Alert variant="destructive">
                <AlertDescription>
                  O link de redefinição de senha está incompleto ou inválido.
                  Por favor, solicite um novo link.
                </AlertDescription>
              </Alert>
              <Link to="/forgot-password" className="w-full block">
                <Button className="w-full bg-emerald-600 hover:bg-emerald-700">
                  Solicitar Novo Link
                </Button>
              </Link>
              <Link to="/login" className="w-full block">
                <Button variant="outline" className="w-full">
                  Voltar para o Login
                </Button>
              </Link>
            </div>
          ) : success ? (
            <div className="space-y-4">
              <Alert className="bg-emerald-50 border-emerald-100 text-emerald-800">
                <AlertDescription>
                  Sua senha foi redefinida com sucesso! Redirecionando para a página de login...
                </AlertDescription>
              </Alert>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="newPassword">Nova Senha</Label>
                <Input
                  id="newPassword"
                  type="password"
                  required
                  placeholder="••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="confirmPassword">Confirmar Nova Senha</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  required
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" disabled={isLoading} className="w-full mt-1">
                {isLoading ? "Salvando..." : "Redefinir Senha"}
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
