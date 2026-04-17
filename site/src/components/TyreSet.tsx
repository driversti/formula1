import { TyreDot } from "./TyreDot";
import { UsageBar } from "./UsageBar";

type SessionKey = "FP1" | "FP2" | "FP3" | "Q" | "R";

type Set = {
  set_id: string;
  compound: "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";
  laps: number;
  new_at_first_use: boolean;
  first_seen_session: SessionKey;
  last_seen_session: SessionKey;
};

function historyLabel(set: Set): string {
  if (set.first_seen_session === "R" && set.laps === 0) return "Saved for race";
  if (set.first_seen_session === set.last_seen_session) return set.first_seen_session;
  return `${set.first_seen_session} → ${set.last_seen_session}`;
}

// Static map so Tailwind JIT can detect all class names at build time.
// Note: INTERMEDIATE maps to `compound-inter` (matching the CSS variable name).
const TEXT_COLOR_CLASS: Record<Set["compound"], string> = {
  SOFT: "text-compound-soft",
  MEDIUM: "text-compound-medium",
  HARD: "text-compound-hard",
  INTERMEDIATE: "text-compound-inter",
  WET: "text-compound-wet",
};

function lapsLabel(set: Set): string {
  return set.laps === 0 ? "NEW" : `${set.laps} laps`;
}

export function TyreSet({ set }: { set: Set }) {
  const savedForRace = set.first_seen_session === "R" && set.laps === 0;
  return (
    <div
      className={[
        "rounded-md bg-f1-panel p-3",
        TEXT_COLOR_CLASS[set.compound],
        "border border-f1-border",
      ].join(" ")}
    >
      <div className="flex items-center gap-3">
        <TyreDot compound={set.compound} size="lg" />
        <div className="flex-1">
          <p className="font-mono text-sm text-f1-text">{set.set_id}</p>
          <p className="text-xs text-f1-muted">{lapsLabel(set)}</p>
        </div>
        <span
          className={[
            "rounded px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider",
            savedForRace ? "bg-compound-medium text-f1-bg" : "bg-f1-border text-f1-muted",
          ].join(" ")}
        >
          {historyLabel(set)}
        </span>
      </div>
      <div className="mt-2 text-f1-text/80">
        <UsageBar set={set} />
      </div>
    </div>
  );
}
