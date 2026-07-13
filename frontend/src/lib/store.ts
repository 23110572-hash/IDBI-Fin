import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  role: string | null;
  username: string | null;
  setAuth: (token: string, role: string, username: string) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      username: null,
      setAuth: (token, role, username) => set({ token, role, username }),
      logout: () => set({ token: null, role: null, username: null }),
    }),
    { name: "idbifin-auth" }
  )
);

interface UiState {
  selectedUrn: string | null;
  selectBorrower: (urn: string | null) => void;
}

export const useUi = create<UiState>((set) => ({
  selectedUrn: null,
  selectBorrower: (urn) => set({ selectedUrn: urn }),
}));
