/**
 * Central runtime configuration. Everything tunable lives here and is
 * overridable via environment variables so the engine can be reconfigured
 * without code changes (privacy retention, session thresholds, model choice…).
 */

function num(name: string, fallback: number): number {
  const v = process.env[name];
  if (v === undefined || v === '') return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function str(name: string, fallback: string): string {
  const v = process.env[name];
  return v === undefined || v === '' ? fallback : v;
}

function bool(name: string, fallback: boolean): boolean {
  const v = process.env[name];
  if (v === undefined || v === '') return fallback;
  return ['1', 'true', 'yes', 'on'].includes(v.toLowerCase());
}

export type ContentSensitivity = 'SAFE' | 'NORMAL';

export const config = {
  /** How long raw conversations are retained before automatic deletion. */
  rawDataRetentionDays: num('RAW_DATA_RETENTION_DAYS', 7),

  /** Gap (in hours) that separates one conversation "session" from the next. */
  sessionGapHours: num('SESSION_GAP_HOURS', 6),

  /** Default content filter. SAFE strips sensitive/explicit content from output. */
  contentSensitivity: str('CONTENT_SENSITIVITY', 'SAFE') as ContentSensitivity,

  /** Minimum confidence [0..1] required to keep an LLM-inferred artifact. */
  insideJokeConfidenceThreshold: num('INSIDE_JOKE_CONFIDENCE', 0.6),
  milestoneConfidenceThreshold: num('MILESTONE_CONFIDENCE', 0.6),

  ai: {
    provider: str('AI_PROVIDER', 'mock') as 'mock' | 'anthropic',
    apiKey: str('ANTHROPIC_API_KEY', ''),
    /** Cheap model for bulk chunk work. */
    analysisModel: str('ANALYSIS_MODEL', 'claude-haiku-4-5-20251001'),
    /** Expensive model for final synthesis. */
    synthesisModel: str('SYNTHESIS_MODEL', 'claude-opus-4-8'),
    maxRetries: num('AI_MAX_RETRIES', 3),
    /** Approx. messages per temporal chunk sent to the LLM. */
    chunkSize: num('AI_CHUNK_SIZE', 400),
  },

  branding: {
    name: str('BRAND_NAME', 'The Us Archive'),
    watermark: bool('BRAND_WATERMARK', true),
    watermarkText: str('BRAND_WATERMARK_TEXT', 'Made with The Us Archive'),
  },
} as const;

export type AppConfig = typeof config;
