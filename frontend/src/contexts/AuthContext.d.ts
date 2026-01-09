/**
 * AuthContext - Authentication state management with Google OAuth
 *
 * Provides:
 * - User login/logout
 * - JWT token management
 * - API key storage (encrypted in backend)
 * - Thread migration from localStorage
 */
import React, { ReactNode } from "react";
declare const GOOGLE_CLIENT_ID: any;
export interface User {
    id: string;
    email: string;
    name: string | null;
    picture_url: string | null;
}
export interface JWTPayload {
    user_id: string;
    email: string;
    exp: number;
    iat: number;
}
export interface AuthContextType {
    user: User | null;
    accessToken: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
    login: (googleToken: string) => Promise<void>;
    logout: () => void;
    saveApiKeys: (keys: Record<string, string>) => Promise<void>;
    getApiKeys: () => Promise<Record<string, string>>;
    migrateThreads: (threadIds: string[], metadata?: any) => Promise<void>;
}
export declare const AuthContext: React.Context<AuthContextType | undefined>;
interface AuthProviderProps {
    children: ReactNode;
}
export declare function AuthProvider({ children }: AuthProviderProps): import("react/jsx-runtime").JSX.Element;
export { GOOGLE_CLIENT_ID };
