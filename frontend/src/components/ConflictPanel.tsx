import React from "react";
import type { Conflict } from "../types";

interface ConflictPanelProps {
  conflicts: Conflict[];
  openQuestions: string[];
}

export function ConflictPanel({ conflicts, openQuestions }: ConflictPanelProps) {
  return (
    <div className="space-y-3">
      {conflicts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide">
            Conflicts Detected
          </h3>
          <div className="mt-2 space-y-2">
            {conflicts.map((c, i) => (
              <div
                key={i}
                className="border border-red-200 dark:border-red-800 rounded-lg p-3 bg-red-50 dark:bg-red-900/20"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 font-medium uppercase">
                    {c.conflict_type}
                  </span>
                  <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                    {c.topic}
                  </span>
                </div>
                <div className="flex gap-4 mt-1">
                  {c.experts.map((expert, j) => (
                    <div key={j} className="text-sm text-zinc-600 dark:text-zinc-400">
                      <span className="font-medium">{expert}:</span>{" "}
                      {c.values[j] || "N/A"}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {openQuestions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wide">
            Open Questions
          </h3>
          <ul className="mt-1 space-y-1">
            {openQuestions.map((q, i) => (
              <li
                key={i}
                className="text-sm text-zinc-600 dark:text-zinc-300 pl-4 border-l-2 border-amber-300 dark:border-amber-600"
              >
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
