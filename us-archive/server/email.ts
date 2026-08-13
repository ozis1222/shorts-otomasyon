/**
 * Web email service: renders templated transactional emails (link only, never
 * chat content — spec §30/§35), sends via the configured provider, and logs to
 * the DB. Console in dev; Resend in production.
 */
import { webEnv } from '../lib/env.js';
import { Logs } from '../db/repo.js';
import { subjectFor, type EmailTemplate } from '../src/integrations/email-provider.js';

interface SendArgs {
  orderId: string | null;
  to: string;
  template: EmailTemplate;
  vars: Record<string, string>;
}

function body(template: EmailTemplate, vars: Record<string, string>): string {
  const brand = 'The Us Archive';
  switch (template) {
    case 'upload_your_memories':
      return `Thanks for your order! Start your archive by uploading your chat here:\n${vars.link}\n\n— ${brand}`;
    case 'archive_in_progress':
      return `We're creating your archive now. This usually takes a few minutes. Track progress:\n${vars.link}\n\n— ${brand}`;
    case 'archive_ready':
      return `Your archive is ready 🎉\nView and download everything here:\n${vars.link}\n\n— ${brand}`;
    case 'download_before_expiry':
      return `A reminder to download your archive before your link expires (${vars.expires}):\n${vars.link}\n\n— ${brand}`;
    case 'data_deleted':
      return `As requested, your uploaded chat has been permanently deleted. Your archive files remain available until expiry.\n\n— ${brand}`;
  }
}

async function deliver(to: string, subject: string, text: string): Promise<void> {
  if (webEnv.emailProvider === 'resend' && webEnv.resendApiKey) {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${webEnv.resendApiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: webEnv.emailFrom, to, subject, text }),
    });
    if (!res.ok) throw new Error(`Resend failed: ${res.status} ${await res.text()}`);
    return;
  }
  // Console provider (dev): subject + link only.
  console.log(`[email] to=${to} subject="${subject}"\n${text}\n`);
}

export async function sendEmail({ orderId, to, template, vars }: SendArgs): Promise<void> {
  if (!to) return;
  try {
    await deliver(to, subjectFor(template), body(template, vars));
    Logs.email(orderId, to, template);
  } catch (err) {
    Logs.audit(orderId, 'email_failed', `${template}: ${String(err)}`);
  }
}
