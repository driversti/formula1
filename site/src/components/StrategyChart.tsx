import { Fragment, type CSSProperties } from "react";
import { Group } from "@visx/group";
import { scaleLinear, scaleBand } from "@visx/scale";
import { Bar } from "@visx/shape";
import { ParentSize } from "@visx/responsive";
import { AxisBottom } from "@visx/axis";
import { useTooltip, TooltipWithBounds, defaultStyles } from "@visx/tooltip";

type Compound = "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";

type TrackStatusCode = "Yellow" | "SCDeployed" | "VSCDeployed" | "Red";

type StatusBand = {
  status: TrackStatusCode;
  start_lap: number;
  end_lap: number;
};

// STATUS_LABEL is pre-declared for Task 14 (tooltip wiring) — not yet used.
const STATUS_LABEL: Record<TrackStatusCode, string> = {
  Yellow: "Yellow",
  SCDeployed: "Safety Car",
  VSCDeployed: "Virtual Safety Car",
  Red: "Red Flag",
};
void STATUS_LABEL;

type RaceStint = {
  stint_idx: number;
  compound: Compound;
  start_lap: number;
  end_lap: number;
  laps: number;
  new: boolean;
};

type Driver = {
  racing_number: string;
  tla: string;
  full_name: string;
  team_name: string;
  team_color: string;
  grid_position: number | null;
  sets: unknown[];
  race_stints: RaceStint[];
  sprint_stints: RaceStint[];
  final_position: number | null;
  dnf_at_lap: number | null;
  sprint_final_position: number | null;
  sprint_dnf_at_lap: number | null;
};

type Props = {
  drivers: Driver[];
  sessionKey: "R" | "S";
  totalLaps: number;
  statusBands: StatusBand[];
};

const ROW_H = 34;
const PAD = { top: 16, right: 60, bottom: 24, left: 52 };

const COMPOUND_LETTER: Record<Compound, string> = {
  SOFT: "S",
  MEDIUM: "M",
  HARD: "H",
  INTERMEDIATE: "I",
  WET: "W",
};

function compoundColorVar(c: Compound): string {
  const slug = c === "INTERMEDIATE" ? "inter" : c.toLowerCase();
  return `var(--color-compound-${slug})`;
}

function compoundTextColor(c: Compound): string {
  return c === "MEDIUM" || c === "HARD" ? "#111" : "#fff";
}

type Row = {
  driver: Driver;
  stints: RaceStint[];
  finalPos: number | null;
  dnfAtLap: number | null;
};

type TooltipData = {
  tla: string;
  stintIdx: number;
  totalStints: number;
  compound: Compound;
  startLap: number;
  endLap: number;
  laps: number;
  isNew: boolean;
  dnfAtLap: number | null;
  isLastStint: boolean;
};

function prepareRows(drivers: Driver[], sessionKey: "R" | "S"): Row[] {
  return drivers
    .map<Row>((d) => ({
      driver: d,
      stints: sessionKey === "R" ? d.race_stints : d.sprint_stints,
      finalPos: sessionKey === "R" ? d.final_position : d.sprint_final_position,
      dnfAtLap: sessionKey === "R" ? d.dnf_at_lap : d.sprint_dnf_at_lap,
    }))
    .filter((r) => r.stints.length > 0)
    .sort((a, b) => {
      if (a.finalPos != null && b.finalPos != null) return a.finalPos - b.finalPos;
      if (a.finalPos != null) return -1;
      if (b.finalPos != null) return 1;
      return (b.dnfAtLap ?? 0) - (a.dnfAtLap ?? 0);
    });
}

const TOOLTIP_STYLES: CSSProperties = {
  ...defaultStyles,
  background: "#17171c",
  color: "#eaeaf0",
  border: "1px solid #2a2f3a",
  fontFamily: "ui-monospace, monospace",
  fontSize: 12,
  padding: 8,
  lineHeight: 1.6,
};

export function StrategyChart({ drivers, sessionKey, totalLaps, statusBands }: Props) {
  void statusBands;
  const rows = prepareRows(drivers, sessionKey);
  const {
    tooltipData,
    tooltipLeft,
    tooltipTop,
    tooltipOpen,
    showTooltip,
    hideTooltip,
  } = useTooltip<TooltipData>();

  if (rows.length === 0) {
    return <p className="text-sm text-f1-muted">No stints recorded for this session.</p>;
  }
  const height = PAD.top + rows.length * ROW_H + PAD.bottom;

  return (
    <div className="relative">
      <ParentSize>
        {({ width }) => {
          if (width === 0) return null;

          const narrow = width < 480;
          const leftCol = narrow ? 38 : PAD.left;
          const xScale = scaleLinear<number>({
            domain: [1, Math.max(totalLaps + 1, 2)],
            range: [leftCol, width - PAD.right],
          });
          const yScale = scaleBand<number>({
            domain: rows.map((_, i) => i),
            range: [PAD.top, PAD.top + rows.length * ROW_H],
            padding: 0.15,
          });
          const labelThreshold = narrow ? 48 : 34;

          return (
            <svg width={width} height={height} role="img" aria-label="Race strategy chart">
              {rows.map((row, i) => {
                const y = yScale(i)!;
                return (
                  <Group key={row.driver.tla} data-testid="strategy-row" data-tla={row.driver.tla}>
                    <text
                      x={leftCol - 10}
                      y={y + ROW_H / 2}
                      textAnchor="end"
                      dominantBaseline="middle"
                      className="fill-f1-muted font-mono text-xs font-semibold tracking-widest"
                    >
                      {row.driver.tla}
                    </text>
                    {row.stints.map((s) => {
                      const x0 = xScale(s.start_lap);
                      const x1 = xScale(s.end_lap + 1);
                      const w = Math.max(x1 - x0 - 2, 0);
                      const showLabel = w >= labelThreshold;
                      const isLastStint = s.stint_idx === row.stints.length - 1;
                      return (
                        <Fragment key={s.stint_idx}>
                          <Bar
                            x={x0}
                            y={y + 4}
                            width={w}
                            height={ROW_H - 8}
                            fill={compoundColorVar(s.compound)}
                            rx={3}
                            data-testid="stint-segment"
                            onMouseMove={(e) => {
                              const svg = (e.currentTarget as SVGElement).ownerSVGElement;
                              const rect = svg?.getBoundingClientRect();
                              showTooltip({
                                tooltipLeft: rect ? e.clientX - rect.left : e.clientX,
                                tooltipTop: rect ? e.clientY - rect.top : e.clientY,
                                tooltipData: {
                                  tla: row.driver.tla,
                                  stintIdx: s.stint_idx,
                                  totalStints: row.stints.length,
                                  compound: s.compound,
                                  startLap: s.start_lap,
                                  endLap: s.end_lap,
                                  laps: s.laps,
                                  isNew: s.new,
                                  dnfAtLap: row.dnfAtLap,
                                  isLastStint,
                                },
                              });
                            }}
                            onMouseLeave={hideTooltip}
                          />
                          {s.new && (
                            <circle
                              cx={x0 + w - 5}
                              cy={y + 8}
                              r={2.5}
                              fill={s.compound === "HARD" ? "#333" : "rgba(255,255,255,0.85)"}
                            />
                          )}
                          {showLabel && (
                            <text
                              x={x0 + 6}
                              y={y + ROW_H / 2 + 1}
                              dominantBaseline="middle"
                              fontFamily="ui-monospace, monospace"
                              fontSize={11}
                              fontWeight={700}
                              fill={compoundTextColor(s.compound)}
                            >
                              {COMPOUND_LETTER[s.compound]} · {s.laps}
                            </text>
                          )}
                        </Fragment>
                      );
                    })}
                    <text
                      x={width - PAD.right + 8}
                      y={y + ROW_H / 2}
                      dominantBaseline="middle"
                      fontFamily="ui-monospace, monospace"
                      fontSize={11}
                      fontWeight={700}
                      className={row.dnfAtLap != null ? "fill-compound-soft" : "fill-f1-muted"}
                    >
                      {row.dnfAtLap != null
                        ? `RET L${row.dnfAtLap}`
                        : row.finalPos != null
                          ? `P${row.finalPos}`
                          : "—"}
                    </text>
                  </Group>
                );
              })}
              <AxisBottom
                scale={xScale}
                top={PAD.top + rows.length * ROW_H + 4}
                numTicks={Math.min(7, totalLaps)}
                tickFormat={(v) => String(v)}
                tickLabelProps={() => ({
                  fontFamily: "ui-monospace, monospace",
                  fontSize: 10,
                  fill: "var(--color-f1-muted)",
                  textAnchor: "middle",
                })}
                stroke="var(--color-f1-border)"
                tickStroke="var(--color-f1-border)"
              />
            </svg>
          );
        }}
      </ParentSize>
      {tooltipOpen && tooltipData && (
        <TooltipWithBounds
          top={tooltipTop}
          left={tooltipLeft}
          style={TOOLTIP_STYLES}
        >
          <div>
            {tooltipData.tla} · Stint {tooltipData.stintIdx + 1} / {tooltipData.totalStints}
          </div>
          <div>
            {tooltipData.compound} · laps {tooltipData.startLap}–{tooltipData.endLap} ({tooltipData.laps} laps)
          </div>
          <div>{tooltipData.isNew ? "New set" : "Used set"}</div>
          {tooltipData.dnfAtLap != null && tooltipData.isLastStint && (
            <div>Retired at lap {tooltipData.dnfAtLap}</div>
          )}
        </TooltipWithBounds>
      )}
    </div>
  );
}
