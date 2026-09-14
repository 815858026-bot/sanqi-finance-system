import { create } from 'zustand';

interface AuthState {
  token: string | null;
  user: any;
  login: (token: string, user: any) => void;
  logout: () => void;
  setUser: (user: any) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || '{}'),
  login: (token: string, user: any) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ token: null, user: {} });
  },
  setUser: (user: any) => {
    localStorage.setItem('user', JSON.stringify(user));
    set({ user });
  },
}));
