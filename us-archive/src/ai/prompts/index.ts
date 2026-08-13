/**
 * Versioned prompt registry. Prompts live here (not inline in pipeline code) so
 * they can be reviewed and versioned independently. Every prompt declares the
 * `task` id the provider/mock switches on and the Zod output schema it targets.
 */
import { z } from 'zod';
import {
  AwardSchema,
  CommunicationSchema,
  CreativeSummarySchema,
  DictionaryEntrySchema,
  EraSchema,
  InsideJokeSchema,
  MemorableMomentSchema,
} from '../../profile/schema.js';

export interface PromptDef<T> {
  task: string;
  version: string;
  system: string;
  prompt: string;
  schema: z.ZodType<T, z.ZodTypeDef, any>;
}

const SAFETY = [
  'Never claim infidelity, diagnose mental health, label a relationship toxic,',
  'predict the future, or decide who loves whom more.',
  'Frame everything as playful, affectionate observation ("Based on your patterns…",',
  '"One playful reading is…"). Keep it warm, specific, and human.',
].join(' ');

export const insideJokesPrompt: PromptDef<{ insideJokes: z.infer<typeof InsideJokeSchema>[] }> = {
  task: 'inside_jokes',
  version: '1.0.0',
  system: `You surface a couple's inside jokes from candidate recurring terms. ${SAFETY}`,
  prompt:
    'Given candidate terms that recur unusually often, write a short, funny dictionary-style ' +
    'definition for each that is clearly supported by the evidence. Drop any candidate you are ' +
    'not confident about. Keep evidenceIds. Match the requested tone.',
  schema: z.object({ insideJokes: z.array(InsideJokeSchema) }),
};

export const dictionaryPrompt: PromptDef<{ dictionary: z.infer<typeof DictionaryEntrySchema>[] }> = {
  task: 'dictionary',
  version: '1.0.0',
  system: `You build "The Couple Dictionary" from recurring shared vocabulary. ${SAFETY}`,
  prompt:
    'Define each recurring term as a playful dictionary entry grounded in real usage. ' +
    'Only include terms you can justify from the evidence.',
  schema: z.object({ dictionary: z.array(DictionaryEntrySchema) }),
};

export const erasPrompt: PromptDef<{ relationshipEras: z.infer<typeof EraSchema>[] }> = {
  task: 'eras',
  version: '1.0.0',
  system: `You name and describe relationship eras from time-bucketed activity. ${SAFETY}`,
  prompt:
    'For each detected time bucket, give an evocative title and one-line description. Prefer ' +
    'neutral, time-based names (e.g. "Late Night Era", "Summer 2023") unless the messages clearly ' +
    'justify a themed name. Do not invent milestones.',
  schema: z.object({ relationshipEras: z.array(EraSchema) }),
};

export const awardsPrompt: PromptDef<{ awards: z.infer<typeof AwardSchema>[] }> = {
  task: 'awards',
  version: '1.0.0',
  system: `You write playful relationship "awards" from real statistics. ${SAFETY}`,
  prompt: 'Turn each award (category, winner, supporting stat) into a witty one-line citation.',
  schema: z.object({ awards: z.array(AwardSchema) }),
};

export const memorablePrompt: PromptDef<{
  memorableMoments: z.infer<typeof MemorableMomentSchema>[];
}> = {
  task: 'memorable',
  version: '1.0.0',
  system: `You select and title memorable little conversations. Never alter quoted text. ${SAFETY}`,
  prompt:
    'Give each supplied moment a title and a one-line description. Keep every quote verbatim and ' +
    'keep its messageId.',
  schema: z.object({ memorableMoments: z.array(MemorableMomentSchema) }),
};

export const communicationPrompt: PromptDef<z.infer<typeof CommunicationSchema>> = {
  task: 'communication_summary',
  version: '1.0.0',
  system: `You summarize a couple's communication rhythm from statistics. ${SAFETY}`,
  prompt: 'Write a warm 2–3 sentence summary of the communication style from the numbers provided.',
  schema: CommunicationSchema,
};

export const creativePrompt: PromptDef<z.infer<typeof CreativeSummarySchema>> = {
  task: 'creative',
  version: '1.0.0',
  system: `You write the cover copy, "If we were…" prompts, and a future letter. ${SAFETY}`,
  prompt:
    'Produce a cover title/subtitle, three "If we were…" prompt/answer pairs, a short future ' +
    'letter, and a closing line — all matching the requested tone.',
  schema: CreativeSummarySchema,
};
