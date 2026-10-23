import { useState } from 'react'
import AssistantPage from './Assistant'
import DataOpsPage from './DataOps'
import OverviewPage from './Overview'
import RiskPage from './Risk'

const TABS = [
  { id: 'geral', label: 'Visão geral', who: 'CEO' },
  { id: 'risco', label: 'Contas em risco', who: 'Customer Success' },
  { id: 'dados', label: 'Ingestão e catálogo', who: 'Dados' },
  { id: 'ia', label: 'Assistente de IA', who: 'Todos' },
] as const
type Tab = (typeof TABS)[number]['id']

export default function App() {
  const [tab, setTab] = useState<Tab>(() => {
    const h = window.location.hash.slice(1)
    return (TABS.some((t) => t.id === h) ? h : 'geral') as Tab
  })
  const [question, setQuestion] = useState<string | null>(null)
  const go = (t: Tab) => { setTab(t); window.location.hash = t }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">RavenStack · Diagnóstico de churn</h1>
          <p className="muted text-sm">Lake no Supabase (raw → bronze → silver → gold) · dados sintéticos do Kaggle (River @ Rivalytics, MIT)</p>
        </div>
        <nav className="flex flex-wrap gap-1 rounded-xl bg-slate-200/60 p-1 dark:bg-slate-800">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => go(t.id)} title={t.who}
              className={`rounded-lg px-3 py-1.5 text-sm ${tab === t.id ? 'bg-white shadow-sm dark:bg-slate-950' : 'muted'}`}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      {tab === 'geral' && <OverviewPage />}
      {tab === 'risco' && <RiskPage onAsk={(q) => { setQuestion(q); go('ia') }} />}
      {tab === 'dados' && <DataOpsPage />}
      {tab === 'ia' && <AssistantPage initialQuestion={question} />}
    </div>
  )
}
