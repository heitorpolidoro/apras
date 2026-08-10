import axios from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import i18n from "../i18n";
import { getSimulationState } from "../features/user-administration/context/simulationState";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

const BYPASS_TOKEN = import.meta.env.VITE_BYPASS_TOKEN;

const MUTATING_METHODS = new Set(["post", "put", "patch", "delete"]);

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const method = config.method?.toLowerCase();
    if (
      method &&
      MUTATING_METHODS.has(method) &&
      getSimulationState().isSimulating
    ) {
      // Admin role simulation is a read-only "view-as" mode: there is no
      // real user identity behind the simulated role, so every mutating
      // request is rejected before it leaves the browser. The shape below
      // matches what parseApiError (api/errors.ts) already expects, so it
      // surfaces through existing error-display UI with no new code.
      return Promise.reject({
        response: { data: { detail: i18n.t("simulation.mutationBlocked") } },
      });
    }

    const token =
      sessionStorage.getItem("accessToken") ||
      localStorage.getItem("accessToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (BYPASS_TOKEN) {
      config.headers["x-vercel-protection-bypass"] = BYPASS_TOKEN;
    }
    return config;
  },
  (error: unknown) => {
    return Promise.reject(error);
  },
);

export default apiClient;
