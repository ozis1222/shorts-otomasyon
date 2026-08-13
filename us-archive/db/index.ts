/**
 * Database connection via Node's built-in SQLite (zero native deps). One shared
 * connection per process. The DDL in schema.sql is Postgres-compatible, so
 * moving to Supabase later is a driver swap, not a rewrite.
 */
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dbPath } from '../lib/env.js';

let db: DatabaseSync | null = null;

export function getDb(): DatabaseSync {
  if (db) return db;
  const path = dbPath();
  mkdirSync(dirname(path), { recursive: true });
  db = new DatabaseSync(path);
  db.exec('PRAGMA journal_mode = WAL;');
  db.exec('PRAGMA foreign_keys = ON;');
  const schemaPath = join(dirname(fileURLToPath(import.meta.url)), 'schema.sql');
  db.exec(readFileSync(schemaPath, 'utf8'));
  return db;
}

export function nowIso(): string {
  return new Date().toISOString();
}
