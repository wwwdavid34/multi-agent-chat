/**
 * useAuth - Hook to access authentication context
 *
 * This is a convenience hook that provides access to the AuthContext.
 * It ensures the hook is used within an AuthProvider.
 */
import { AuthContextType } from "../contexts/AuthContext";
export declare function useAuth(): AuthContextType;
