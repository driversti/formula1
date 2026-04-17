// Hand-written union used because Manifest["race"] is z.any() in the
// auto-generated schemas.ts, so the inferred type chain would resolve to `any`.
type Compound = "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";

const COLOR_CLASS: Record<Compound, string> = {
  SOFT: "bg-compound-soft",
  MEDIUM: "bg-compound-medium",
  HARD: "bg-compound-hard ring-1 ring-f1-border",
  INTERMEDIATE: "bg-compound-inter",
  WET: "bg-compound-wet",
};

const SIZE_CLASS = {
  sm: "w-3 h-3",
  md: "w-4 h-4",
  lg: "w-6 h-6",
} as const;

type Props = {
  compound: Compound;
  size?: keyof typeof SIZE_CLASS;
  "aria-label"?: string;
  className?: string;
};

export function TyreDot({ compound, size = "sm", className = "", ...rest }: Props) {
  const classes = [
    "inline-block rounded-full",
    SIZE_CLASS[size],
    COLOR_CLASS[compound],
    className,
  ].join(" ");
  return <span className={classes} {...rest} />;
}
