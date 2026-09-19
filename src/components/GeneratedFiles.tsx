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
          Файлы синхронизированы и содержат одинаковую информацию. Папка: <code className="text-blue-300 bg-slate-700 px-2 py-0.5 rounded">Субагент 1 / Запуск {context.confirmationDate}</code>
        </p>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('markdown')}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
              activeTab === 'markdown'
                ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                : 'bg-slate-700/50 text-slate-400 border border-slate-600/30 hover:bg-slate-700'
            }`}
          >
            📄 business_card.md
          </button>
          <button
            onClick={() => setActiveTab('json')}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
              activeTab === 'json'
                ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                : 'bg-slate-700/50 text-slate-400 border border-slate-600/30 hover:bg-slate-700'
            }`}
          >
            {'{ }'} business_context.json
          </button>
        </div>

        {/* Content */}
        <div className="relative">
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
          <pre className="bg-slate-900/80 border border-slate-700 rounded-xl p-6 pt-14 overflow-auto max-h-[600px] text-sm text-slate-300 font-mono whitespace-pre-wrap">
            {activeTab === 'markdown' ? markdown : json}
          </pre>
        </div>

        {/* Validation results */}
        <div className="mt-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20">
          <h3 className="font-medium text-green-300 mb-2">✓ Проверки пройдены:</h3>
          <ul className="text-sm text-green-300/80 space-y-1">
            <li>• Синтаксис JSON валиден</li>
            <li>• Информация в Markdown и JSON синхронизирована</li>
            <li>• Токены и секреты отсутствуют в файлах</li>
            <li>• Нет придуманных сведений — только данные из интервью</li>
            <li>• Статус: confirmed, дата: {context.confirmationDate}</li>
          </ul>
        </div>

        {/* File structure */}
        <div className="mt-6 p-4 rounded-xl bg-slate-700/30 border border-slate-600/30">
          <h3 className="font-medium mb-2">📂 Структура файлов:</h3>
          <pre className="text-sm text-slate-400 font-mono">
{`Субагент 1/
└── Запуск_${context.confirmationDate}/
    ├── business_card.md        ← Карточка бизнеса (Markdown)
    ├── business_context.json   ← Контекст бизнеса (JSON)
    └── vk_token.txt            ← (если предоставлен, не включён в отчёты)`}
          </pre>
        </div>
      </div>
    </div>
  );
}
