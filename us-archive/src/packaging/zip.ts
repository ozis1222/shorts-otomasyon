/** Bundle the delivered archive into a single ZIP for secure download. */
import { createWriteStream } from 'node:fs';
import archiver from 'archiver';

export function zipDirectory(sourceDir: string, outPath: string): Promise<{ path: string; bytes: number }> {
  return new Promise((resolve, reject) => {
    const output = createWriteStream(outPath);
    const archive = archiver('zip', { zlib: { level: 9 } });
    output.on('close', () => resolve({ path: outPath, bytes: archive.pointer() }));
    archive.on('warning', (err) => {
      if ((err as any).code !== 'ENOENT') reject(err);
    });
    archive.on('error', reject);
    archive.pipe(output);
    archive.directory(sourceDir, false);
    archive.finalize();
  });
}
