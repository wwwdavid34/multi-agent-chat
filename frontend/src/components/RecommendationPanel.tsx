import React from "react";
import type { Recommendation } from "../types";

interface RecommendationPanelProps {
  recommendation: Recommendation;
  options: string[];
}

export function RecommendationPanel({
  recommendation,
  options,
}: RecommendationPanelProps) {
  const rec = recommendation;
  return (
    <div className="border-2 border-green-300 dark:border-green-700 rounded-lg p-4 bg-green-50 dark:bg-green-900/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-green-800 dark:text-green-200">
          Recommendation: {rec.recommended_option}
        </h3>
        <span className="text-sm px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 font-medium">
          Confidence: {(rec.confidence * 100).toFixed(0)}%
        </span>
      </div>

      {/* Reasoning */}
      <div className="mb-3">
        <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
          Why
        </h4>
        <ul className="mt-1 space-y-1">
          {rec.reasoning.map((r, i) => (
            <li key={i} className="text-sm text-zinc-700 dark:text-zinc-300">
              &#8226; {r}
            </li>
          ))}
        </ul>
      </div>

      {/* Tradeoff table */}
      <div className="mb-3">
        <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
          Tradeoffs
        </h4>
        <div className="mt-2 grid gap-2">
          {options.map((opt) => {
            const t = rec.tradeoffs[opt];
            if (!t) return null;
            const isRecommended = opt === rec.recommended_option;
            return (
              <div
                key={opt}
                className={`rounded-lg p-3 ${
                  isRecommended
                    ? "bg-green-100 dark:bg-green-900/40 border border-green-300 dark:border-green-700"
                    : "bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700"
                }`}
              >
                <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  {opt} {isRecommended && "\u2605"}
                </span>
                <div className="mt-1 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="font-medium text-green-700 dark:text-green-400">
                      Pros:
                    </span>
                    <ul>
                      {t.pros?.map((p: string, i: number) => (
                        <li key={i} className="text-zinc-600 dark:text-zinc-400">
                          + {p}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span className="font-medium text-red-700 dark:text-red-400">
                      Cons:
                    </span>
                    <ul>
                      {t.cons?.map((c: string, i: number) => (
                        <li key={i} className="text-zinc-600 dark:text-zinc-400">
                          - {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Risks */}
      {rec.risks.length > 0 && (
        <div className="mb-3">
          <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
            Remaining Risks
          </h4>
          <ul className="mt-1 space-y-0.5">
            {rec.risks.map((r, i) => (
              <li key={i} className="text-sm text-red-600 dark:text-red-400">
                &#x26A0; {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* What would change my mind */}
      {rec.what_would_change_mind.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
            What Would Change This Recommendation
          </h4>
          <ul className="mt-1 space-y-0.5">
            {rec.what_would_change_mind.map((w, i) => (
              <li
                key={i}
                className="text-sm text-zinc-600 dark:text-zinc-300 italic"
              >
                &rarr; {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
