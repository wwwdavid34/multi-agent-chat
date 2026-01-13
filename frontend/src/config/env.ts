/**
 * Environment configuration for the Multi-Agent Panel frontend
 *
 * This module provides environment-specific configuration with smart defaults.
 * Priority order:
 * 1. Explicit VITE_API_BASE_URL environment variable
 * 2. Dynamic URL based on current window location
 */

interface Config {
  apiBaseUrl: string;
  environment: string;
  enableDebugLogs: boolean;
  sentryDsn?: string;
}

function getConfig(): Config {
  const env = import.meta.env.VITE_ENVIRONMENT || import.meta.env.MODE || 'development';

  // Allow explicit override via environment variable
  if (import.meta.env.VITE_API_BASE_URL) {
    return {
      apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
      environment: env,
      enableDebugLogs: env !== 'production',
      sentryDsn: import.meta.env.VITE_SENTRY_DSN,
    };
  }

  // Smart defaults based on current location
  // This allows the frontend to work in any deployment without hardcoding URLs
  const { protocol, hostname } = window.location;

  return {
    apiBaseUrl: `${protocol}//${hostname}:8000`,
    environment: env,
    enableDebugLogs: env !== 'production',
    sentryDsn: import.meta.env.VITE_SENTRY_DSN,
  };
}

export const config = getConfig();

// Helper for conditional logging
export function debugLog(...args: any[]) {
  if (config.enableDebugLogs) {
    console.log('[DEBUG]', ...args);
  }
}
