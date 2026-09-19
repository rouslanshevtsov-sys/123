import { useState, useCallback } from 'react';
import { InterviewFlow } from './components/InterviewFlow';
import { BusinessCard } from './components/BusinessCard';
import { SourceInfo } from './components/SourceInfo';
import { GeneratedFiles } from './components/GeneratedFiles';
import { type BusinessContext, type InterviewAnswers } from './types';

type AppStep = 'intro' | 'source-info' | 'interview' | 'gaps' | 'competitor-questions' | 'card-review' | 'files';

const initialContext: BusinessContext = {
  status: 'draft',
  confirmationDate: null,
  sourceUrl: 'https://vk.ru/shpmcourse',
  sourceAccessible: false,
  sourceParseError: 'Страница VK недоступна для прямого парсинга (защита капчей). Требуется ручное заполнение.',
  business: {
    name: null,
    niche: null,
    positioning: null,
    description: null,
  },
  products: {
    main: [],
    secondary: [],
    assortmentWidth: null,
    producer: null,
    productionType: null,
  },
  audience: {
    targetSegments: [],
    tasks: [],
    painPoints: [],
  },
  geography: {
    regions: [],
    format: null,
  },
  pricing: {
    model: null,
    range: null,
  },
  salesProcess: {
    orderProcess: null,
    paymentMethods: [],
    deliveryOrAccess: null,
    salesFormat: null,
  },
  channels: {
    acquisition: [],
    onlinePresence: [],
  },
  advantages: [],
  limitations: [],
  keyFeatures: [],
  competitors: {
    known: [],
    directDefinition: '',
    indirectDefinition: '',
    attentionDefinition: '',
  },
  searchCriteria: {
    mustHaveFeatures: [],
    searchPlatforms: [],
    count: null,
    geography: null,
    vkAudienceLimit: null,
    publicationFreshness: null,
    include: [],
    exclude: [],
    searchQueries: [],
  },
  gaps: [],
};

export default function App() {
  const [step, setStep] = useState<AppStep>('intro');
  const [context, setContext] = useState<BusinessContext>(initialContext);
  const [answers, setAnswers] = useState<InterviewAnswers>({});

  const updateContext = useCallback((updates: Partial<BusinessContext>) => {
    setContext(prev => ({ ...prev, ...updates }));
  }, []);

  const updateAnswers = useCallback((key: string, value: string) => {
    setAnswers(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleInterviewComplete = useCallback(() => {
    setStep('gaps');
  }, []);

  const handleGapsReviewed = useCallback(() => {
    setStep('competitor-questions');
  }, []);

  const handleCompetitorQuestionsDone = useCallback(() => {
    setStep('card-review');
  }, []);

  const handleCardConfirmed = useCallback(() => {
    setContext(prev => ({
      ...prev,
      status: 'confirmed',
      confirmationDate: new Date().toISOString().split('T')[0],
    }));
    setStep('files');
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-lg font-bold">
              К
            </div>
            <div>
              <h1 className="text-lg font-semibold">Контекст бизнеса</h1>
              <p className="text-xs text-slate-400">Субагент 1 — Сбор и анализ</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              context.status === 'confirmed' 
                ? 'bg-green-500/20 text-green-300 border border-green-500/30' 
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            }`}>
              {context.status === 'confirmed' ? '✓ Подтверждено' : '● Draft'}
            </span>
          </div>
        </div>
      </header>

      {/* Progress */}
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <div className="flex items-center gap-1 mb-8">
          {['intro', 'source-info', 'interview', 'gaps', 'competitor-questions', 'card-review', 'files'].map((s, i) => (
            <div key={s} className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all ${
                step === s ? 'bg-blue-500 text-white scale-110' :
                ['intro', 'source-info', 'interview', 'gaps', 'competitor-questions', 'card-review', 'files'].indexOf(step) > i
                  ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                  : 'bg-slate-700 text-slate-400'
              }`}>
                {['intro', 'source-info', 'interview', 'gaps', 'competitor-questions', 'card-review', 'files'].indexOf(step) > i ? '✓' : i + 1}
              </div>
              {i < 6 && <div className={`w-8 h-0.5 ${
                ['intro', 'source-info', 'interview', 'gaps', 'competitor-questions', 'card-review', 'files'].indexOf(step) > i
                  ? 'bg-green-500/30' : 'bg-slate-700'
              }`} />}
            </div>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 pb-12">
        {step === 'intro' && (
          <div className="max-w-3xl mx-auto">
            <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 p-8">
              <h2 className="text-2xl font-bold mb-4">Добро пожаловать</h2>
              <p className="text-slate-300 mb-6 leading-relaxed">
                Этот инструмент поможет собрать полный контекст вашего бизнеса для последующего поиска и анализа конкурентов. 
                Мы пройдём несколько этапов:
              </p>
              <div className="space-y-4 mb-8">
                {[
                  { icon: '🔍', title: 'Изучение источников', desc: 'Анализ предоставленных ссылок и материалов' },
                  { icon: '🎤', title: 'Интервью о бизнесе', desc: 'До 15 вопросов для заполнения карточки бизнеса' },
                  { icon: '⚠️', title: 'Пробелы', desc: 'Показ оставшихся пробелов в информации' },
                  { icon: '🎯', title: 'Вопросы о конкурентах', desc: 'До 10 вопросов о критериях поиска конкурентов' },
                  { icon: '📋', title: 'Проверка карточки', desc: 'Ваша проверка и подтверждение' },
                  { icon: '📁', title: 'Итоговые файлы', desc: 'Генерация Markdown и JSON' },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-4 p-4 rounded-xl bg-slate-700/30 border border-slate-600/30">
                    <span className="text-2xl">{item.icon}</span>
                    <div>
                      <h3 className="font-medium text-white">{item.title}</h3>
                      <p className="text-sm text-slate-400">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setStep('source-info')}
                className="w-full py-3 px-6 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl font-medium hover:opacity-90 transition-opacity"
              >
                Начать →
              </button>
            </div>
          </div>
        )}

        {step === 'source-info' && (
          <SourceInfo
            context={context}
            onNext={() => setStep('interview')}
          />
        )}

        {step === 'interview' && (
          <InterviewFlow
            context={context}
            updateContext={updateContext}
            answers={answers}
            updateAnswers={updateAnswers}
            onComplete={handleInterviewComplete}
            block="business"
          />
        )}

        {step === 'gaps' && (
          <div className="max-w-3xl mx-auto">
            <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 p-8">
              <h2 className="text-2xl font-bold mb-4">⚠️ Оставшиеся пробелы</h2>
              <p className="text-slate-300 mb-6">
                На основе собранных данных, вот что осталось неясным. Предлагаю дополнительный раунд вопросов позже.
              </p>
              <div className="space-y-3 mb-8">
                {getGaps(context).map((gap, i) => (
                  <div key={i} className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                    <p className="text-red-300 text-sm">{gap}</p>
                  </div>
                ))}
                {getGaps(context).length === 0 && (
                  <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20">
                    <p className="text-green-300 text-sm">Все основные поля заполнены!</p>
                  </div>
                )}
              </div>
              <button
                onClick={handleGapsReviewed}
                className="w-full py-3 px-6 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl font-medium hover:opacity-90 transition-opacity"
              >
                Перейти к вопросам о конкурентах →
              </button>
            </div>
          </div>
        )}

        {step === 'competitor-questions' && (
          <InterviewFlow
            context={context}
            updateContext={updateContext}
            answers={answers}
            updateAnswers={updateAnswers}
            onComplete={handleCompetitorQuestionsDone}
            block="competitors"
          />
        )}

        {step === 'card-review' && (
          <BusinessCard
            context={context}
            onConfirm={handleCardConfirmed}
            onEdit={() => setStep('interview')}
          />
        )}

        {step === 'files' && (
          <GeneratedFiles context={context} />
        )}
      </main>
    </div>
  );
}

function getGaps(context: BusinessContext): string[] {
  const gaps: string[] = [];
  
  if (!context.business.name) gaps.push('Название бизнеса не указано');
  if (!context.business.niche) gaps.push('Маркетинговая ниша не определена');
  if (!context.business.description) gaps.push('Описание бизнеса отсутствует');
  if (context.products.main.length === 0) gaps.push('Основные продукты не перечислены');
  if (!context.products.producer) gaps.push('Не указано, кто производит/поставляет продукты');
  if (context.audience.targetSegments.length === 0) gaps.push('Целевые сегменты аудитории не определены');
  if (context.geography.regions.length === 0) gaps.push('География работы не указана');
  if (!context.pricing.model) gaps.push('Модель ценообразования не описана');
  if (!context.salesProcess.orderProcess) gaps.push('Процесс заказа не описан');
  if (context.channels.acquisition.length === 0) gaps.push('Каналы привлечения клиентов не указаны');
  if (context.advantages.length === 0) gaps.push('Преимущества бизнеса не перечислены');
  if (context.competitors.known.length === 0) gaps.push('Известные конкуренты не указаны');
  if (!context.searchCriteria.count) gaps.push('Количество конкурентов для поиска не указано');
  
  return gaps;
}
