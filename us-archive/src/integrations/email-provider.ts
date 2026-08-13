/**
 * Email provider abstraction (spec §30). Console provider for development;
 * Resend/SMTP implement the same interface. Templates are content-only — no raw
 * chat is ever placed in an email.
 */
export type EmailTemplate =
  | 'upload_your_memories'
  | 'archive_in_progress'
  | 'archive_ready'
  | 'download_before_expiry'
  | 'data_deleted';

export interface EmailMessage {
  to: string;
  template: EmailTemplate;
  vars: Record<string, string>;
}

export interface EmailProvider {
  readonly name: string;
  send(msg: EmailMessage): Promise<void>;
}

const SUBJECTS: Record<EmailTemplate, string> = {
  upload_your_memories: 'Upload your memories to start your archive',
  archive_in_progress: 'Your archive is being created',
  archive_ready: 'Your archive is ready 🎉',
  download_before_expiry: 'Download your archive before it expires',
  data_deleted: 'Your chat data has been deleted',
};

export class ConsoleEmailProvider implements EmailProvider {
  readonly name = 'console';
  async send(msg: EmailMessage): Promise<void> {
    // Dev-only: subject + link, never message content.
    console.log(`[email:console] to=${msg.to} subject="${SUBJECTS[msg.template]}" vars=${JSON.stringify(msg.vars)}`);
  }
}

export function subjectFor(t: EmailTemplate): string {
  return SUBJECTS[t];
}
