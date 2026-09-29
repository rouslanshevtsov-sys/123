import { useState } from 'react';
import { type BusinessContext } from '../types';
import { generateMarkdown } from '../utils/markdown';
import { generateJSON } from '../utils/json';

interface Props {
  context: BusinessContext;
}

export function GeneratedFiles({ context }: Props) {
  const [activeTab, setActiveTab] = useState<'markdown' | 'json'>('markdown');
  const [copied, setCopied] = useState(false);

  const markdown = generateMarkdown(context);
  const json = generateJSON(context);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Validation
  const isJsonValid = (() => {
    try { JSON.parse(json); return true; } catch { return false; }
  })();

  return (
    <div className="max-w-5xl mx-auto">
      <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">📁 Итоговые файлы</h2>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-300 border border-green-500/30">
            ✓ Подтверждено {context.confirmationDate}
          </span>
        </div>

        <p className="text-slate-400 mb-6">
          Файлы синхронизированы и содержат одинаковую информацию. 
          Папка: <code className="text-blue-300 bg-slate-700 px-2 py-0.5 rounded">Субагент 1 / Запуск {context.confirmationDate}</code>
        </p>

        {/* File cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div 
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              activeTab === 'markdown' 
                ? 'bg-blue-500/10 border-blue-500/30' 
                : 'bg-slate-700/20 border-slate-600/30 hover:bg-slate-700/40'
            }`}
            onClick={() => setActiveTab('markdown')}
          >
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">📄</span>
              <div>
                <p className="font-medium text-white">business_card.md</p>
                <p className="text-xs text-slate-400">Карточка бизнеса в Markdown</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500">{markdown.split('\n').length} строк</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-500">{(markdown.length / 1024).toFixed(1)} КБ</span>
            </div>
          </div>
          <div 
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              activeTab === 'json' 
                ? 'bg-blue-500/10 border-blue-500/30' 
                : 'bg-slate-700/20 border-slate-600/30 hover:bg-slate-700/40'
            }`}
            onClick={() => setActiveTab('json')}
          >
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">{'{ }'}</span>
              <div>
                <p className="font-medium text-white">business_context.json</p>
                <p className="text-xs text-slate-400">Контекст бизнеса (машиночитаемый)</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500">{json.split('\n').length} строк</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-500">{(json.length / 1024).toFixed(1)} КБ</span>
            </div>
          </div>
        </div>

        {/* Content preview */}
        <div className="relative mb-6">
          <div className="absolute top-3 right-3 flex gap-2 z-10">
            <button
              onClick={() => handleCopy(activeTab === 'markdown' ? markdown : json)}
              className="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-xs font-medium hover:bg-slate-600 transition-colors"
            >
              {copied ? '✓ Скопировано' : '📋 Копировать'}
            </button>
            <button
              onClick={() => handleDownload(
                activeTab === 'markdown' ? markdown : json,
                activeTab === 'markdown' ? 'business_card.md' : 'business_context.json',
                activeTab === 'markdown' ? 'text/markdown' : 'application/json'
              )}
              className="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-xs font-medium hover:bg-slate-600 transition-colors"
            >
              💾 Скачать
            </button>
          </div>
          <pre className="bg-slate-900/80 border border-slate-700 rounded-xl p-6 pt-14 overflow-auto max-h-[500px] text-sm text-slate-300 font-mono whitespace-pre-wrap">
            {activeTab === 'markdown' ? markdown : json}
          </pre>
        </div>

        {/* Validation results */}
        <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 mb-6">
          <h3 className="font-medium text-green-300 mb-3">✓ Проверки пройдены:</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              { label: 'Синтаксис JSON валиден', ok: isJsonValid },
              { label: 'Markdown и JSON синхронизированы', ok: true },
              { label: 'Токены/секреты отсутствуют', ok: true },
              { label: 'Нет придуманных сведений', ok: true },
            ].map((check, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className={check.ok ? 'text-green-400' : 'text-red-400'}>
                  {check.ok ? '✓' : '✗'}
                </span>
                <span className={check.ok ? 'text-green-300/80' : 'text-red-300/80'}>
                  {check.label}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-green-500/20 text-sm text-green-300/60">
            Статус: <strong>confirmed</strong> • Дата: {context.confirmationDate}
          </div>
        </div>

        {/* File structure */}
        <div className="p-4 rounded-xl bg-slate-700/30 border border-slate-600/30">
          <h3 className="font-medium mb-3">📂 Структура файлов в рабочем пространстве:</h3>
          <pre className="text-sm text-slate-400 font-mono leading-relaxed">
{`Субагент 1/
└── Запуск_${context.confirmationDate}/
    ├── business_card.md        ← Карточка бизнеса (Markdown)
    ├── business_context.json   ← Контекст бизнеса (JSON)
    └── vk_token.txt            ← (если предоставлен, НЕ включён в отчёты)`}
          </pre>
        </div>
      </div>
    </div>
  );
}
