import * as fs from "fs";

export function stamp(): number {
  // ruleid: typescript-clock
  return Date.now();
}

export function today(): Date {
  // ruleid: typescript-clock
  return new Date();
}

export function roll(): number {
  // ruleid: typescript-random
  return Math.random();
}

export function id(): string {
  // ruleid: typescript-random
  return crypto.randomUUID();
}

export function apiKey(): string | undefined {
  // ruleid: typescript-environment
  return process.env.API_KEY;
}

export async function load(url: string): Promise<Response> {
  // ruleid: typescript-io
  return fetch(url);
}

export function read(path: string): string {
  // ruleid: typescript-io
  return fs.readFileSync(path, "utf8");
}

export function log(message: string): void {
  // ruleid: typescript-io
  console.log(message);
}

// ok: typescript-clock
export const parse = (iso: string): Date => new Date(iso);

// ok: typescript-random
export const pick = <T>(items: readonly T[], index: number): T | undefined => items[index];
