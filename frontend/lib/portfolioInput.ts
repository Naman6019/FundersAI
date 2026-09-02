const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuid(value: unknown): value is string {
  return typeof value === 'string' && UUID_PATTERN.test(value);
}

export function parsePortfolioName(value: unknown): string | null {
  if (value === undefined || value === null) return 'My research portfolio';
  if (typeof value !== 'string') return null;
  const name = value.trim();
  return name && name.length <= 80 ? name : null;
}

function parseDecimal(value: unknown, maxDecimals: number, maximum: number): number | null {
  const raw = typeof value === 'number' ? String(value) : typeof value === 'string' ? value.trim() : '';
  if (!/^\d+(?:\.\d+)?$/.test(raw)) return null;
  const decimals = raw.split('.')[1]?.length || 0;
  if (decimals > maxDecimals) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed <= maximum ? parsed : null;
}

export function parseSchemeCode(value: unknown): number | null {
  const raw = typeof value === 'number' ? String(value) : typeof value === 'string' ? value.trim() : '';
  if (!/^\d{1,9}$/.test(raw)) return null;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function parsePositionInput(body: Record<string, unknown>): {
  scheme_code: number;
  units: number;
  current_value: number;
} | null {
  const schemeCode = parseSchemeCode(body.scheme_code ?? body.schemeCode);
  const units = parseDecimal(body.units, 8, 1e15);
  const currentValue = parseDecimal(body.current_value ?? body.currentValue, 4, 1e15);
  if (schemeCode === null || units === null || units <= 0 || currentValue === null) return null;
  return { scheme_code: schemeCode, units, current_value: currentValue };
}

export function parsePositionPatch(body: Record<string, unknown>): Partial<{
  units: number;
  current_value: number;
}> | null {
  const patch: { units?: number; current_value?: number } = {};
  if ('units' in body) {
    const units = parseDecimal(body.units, 8, 1e15);
    if (units === null || units <= 0) return null;
    patch.units = units;
  }
  if ('current_value' in body || 'currentValue' in body) {
    const currentValue = parseDecimal(body.current_value ?? body.currentValue, 4, 1e15);
    if (currentValue === null) return null;
    patch.current_value = currentValue;
  }
  return Object.keys(patch).length ? patch : null;
}
