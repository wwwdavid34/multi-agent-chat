import React from "react";
import type {
  DecisionPhase,
  ExpertTask,
  ExpertOutput,
  Conflict,
  Recommendation,
} from "../types";
import { ExpertCard } from "./ExpertCard";
import { ConflictPanel } from "./ConflictPanel";
import { RecommendationPanel } from "./RecommendationPanel";

interface DecisionViewerProps {
  phase: DecisionPhase;
  options: string[];
  expertTasks: ExpertTask[];
  expertOutputs: Record<string, ExpertOutput>;
  conflicts: Conflict[];
  openQuestions: string[];
  recommendation: Recommendation | null;
  awaitingInput: boolean;
  onHumanFeedback?: (feedback: { action: string; additional_instructions?: string }) => void;
}

const PHASE_STEPS: { key: DecisionPhase; label: string }[] = [
  { key: "planning", label: "Planning" },
  { key: "analysis", label: "Analysis" },
  { key: "conflict", label: "Conflicts" },
  { key: "synthesis", label: "Decision" },
];

function phaseDone(current: DecisionPhase, step: DecisionPhase): boolean {
  const order = PHASE_STEPS.map((s) => s.key);
  return order.indexOf(current) > order.indexOf(step);
}

function phaseActive(current: DecisionPhase, step: DecisionPhase): boolean {
  return current === step || (step === "conflict" && current === "human");
}

export function DecisionViewer({
  phase,
  options,
  expertTasks,
  expertOutputs,
  conflicts,
  openQuestions,
  recommendation,
  awaitingInput,
  onHumanFeedback,
}: DecisionViewerProps) {
  const [feedbackText, setFeedbackText] = React.useState("");

  return (
    <div className="space-y-4">
      {/* Phase stepper */}
      <div className="flex gap-2 border-b border-zinc-200 dark:border-zinc-700 pb-3">
        {PHASE_STEPS.map((step) => (
          <div
            key={step.key}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              phaseActive(phase, step.key)
                ? "bg-blue-600 text-white"
                : phaseDone(phase, step.key)
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500"
            }`}
          >
            {step.label}
          </div>
        ))}
      </div>

      {/* Planning phase */}
      {(phase === "planning" || options.length > 0) && (
        <div className="space-y-2">
          {options.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
                Options Identified
              </h3>
              <div className="flex gap-2 mt-1">
                {options.map((opt) => (
                  <span
                    key={opt}
                    className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-sm font-medium"
                  >
                    {opt}
                  </span>
                ))}
              </div>
            </div>
          )}
          {expertTasks.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mt-3">
                Expert Tasks
              </h3>
              <ul className="mt-1 space-y-1">
                {expertTasks.map((task, i) => (
                  <li key={i} className="text-sm text-zinc-600 dark:text-zinc-300">
                    <span className="font-medium">{task.expert_role}:</span>{" "}
                    {task.deliverable}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Analysis phase -- expert cards */}
      {Object.keys(expertOutputs).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
            Expert Analysis
          </h3>
          <div className="grid gap-3 mt-2">
            {Object.entries(expertOutputs).map(([role, output]) => (
              <ExpertCard key={role} output={output} options={options} />
            ))}
          </div>
        </div>
      )}

      {/* Conflicts phase */}
      {(conflicts.length > 0 || openQuestions.length > 0) && (
        <ConflictPanel
          conflicts={conflicts}
          openQuestions={openQuestions}
        />
      )}

      {/* Human gate -- awaiting input */}
      {awaitingInput && onHumanFeedback && (
        <div className="border border-amber-300 dark:border-amber-600 rounded-lg p-4 bg-amber-50 dark:bg-amber-900/20">
          <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200">
            Your Input Needed
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
            Review the expert analyses and conflicts above. You can approve and
            proceed, or request deeper analysis.
          </p>
          <textarea
            className="w-full mt-2 p-2 border rounded text-sm bg-white dark:bg-zinc-800 dark:border-zinc-600"
            rows={3}
            placeholder="Additional instructions (optional)..."
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
          />
          <div className="flex gap-2 mt-2">
            <button
              className="px-4 py-1.5 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700"
              onClick={() =>
                onHumanFeedback({
                  action: "proceed",
                  additional_instructions: feedbackText,
                })
              }
            >
              Proceed to Decision
            </button>
            <button
              className="px-4 py-1.5 bg-amber-600 text-white rounded text-sm font-medium hover:bg-amber-700"
              onClick={() =>
                onHumanFeedback({
                  action: "re_analyze",
                  additional_instructions: feedbackText,
                })
              }
            >
              Dig Deeper
            </button>
          </div>
        </div>
      )}

      {/* Recommendation phase */}
      {recommendation && (
        <RecommendationPanel
          recommendation={recommendation}
          options={options}
        />
      )}
    </div>
  );
}
