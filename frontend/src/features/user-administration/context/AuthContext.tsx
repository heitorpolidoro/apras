import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import apiClient from "../../../api/client";
import { type User } from "../../../types/auth";
import { triggerSimulationReset } from "./simulationState";
import {
  clearActingTenantId,
  getActingTenantId,
  resolveActingTenantId,
  setActingTenantId,
} from "./tenantState";
export { UserRole } from "../../../types/auth";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, remember: boolean) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const response = await apiClient.get<User>("/auth/me");
      // BEFORE setUser, deliberately: this closes the window in which a
      // tenant-scoped query could fire without an X-Tenant-Id header. Writing
      // the mirror first makes the invariant `user !== null implies acting
      // tenant decided` hold, and — because TenantContext reads the mirror
      // through useSyncExternalStore rather than copying it into state — there
      // is no commit in which `user` is set, `isLoading` is false and the
      // acting tenant is still the pre-boot value (APRAS-38 §4.4, §4.5).
      setActingTenantId(
        resolveActingTenantId(
          response.data.tenants ?? [],
          response.data.role,
          getActingTenantId(),
        ),
      );
      setUser(response.data);
    } catch {
      localStorage.removeItem("accessToken");
      sessionStorage.removeItem("accessToken");
      clearActingTenantId();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const token =
      sessionStorage.getItem("accessToken") ||
      localStorage.getItem("accessToken");
    if (token) {
      void fetchUser();
    } else {
      setIsLoading(false);
    }
  }, [fetchUser]);

  const login = useCallback(
    async (token: string, remember: boolean) => {
      localStorage.removeItem("accessToken");
      sessionStorage.removeItem("accessToken");
      if (remember) {
        localStorage.setItem("accessToken", token);
      } else {
        sessionStorage.setItem("accessToken", token);
      }
      setIsLoading(true);
      await fetchUser();
    },
    [fetchUser],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("accessToken");
    sessionStorage.removeItem("accessToken");
    clearActingTenantId();
    setUser(null);
    triggerSimulationReset();
  }, []);

  const value = React.useMemo(
    () => ({ user, isAuthenticated: Boolean(user), isLoading, login, logout }),
    [user, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
