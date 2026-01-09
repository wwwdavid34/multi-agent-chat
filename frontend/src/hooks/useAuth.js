/**
 * useAuth - Hook to access authentication context
 *
 * This is a convenience hook that provides access to the AuthContext.
 * It ensures the hook is used within an AuthProvider.
 */
import { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";
export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider. " +
            "Wrap your app with <AuthProvider> in main.tsx");
    }
    return context;
}
