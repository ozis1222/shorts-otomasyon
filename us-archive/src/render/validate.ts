/**
 * Pre-render validation (spec §37). No deliverable may contain undefined, null,
 * [object Object], NaN, Lorem ipsum, or empty chart markers. Throws with a
 * pointer to the offending fragment so the pipeline can fail loudly, not ship
 * broken output.
 */
const FORBIDDEN: { name: string; re: RegExp }[] = [
  { name: 'undefined', re: /\bundefined\b/ },
  { name: 'null-token', re: />\s*null\s*</ },
  { name: 'object-Object', re: /\[object Object\]/ },
  { name: 'NaN', re: /\bNaN\b/ },
  { name: 'lorem-ipsum', re: /lorem ipsum/i },
  { name: 'placeholder', re: /\bplaceholder\b/i },
  { name: 'empty-svg', re: /<svg[^>]*>\s*<\/svg>/ },
];

export function validateHTML(html: string): void {
  for (const { name, re } of FORBIDDEN) {
    const m = re.exec(html);
    if (m) {
      const around = html.slice(Math.max(0, m.index - 40), m.index + 40).replace(/\s+/g, ' ');
      throw new Error(`Output validation failed — found "${name}" near: …${around}…`);
    }
  }
}
