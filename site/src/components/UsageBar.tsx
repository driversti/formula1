import { Group } from "@visx/group";
import { AxisBottom } from "@visx/axis";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";
import { ParentSize } from "@visx/responsive";

type SessionKey = "FP1" | "FP2" | "FP3" | "Q" | "R";

type Set = {
  set_id: string;
  compound: "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";
  laps: number;
  new_at_first_use: boolean;
  first_seen_session: SessionKey;
  last_seen_session: SessionKey;
};

const SESSIONS: ReadonlyArray<SessionKey> = ["FP1", "FP2", "FP3", "Q", "R"];
const HEIGHT = 60;
const MARGIN = { top: 4, right: 4, bottom: 26, left: 4 };

function firstToLastIndex(set: Set): [number, number] {
  return [SESSIONS.indexOf(set.first_seen_session), SESSIONS.indexOf(set.last_seen_session)];
}

export function UsageBar({ set }: { set: Set }) {
  return (
    <ParentSize>
      {({ width }) => {
        if (width === 0) return null;

        const xScale = scaleBand<string>({
          domain: SESSIONS as unknown as string[],
          range: [MARGIN.left, width - MARGIN.right],
          padding: 0.2,
        });
        const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
        const yScale = scaleLinear<number>({
          domain: [0, 1],
          range: [innerHeight, 0],
        });
        const [firstIdx, lastIdx] = firstToLastIndex(set);

        return (
          <svg width={width} height={HEIGHT} aria-label={`usage timeline for ${set.set_id}`}>
            <Group top={MARGIN.top}>
              {SESSIONS.map((s, i) => {
                const x = xScale(s)!;
                const bw = xScale.bandwidth();
                const active = i >= firstIdx && i <= lastIdx;
                return (
                  <Bar
                    key={s}
                    x={x}
                    y={yScale(1)}
                    width={bw}
                    height={innerHeight - yScale(1)}
                    fill={active ? "currentColor" : "rgba(255,255,255,0.08)"}
                    rx={2}
                  />
                );
              })}
            </Group>
            <AxisBottom
              top={HEIGHT - MARGIN.bottom}
              scale={xScale}
              tickFormat={(s) => String(s)}
              stroke="transparent"
              tickStroke="transparent"
              hideTicks
              tickLabelProps={() => ({
                fill: "var(--color-f1-muted)",
                fontSize: 11,
                textAnchor: "middle",
                dy: "1em",
                fontFamily: "var(--font-mono)",
              })}
            />
          </svg>
        );
      }}
    </ParentSize>
  );
}
