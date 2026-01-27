import React from "react";
import type { ExpertOutput } from "../types";

interface ExpertCardProps {
  output: ExpertOutput;
  options: string[];
}

export function ExpertCard({ output, options }: ExpertCardProps) {
  return (
    <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-zinc-800 dark:text-zinc-200">
          {output.expert_role} Expert
        </h4>
        <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
          Confidence: {(output.confidence * 100).toFixed(0)}%
        </span>
      </div>

      {/* Option ratings */}
      <div className="grid gap-2">
        {options.map((opt) => {
          const analysis = output.option_analyses?.[opt];
          if (!analysis) return null;
          return (
            <div
              key={opt}
              className="bg-zinc-50 dark:bg-zinc-800/50 rounded p-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  {opt}
                </span>
                <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
                  {analysis.score}/10
                </span>
              </div>
              {analysis.claims.length > 0 && (
                <ul className="mt-1 text-xs text-zinc-600 dark:text-zinc-400 space-y-0.5">
                  {analysis.claims.map((claim, i) => (
                    <li key={i}>&#8226; {claim}</li>
                  ))}
                </ul>
              )}
              {analysis.risks.length > 0 && (
                <div className="mt-1 text-xs text-red-600 dark:text-red-400">
                  Risks: {analysis.risks.join(", ")}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Assumptions */}
      {output.assumptions.length > 0 && (
        <div className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="font-medium">Assumptions:</span>{" "}
          {output.assumptions.join("; ")}
        </div>
      )}

      {/* Sources */}
      {output.sources.length > 0 && (
        <div className="mt-1 text-xs text-zinc-400">
          Sources: {output.sources.join(", ")}
        </div>
      )}
    </div>
  );
}
