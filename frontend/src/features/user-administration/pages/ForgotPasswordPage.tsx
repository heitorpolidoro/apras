import React, { useState } from "react";
import { Link } from "react-router-dom";
import apiClient from "../../../api/client";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { AlertModal } from "../../../components/ui/alert-modal";

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setIsLoading(true);

    try {
      await apiClient.post("/auth/forgot-password", { email: email.trim() });
      setSuccess(true);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "Ocorreu um erro ao processar sua solicitação. Tente novamente."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary tracking-tight">APRAS</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Recuperação de Acesso
          </p>
        </div>

        <div className="rounded-xl border bg-card shadow-sm p-6">
          <h2 className="text-lg font-semibold text-foreground mb-5">
            Recuperar Senha
          </h2>

          <AlertModal
            open={success}
            onClose={() => setSuccess(false)}
            variant="success"
            title="E-mail enviado"
            message="Se o e-mail estiver cadastrado, um link de redefinição foi enviado. Verifique sua caixa de entrada e siga as instruções."
          />

          <AlertModal
            open={!!error}
            onClose={() => setError(null)}
            variant="destructive"
            title="Erro"
            message={error ?? ""}
          />

          {!success && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <p className="text-sm text-muted-foreground">
                Digite seu e-mail e enviaremos um link para você redefinir sua senha.
              </p>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="seu@email.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <Button type="submit" disabled={isLoading} className="w-full mt-1">
                {isLoading ? "Enviando..." : "Enviar link de recuperação"}
              </Button>
            </form>
          )}

          <p className="text-center text-sm text-muted-foreground mt-5">
            Lembrou da senha?{" "}
            <Link to="/login" className="text-primary font-medium hover:underline">
              Voltar ao Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
