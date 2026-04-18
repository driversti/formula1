type SessionKey = "R" | "S";

type Props = {
  value: SessionKey;
  onChange: (v: SessionKey) => void;
};

const KEYS: ReadonlyArray<{ k: SessionKey; label: string }> = [
  { k: "S", label: "SPRINT" },
  { k: "R", label: "RACE" },
];

export function SessionTabs({ value, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Session"
      className="mb-4 inline-flex rounded-md border border-f1-border bg-f1-panel p-1"
    >
      {KEYS.map(({ k, label }) => {
        const active = value === k;
        return (
          <button
            key={k}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(k)}
            className={`rounded px-3 py-1 font-mono text-xs font-semibold tracking-widest transition ${
              active ? "bg-f1-border text-f1-text" : "text-f1-muted hover:text-f1-text"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
