export const TYPE_STYLES: Record<string, { bg: string; text: string; icon: string }> = {
  hr: { bg: "var(--color-green-muted)", text: "var(--color-green-text)", icon: "📋" },
  engineering: { bg: "var(--color-blue-muted)", text: "var(--color-blue-text)", icon: "⚙️" },
  onboarding: { bg: "var(--color-purple-muted)", text: "var(--color-purple-text)", icon: "🎯" },
  product: { bg: "var(--color-orange-muted)", text: "var(--color-orange-text)", icon: "📦" },
  security: { bg: "var(--color-red-muted)", text: "var(--color-red-text)", icon: "🔒" },
};

export const DEFAULT_STYLE = {
  bg: "var(--color-surface-overlay)",
  text: "var(--color-text-secondary)",
  icon: "📄",
};

export function nameToSlug(name: string): string {
  return name.toLowerCase().replace(/ /g, "-");
}
