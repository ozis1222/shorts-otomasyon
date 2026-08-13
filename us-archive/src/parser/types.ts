export type MessageType =
  | 'text'
  | 'media'
  | 'sticker'
  | 'gif'
  | 'voice'
  | 'video'
  | 'image'
  | 'audio'
  | 'document'
  | 'deleted'
  | 'location'
  | 'contact'
  | 'system';

/** A single normalized chat message. `id` gives every quote traceability. */
export interface ParsedMessage {
  id: number;
  /** ISO 8601 timestamp. */
  timestamp: string;
  /** Epoch milliseconds — precomputed for cheap stats math. */
  ts: number;
  sender: string;
  message: string;
  type: MessageType;
  links: string[];
  emoji: string[];
  /** Number of Unicode code-point "words" (whitespace split). */
  wordCount: number;
}

export interface ParseResult {
  messages: ParsedMessage[];
  /** Distinct human senders (system messages excluded). */
  participants: string[];
  /** Diagnostics — never contains raw message content. */
  meta: {
    totalLines: number;
    parsedMessages: number;
    systemMessages: number;
    unparsedLines: number;
    detectedFormat: string;
    dateOrder: 'DMY' | 'MDY' | 'YMD' | 'unknown';
    firstTimestamp: string | null;
    lastTimestamp: string | null;
  };
}
