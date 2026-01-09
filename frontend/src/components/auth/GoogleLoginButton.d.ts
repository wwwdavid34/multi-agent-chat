/**
 * GoogleLoginButton - Google OAuth login button using Google Identity Services
 *
 * This component:
 * 1. Loads the Google Identity Services SDK from CDN
 * 2. Renders the official Google Sign-In button
 * 3. Handles the OAuth callback
 * 4. Passes the ID token to AuthContext for verification
 */
declare global {
    interface Window {
        google?: {
            accounts: {
                id: {
                    initialize: (config: GoogleIdConfiguration) => void;
                    renderButton: (parent: HTMLElement, options: GoogleButtonConfiguration) => void;
                    prompt: () => void;
                };
            };
        };
    }
}
interface GoogleIdConfiguration {
    client_id: string;
    callback: (response: GoogleCallbackResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
}
interface GoogleCallbackResponse {
    credential: string;
    select_by?: string;
}
interface GoogleButtonConfiguration {
    type?: "standard" | "icon";
    theme?: "outline" | "filled_blue" | "filled_black";
    size?: "large" | "medium" | "small";
    text?: "signin_with" | "signup_with" | "continue_with" | "signin";
    shape?: "rectangular" | "pill" | "circle" | "square";
    logo_alignment?: "left" | "center";
    width?: number;
    locale?: string;
}
export declare function GoogleLoginButton(): import("react/jsx-runtime").JSX.Element;
export {};
