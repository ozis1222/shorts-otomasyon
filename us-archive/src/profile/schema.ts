/**
 * The canonical Relationship Profile. Every design surface (PDF, social cards,
 * fingerprint, wallpapers) is rendered from this single JSON — the renderer
 * never calls the LLM again. Zod both validates AI output and documents shape.
 */
import { z } from 'zod';

export const CoupleSchema = z.object({
  partnerA: z.string(),
  partnerB: z.string(),
  relationshipStartDate: z.string().nullable().optional(),
  anniversaryDate: z.string().nullable().optional(),
  firstDate: z.string().nullable().optional(),
  firstTrip: z.string().nullable().optional(),
  weddingDate: z.string().nullable().optional(),
  currentCity: z.string().nullable().optional(),
  language: z.enum(['en', 'tr']).default('en'),
  tone: z.enum(['romantic', 'funny', 'balanced', 'minimal', 'emotional']).default('balanced'),
});

export const StatisticsRefSchema = z.record(z.any()); // Full Statistics object.

export const CommunicationSchema = z.object({
  summary: z.string(),
  whoCards: z.array(
    z.object({
      question: z.string(),
      winner: z.string(),
      percentage: z.number(),
      loserPercentage: z.number().optional(),
    }),
  ),
});

export const EmojiSchema = z.object({
  top: z.array(z.object({ emoji: z.string(), count: z.number() })),
  interpretation: z.string(),
});

export const WordsSchema = z.object({
  top: z.array(z.object({ word: z.string(), count: z.number() })),
});

export const InsideJokeSchema = z.object({
  term: z.string(),
  definition: z.string(),
  /** [0..1] — items below the configured threshold are dropped upstream. */
  confidence: z.number().min(0).max(1),
  /** Message IDs that support the joke, for traceability. */
  evidenceIds: z.array(z.number()).default([]),
});

export const EraSchema = z.object({
  title: z.string(),
  startDate: z.string().nullable(),
  endDate: z.string().nullable(),
  description: z.string(),
  messageCount: z.number().default(0),
  highlight: z.string().default(''),
});

export const AwardSchema = z.object({
  category: z.string(),
  winner: z.string(),
  blurb: z.string(),
});

export const MemorableMomentSchema = z.object({
  title: z.string(),
  description: z.string(),
  /** Verbatim quoted lines, each traceable to a source message ID. */
  quotes: z.array(z.object({ messageId: z.number(), sender: z.string(), text: z.string() })),
});

export const DictionaryEntrySchema = z.object({
  term: z.string(),
  definition: z.string(),
  confidence: z.number().min(0).max(1),
  evidenceIds: z.array(z.number()).default([]),
});

const DnaDimension = z.object({ name: z.string(), score: z.number().min(0).max(100) });

export const RelationshipDnaSchema = z.object({
  disclaimer: z.string().default('For entertainment and memory-keeping purposes.'),
  dimensions: z.array(DnaDimension),
  archetypes: z.object({
    partnerA: z.array(z.object({ name: z.string(), percentage: z.number() })),
    partnerB: z.array(z.object({ name: z.string(), percentage: z.number() })),
  }),
});

export const QuoteSchema = z.object({
  messageId: z.number(),
  sender: z.string(),
  text: z.string(),
});

export const TimelineEventSchema = z.object({
  date: z.string().nullable(),
  label: z.string(),
  kind: z.enum(['provided', 'detected']),
  confidence: z.number().min(0).max(1).default(1),
});

export const FingerprintSchema = z.object({
  seed: z.string(),
  /** Normalized signal vector [0..1] used to drive the generative art. */
  signals: z.record(z.number()),
});

export const CreativeSummarySchema = z.object({
  coverTitle: z.string(),
  coverSubtitle: z.string(),
  ifWeWere: z.array(z.object({ prompt: z.string(), answer: z.string() })),
  futureLetter: z.string(),
  closingLine: z.string(),
});

export const RelationshipProfileSchema = z.object({
  schemaVersion: z.literal(1).default(1),
  generatedAt: z.string(),
  packageId: z.string(),
  couple: CoupleSchema,
  statistics: StatisticsRefSchema,
  communication: CommunicationSchema,
  emojis: EmojiSchema,
  words: WordsSchema,
  insideJokes: z.array(InsideJokeSchema),
  relationshipEras: z.array(EraSchema),
  awards: z.array(AwardSchema),
  memorableMoments: z.array(MemorableMomentSchema),
  dictionary: z.array(DictionaryEntrySchema),
  relationshipDna: RelationshipDnaSchema,
  quotes: z.array(QuoteSchema),
  timeline: z.array(TimelineEventSchema),
  fingerprint: FingerprintSchema,
  creativeSummary: CreativeSummarySchema,
});

export type RelationshipProfile = z.infer<typeof RelationshipProfileSchema>;
export type Couple = z.infer<typeof CoupleSchema>;
export type RelationshipDna = z.infer<typeof RelationshipDnaSchema>;
