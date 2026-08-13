/**
 * Model-provider abstraction. Anthropic is the first concrete provider; the
 * interface is deliberately generic so OpenAI/Gemini can be added later without
 * touching the pipeline. A `mock` provider synthesizes well-formed output from
 * the deterministic candidate payload so the whole engine runs offline with no
 * API key (used by the demo and tests).
 */
import { z } from 'zod';
import { config } from '../config/index.js';
import { synthesizeMock } from './mock.js';

export interface GenerateOptions<T> {
  /** Stable stage identifier — used for logging and by the mock provider. */
  task: string;
  /** Optional prompt version (carried through when spreading a PromptDef). */
  version?: string;
  system: string;
  /** Human-readable instruction template. */
  prompt: string;
  /** Deterministic candidates / stats the model should phrase (never raw chat in bulk). */
  payload: unknown;
  schema: z.ZodType<T, z.ZodTypeDef, any>;
  model?: string;
}

export interface ModelProvider {
  readonly name: string;
  generate<T>(opts: GenerateOptions<T>): Promise<T>;
}

class MockProvider implements ModelProvider {
  readonly name = 'mock';
  async generate<T>(opts: GenerateOptions<T>): Promise<T> {
    const raw = synthesizeMock(opts.task, opts.payload);
    return opts.schema.parse(raw);
  }
}

class AnthropicProvider implements ModelProvider {
  readonly name = 'anthropic';
  private client: any;

  private async getClient() {
    if (!this.client) {
      const { default: Anthropic } = await import('@anthropic-ai/sdk');
      this.client = new Anthropic({ apiKey: config.ai.apiKey });
    }
    return this.client;
  }

  async generate<T>(opts: GenerateOptions<T>): Promise<T> {
    const client = await this.getClient();
    const model = opts.model || config.ai.analysisModel;
    const userContent =
      `${opts.prompt}\n\nDATA (JSON):\n${JSON.stringify(opts.payload)}\n\n` +
      `Respond with ONLY a valid JSON object. No prose, no markdown fences.`;

    let lastErr: unknown;
    for (let attempt = 0; attempt < config.ai.maxRetries; attempt++) {
      try {
        const res = await client.messages.create({
          model,
          max_tokens: 4096,
          system: opts.system,
          messages: [{ role: 'user', content: userContent }],
        });
        const text = res.content
          .filter((b: any) => b.type === 'text')
          .map((b: any) => b.text)
          .join('');
        const json = extractJson(text);
        return opts.schema.parse(json);
      } catch (err) {
        lastErr = err;
        // Exponential backoff between retries.
        await new Promise((r) => setTimeout(r, 500 * 2 ** attempt));
      }
    }
    throw new Error(`Anthropic generate failed for task "${opts.task}": ${String(lastErr)}`);
  }
}

/** Pull the first JSON object out of a model response, tolerating fences. */
function extractJson(text: string): unknown {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidate = fenced ? fenced[1] : text;
  const start = candidate.indexOf('{');
  const end = candidate.lastIndexOf('}');
  if (start === -1 || end === -1) throw new Error('No JSON object in model response');
  return JSON.parse(candidate.slice(start, end + 1));
}

export function createProvider(): ModelProvider {
  if (config.ai.provider === 'anthropic' && config.ai.apiKey) return new AnthropicProvider();
  return new MockProvider();
}
