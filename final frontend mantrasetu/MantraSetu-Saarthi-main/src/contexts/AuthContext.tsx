import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '@/services/auth.service';

interface AuthContextType {
  isAuthenticated: boolean;
  user: any | null;
  login: (token: string, userData?: any) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Restore session on mount
    const checkAuth = async () => {
      const token = authService.getToken();
      if (token) {
        try {
          const userData = await authService.getMe();
          setUser(userData);
          setIsAuthenticated(true);
        } catch (error) {
          authService.logout();
          setIsAuthenticated(false);
          setUser(null);
        }
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  const login = (token: string, userData?: any) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('token', token);
    setIsAuthenticated(true);
    if (userData) {
      setUser(userData);
    }
  };

  const logout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
