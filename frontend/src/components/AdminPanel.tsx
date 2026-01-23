/**
 * AdminPanel - Admin UI for managing system key allowlist
 *
 * Allows admins to:
 * - View all users
 * - Add/remove emails from system key allowlist
 * - Update user roles
 */

import { useState, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "../hooks/useAuth";

// Get API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ??
  `${window.location.protocol}//${window.location.hostname}:8000`;

// Types
interface AllowlistEntry {
  id: number;
  email: string;
  provider: string;
  added_by: string;
  notes: string | null;
  created_at: string;
}

interface UserWithRole {
  id: string;
  email: string;
  name: string | null;
  role: string;
  created_at: string;
  last_login: string;
}

const PROVIDERS = ["openai", "anthropic", "google", "xai"] as const;
type Provider = typeof PROVIDERS[number];

const PROVIDER_LABELS: Record<Provider, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic (Claude)",
  google: "Google (Gemini)",
  xai: "xAI (Grok)",
};

interface AdminPanelProps {
  open: boolean;
  onClose: () => void;
}

type TabType = "allowlist" | "users";

export function AdminPanel({ open, onClose }: AdminPanelProps) {
  const { accessToken, isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>("allowlist");

  // Allowlist state
  const [allowlist, setAllowlist] = useState<AllowlistEntry[]>([]);
  const [allowlistLoading, setAllowlistLoading] = useState(false);
  const [allowlistError, setAllowlistError] = useState<string | null>(null);

  // Add entry form state
  const [newEmail, setNewEmail] = useState("");
  const [newProvider, setNewProvider] = useState<Provider>("openai");
  const [newNotes, setNewNotes] = useState("");
  const [adding, setAdding] = useState(false);

  // Users state
  const [users, setUsers] = useState<UserWithRole[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);

  // Fetch allowlist
  const fetchAllowlist = useCallback(async () => {
    if (!accessToken) return;
    setAllowlistLoading(true);
    setAllowlistError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/allowlist`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to fetch allowlist");
      }

      const data = await response.json();
      setAllowlist(data.entries);
    } catch (err) {
      setAllowlistError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setAllowlistLoading(false);
    }
  }, [accessToken]);

  // Fetch users
  const fetchUsers = useCallback(async () => {
    if (!accessToken) return;
    setUsersLoading(true);
    setUsersError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/users`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to fetch users");
      }

      const data = await response.json();
      setUsers(data.users);
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setUsersLoading(false);
    }
  }, [accessToken]);

  // Load data when panel opens
  useEffect(() => {
    if (open && isAdmin) {
      fetchAllowlist();
      fetchUsers();
    }
  }, [open, isAdmin, fetchAllowlist, fetchUsers]);

  // Add to allowlist
  const handleAddEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken || !newEmail.trim()) return;

    setAdding(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/allowlist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          email: newEmail.trim(),
          provider: newProvider,
          notes: newNotes.trim() || null,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to add entry");
      }

      // Refresh and clear form
      await fetchAllowlist();
      setNewEmail("");
      setNewNotes("");
    } catch (err) {
      setAllowlistError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setAdding(false);
    }
  };

  // Remove from allowlist
  const handleRemoveEntry = async (id: number) => {
    if (!accessToken) return;
    if (!confirm("Remove this entry from the allowlist?")) return;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/allowlist/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to remove entry");
      }

      await fetchAllowlist();
    } catch (err) {
      setAllowlistError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  // Update user role
  const handleUpdateRole = async (userId: string, newRole: string) => {
    if (!accessToken) return;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/admin/users/${userId}/role`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ role: newRole }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to update role");
      }

      await fetchUsers();
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  if (!open) return null;
  if (!isAdmin) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-background p-6 rounded-lg">
          <p className="text-destructive">Admin access required</p>
          <button onClick={onClose} className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded">
            Close
          </button>
        </div>
      </div>
    );
  }

  // Group allowlist by provider
  const allowlistByProvider = PROVIDERS.reduce((acc, provider) => {
    acc[provider] = allowlist.filter((e) => e.provider === provider);
    return acc;
  }, {} as Record<Provider, AllowlistEntry[]>);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-background border rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="text-xl font-semibold">Admin Panel</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-muted rounded-full transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b px-4">
            <div className="flex gap-4">
              <button
                onClick={() => setActiveTab("allowlist")}
                className={`py-3 px-1 border-b-2 transition-colors ${
                  activeTab === "allowlist"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                System Key Allowlist
              </button>
              <button
                onClick={() => setActiveTab("users")}
                className={`py-3 px-1 border-b-2 transition-colors ${
                  activeTab === "users"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                User Management
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === "allowlist" && (
              <div className="space-y-6">
                {/* Add Entry Form */}
                <form onSubmit={handleAddEntry} className="p-4 border rounded-lg bg-muted/30">
                  <h3 className="font-medium mb-3">Add Email to Allowlist</h3>
                  <div className="flex flex-wrap gap-3">
                    <input
                      type="email"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      placeholder="user@example.com"
                      className="flex-1 min-w-[200px] px-3 py-2 border rounded bg-background"
                      required
                    />
                    <select
                      value={newProvider}
                      onChange={(e) => setNewProvider(e.target.value as Provider)}
                      className="px-3 py-2 border rounded bg-background"
                    >
                      {PROVIDERS.map((p) => (
                        <option key={p} value={p}>{PROVIDER_LABELS[p]}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      value={newNotes}
                      onChange={(e) => setNewNotes(e.target.value)}
                      placeholder="Notes (optional)"
                      className="flex-1 min-w-[150px] px-3 py-2 border rounded bg-background"
                    />
                    <button
                      type="submit"
                      disabled={adding || !newEmail.trim()}
                      className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
                    >
                      {adding ? "Adding..." : "Add"}
                    </button>
                  </div>
                </form>

                {allowlistError && (
                  <div className="p-3 bg-destructive/10 border border-destructive/20 rounded text-destructive text-sm">
                    {allowlistError}
                  </div>
                )}

                {allowlistLoading ? (
                  <div className="text-center py-8 text-muted-foreground">Loading...</div>
                ) : (
                  <div className="space-y-4">
                    {PROVIDERS.map((provider) => (
                      <div key={provider} className="border rounded-lg overflow-hidden">
                        <div className="bg-muted/50 px-4 py-2 font-medium flex items-center gap-2">
                          {PROVIDER_LABELS[provider]}
                          <span className="text-xs text-muted-foreground">
                            ({allowlistByProvider[provider].length} users)
                          </span>
                        </div>
                        {allowlistByProvider[provider].length === 0 ? (
                          <div className="px-4 py-3 text-sm text-muted-foreground">
                            No users allowlisted
                          </div>
                        ) : (
                          <div className="divide-y">
                            {allowlistByProvider[provider].map((entry) => (
                              <div key={entry.id} className="px-4 py-2 flex items-center justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium truncate">{entry.email}</div>
                                  <div className="text-xs text-muted-foreground">
                                    Added by {entry.added_by} on {new Date(entry.created_at).toLocaleDateString()}
                                    {entry.notes && ` - ${entry.notes}`}
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleRemoveEntry(entry.id)}
                                  className="p-1 text-destructive hover:bg-destructive/10 rounded"
                                  title="Remove"
                                >
                                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "users" && (
              <div className="space-y-4">
                {usersError && (
                  <div className="p-3 bg-destructive/10 border border-destructive/20 rounded text-destructive text-sm">
                    {usersError}
                  </div>
                )}

                {usersLoading ? (
                  <div className="text-center py-8 text-muted-foreground">Loading...</div>
                ) : (
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-2 text-left text-sm font-medium">Email</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">Name</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">Role</th>
                          <th className="px-4 py-2 text-left text-sm font-medium">Last Login</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {users.map((user) => (
                          <tr key={user.id}>
                            <td className="px-4 py-2 text-sm">{user.email}</td>
                            <td className="px-4 py-2 text-sm text-muted-foreground">{user.name || "-"}</td>
                            <td className="px-4 py-2">
                              <select
                                value={user.role}
                                onChange={(e) => handleUpdateRole(user.id, e.target.value)}
                                className={`px-2 py-1 text-xs rounded border ${
                                  user.role === "admin"
                                    ? "bg-primary/10 border-primary/20 text-primary"
                                    : "bg-muted border-muted-foreground/20"
                                }`}
                              >
                                <option value="user">User</option>
                                <option value="admin">Admin</option>
                              </select>
                            </td>
                            <td className="px-4 py-2 text-sm text-muted-foreground">
                              {new Date(user.last_login).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
