export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export type Row = Record<string, unknown>

export async function getData<T = Row>(view: string, params: Record<string, string> = {}): Promise<T[]> {
  const qs = new URLSearchParams(params).toString()
  const res = await fetch(`${API_URL}/data/${view}${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error(`Falha ao ler ${view} (${res.status})`)
  return res.json() as Promise<T[]>
}

function accessHeaders(): Record<string, string> {
  let code = ''
  try { code = localStorage.getItem('accessCode') ?? '' } catch { /* sem storage */ }
  return { 'content-type': 'application/json', ...(code ? { 'x-access-code': code } : {}) }
}

export async function post<T>(path: string, body: unknown, method = 'POST'): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { method, headers: accessHeaders(), body: JSON.stringify(body) })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error((detail as { detail?: string }).detail ?? `Erro ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const usd = (v: unknown) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(v ?? 0))
export const num = (v: unknown, d = 0) =>
  new Intl.NumberFormat('pt-BR', { maximumFractionDigits: d, minimumFractionDigits: d }).format(Number(v ?? 0))
export const pct = (v: unknown, d = 1) => `${num(v, d)}%`
