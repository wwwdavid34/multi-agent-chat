import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { ThemeProvider } from "./components/theme-provider";
import { AuthProvider } from "./contexts/AuthContext";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <ThemeProvider defaultTheme="system" storageKey="multi-agent-chat-theme">
        <App />
      </ThemeProvider>
    </AuthProvider>
  </React.StrictMode>
);
