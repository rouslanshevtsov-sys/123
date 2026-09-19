import { useState } from 'react';
import { type BusinessContext, type InterviewAnswers, type Question } from '../types';

interface Props {
  context: BusinessContext;
  updateContext: (updates: Partial<BusinessContext>) => void;
  answers: InterviewAnswers;
  updateAnswers: (key: string, value: string) => void;
  onComplete: () => void;
  block: 'business' | 'competitors';
}

const businessQuestions: Question[] = [
  {
    id: 'b1',
    text: 'Как называется ваш бизнес? (Из поиска: «Школа Практического Маркетинга» — это верно?)',
    placeholder: 'Например: Школа Практического Маркетинга, SHPM Course, или другое название...',
    type: 'text',
    contextKey: 'business.name',
    required: true,
    block: 'business',
  },
  {
    id: 'b2',
    text: 'Опишите ваш бизнес в 2-3 предложениях: что это, для кого, какую проблему решает',
    placeholder: 'Например: Наставничество по маркетингу для специалистов и владельцев бизнеса. Помогаю настроить рекламу и привлечь клиентов...',
    type: 'textarea',
    contextKey: 'business.description',
    required: true,
    block: 'business',
  },
  {
    id: 'b3',
    text: 'К какой маркетинговой нише относится ваш бизнес?',
    placeholder: 'Например: digital-маркетинг, обучение маркетингу, наставничество для предпринимателей...',
    type: 'text',
    contextKey: 'business.niche',
    block: 'business',
  },
  {
    id: 'b4',
    text: 'Какие основные продукты/услуги вы продаёте? Перечислите через запятую',
    placeholder: 'Например: Курс по таргету VK, Наставничество 1-на-1, Марафон по рекламе, Групповая программа...',
    type: 'tags',
    contextKey: 'products.main',
    required: true,
    block: 'business',
  },
  {
    id: 'b5',
    text: 'Есть ли второстепенные продукты/услуги? (доп. материалы, шаблоны, чаты поддержки)',
    placeholder: 'Например: Шаблоны креативов, Чат выпускников, Разовые консультации, Гайды...',
    type: 'tags',
    contextKey: 'products.secondary',
    block: 'business',
  },
  {
    id: 'b6',
    text: 'Кто производит контент/продукты? Вы сами, команда, приглашённые эксперты?',
    placeholder: 'Например: Я сам веду обучение + привлекаю практикующих маркетологов для гостевых уроков',
    type: 'text',
    contextKey: 'products.producer',
    block: 'business',
  },
  {
    id: 'b7',
    text: 'Кто ваша целевая аудитория? Опишите 2-3 основных сегмента',
    placeholder: 'Например: Начинающие маркетологи, Таргетологи для повышения квалификации, Владельцы малого бизнеса...',
    type: 'tags',
    contextKey: 'audience.targetSegments',
    required: true,
    block: 'business',
  },
  {
    id: 'b8',
    text: 'Какие задачи/проблемы решает ваш клиент, покупая у вас?',
    placeholder: 'Например: Настроить рекламу и получить клиентов, Освоить новую профессию, Масштабировать бизнес...',
    type: 'tags',
    contextKey: 'audience.tasks',
    block: 'business',
  },
  {
    id: 'b9',
    text: 'В какой географии работает ваш бизнес? (страны, города, или «весь мир онлайн»)',
    placeholder: 'Например: Россия, СНГ, весь мир (онлайн-формат)',
    type: 'tags',
    contextKey: 'geography.regions',
    required: true,
    block: 'business',
  },
  {
    id: 'b10',
    text: 'Как устроены цены? (диапазон, модель: подписка, разовая покупка, пакеты)',
    placeholder: 'Например: Базовый курс 15000₽, Наставничество 50000₽, подписка 3000₽/мес',
    type: 'textarea',
    contextKey: 'pricing.model',
    block: 'business',
  },
  {
    id: 'b11',
    text: 'Как клиент заказывает и получает доступ? (процесс покупки)',
    placeholder: 'Например: Пишет в сообщения VK → оплачивает → получает доступ к платформе обучения',
    type: 'textarea',
    contextKey: 'salesProcess.orderProcess',
    block: 'business',
  },
  {
    id: 'b12',
    text: 'Какие способы оплаты принимаете?',
    placeholder: 'Например: Карта, СБП, рассрочка, оплата через VK Pay',
    type: 'tags',
    contextKey: 'salesProcess.paymentMethods',
    block: 'business',
  },
  {
    id: 'b13',
    text: 'Через какие каналы к вам приходят клиенты?',
    placeholder: 'Например: VK таргет, рефералы от учеников, YouTube, сарафанное радио, личные выступления',
    type: 'tags',
    contextKey: 'channels.acquisition',
    required: true,
    block: 'business',
  },
  {
    id: 'b14',
    text: 'Где ещё вы представлены в интернете? (сайты, соцсети, платформы)',
    placeholder: 'Например: Личная страница VK, Telegram-канал, YouTube, GetCourse',
    type: 'tags',
    contextKey: 'channels.onlinePresence',
    block: 'business',
  },
  {
    id: 'b15',
    text: 'В чём главные преимущества и ограничения вашего бизнеса?',
    placeholder: 'Преимущества: практический опыт, кейсы, поддержка... Ограничения: только онлайн, ограниченный набор в наставничество...',
    type: 'textarea',
    contextKey: 'advantages',
    block: 'business',
  },
];

const competitorQuestions: Question[] = [
  {
    id: 'c1',
    text: 'Кого вы уже считаете своими конкурентами? Перечислите известных',
    placeholder: 'Например: Школа X, Блогер Y, Курс Z, Агентство W...',
    type: 'tags',
    contextKey: 'competitors.known',
    required: true,
    block: 'competitors',
  },
  {
    id: 'c2',
    text: 'Какие особенности вашего бизнеса ОБЯЗАТЕЛЬНО должны быть у конкурентов, чтобы их учитывать?',
    placeholder: 'Например: Обучение маркетингу, онлайн-формат, русскоязычный контент, цена от 5000₽',
    type: 'tags',
    contextKey: 'searchCriteria.mustHaveFeatures',
    required: true,
    block: 'competitors',
  },
  {
    id: 'c3',
    text: 'Где и по каким критериям нужно искать конкурентов? (платформы, ключевые слова)',
    placeholder: 'Например: VK сообщества, GetCourse, YouTube каналы, Telegram, Instagram',
    type: 'tags',
    contextKey: 'searchCriteria.searchPlatforms',
    block: 'competitors',
  },
  {
    id: 'c4',
    text: 'Сколько конкурентов нужно найти? (примерное количество)',
    placeholder: 'Например: 10-15 прямых, 5-10 косвенных, 5-10 за внимание',
    type: 'text',
    contextKey: 'searchCriteria.count',
    block: 'competitors',
  },
  {
    id: 'c5',
    text: 'Какую географию учитывать при поиске конкурентов?',
    placeholder: 'Например: Только Россия, Россия и СНГ, весь русскоязычный мир',
    type: 'text',
    contextKey: 'searchCriteria.geography',
    block: 'competitors',
  },
  {
    id: 'c6',
    text: 'Какой минимальный размер аудитории сообщества VK допустим для конкурента?',
    placeholder: 'Например: от 1000 подписчиков, от 5000 подписчиков',
    type: 'text',
    contextKey: 'searchCriteria.vkAudienceLimit',
    block: 'competitors',
  },
  {
    id: 'c7',
    text: 'Насколько свежими должны быть публикации у конкурента? (чтобы считать его активным)',
    placeholder: 'Например: публикации не старше 3 месяцев, хотя бы 1 пост в неделю',
    type: 'text',
    contextKey: 'searchCriteria.publicationFreshness',
    block: 'competitors',
  },
  {
    id: 'c8',
    text: 'Кого обязательно включить в список? (конкретные бизнесы, если есть)',
    placeholder: 'Например: Обязательно включить «Церебро» и «Школу X»',
    type: 'tags',
    contextKey: 'searchCriteria.include',
    block: 'competitors',
  },
  {
    id: 'c9',
    text: 'Кого исключить? (кто точно НЕ конкурент)',
    placeholder: 'Например: Офлайн-агентства без обучения, бесплатные YouTube-уроки без структуры',
    type: 'tags',
    contextKey: 'searchCriteria.exclude',
    block: 'competitors',
  },
  {
    id: 'c10',
    text: 'Какие поисковые запросы использовать для нахождения конкурентов?',
    placeholder: 'Например: "курсы маркетинга онлайн", "обучение таргету VK", "наставничество по рекламе"',
    type: 'tags',
    contextKey: 'searchCriteria.searchQueries',
    block: 'competitors',
  },
];

export function InterviewFlow({ context, updateContext, answers, updateAnswers, onComplete, block }: Props) {
  const questions = block === 'business' ? businessQuestions : competitorQuestions;
  const [currentQ, setCurrentQ] = useState(0);
  const [localValue, setLocalValue] = useState('');

  const question = questions[currentQ];
  const isLast = currentQ === questions.length - 1;
  const progress = ((currentQ + 1) / questions.length) * 100;

  const handleNext = () => {
    saveAnswer(question.contextKey, localValue);
    
    if (isLast) {
      applyAllAnswers();
      onComplete();
    } else {
      setCurrentQ(currentQ + 1);
      const nextQ = questions[currentQ + 1];
      setLocalValue(answers[nextQ.contextKey] || '');
    }
  };

  const handlePrev = () => {
    saveAnswer(question.contextKey, localValue);
    if (currentQ > 0) {
      setCurrentQ(currentQ - 1);
      const prevQ = questions[currentQ - 1];
      setLocalValue(answers[prevQ.contextKey] || '');
    }
  };

  const handleSkip = () => {
    if (currentQ < questions.length - 1) {
      saveAnswer(question.contextKey, localValue);
      setCurrentQ(currentQ + 1);
      const nextQ = questions[currentQ + 1];
      setLocalValue(answers[nextQ.contextKey] || '');
    }
  };

  const saveAnswer = (key: string, value: string) => {
    updateAnswers(key, value);
  };

  const applyAllAnswers = () => {
    const updates: Partial<BusinessContext> = {};
    
    const allAnswers = { ...answers, [question.contextKey]: localValue };
    
    if (block === 'business') {
      updates.business = {
        name: allAnswers['business.name'] || context.business.name,
        niche: allAnswers['business.niche'] || context.business.niche,
        positioning: context.business.positioning,
        description: allAnswers['business.description'] || context.business.description,
      };
      updates.products = {
        main: parseTags(allAnswers['products.main']),
        secondary: parseTags(allAnswers['products.secondary']),
        assortmentWidth: context.products.assortmentWidth,
        producer: allAnswers['products.producer'] || context.products.producer,
        productionType: context.products.productionType,
      };
      updates.audience = {
        targetSegments: parseTags(allAnswers['audience.targetSegments']),
        tasks: parseTags(allAnswers['audience.tasks']),
        painPoints: context.audience.painPoints,
      };
      updates.geography = {
        regions: parseTags(allAnswers['geography.regions']),
        format: context.geography.format,
      };
      updates.pricing = {
        model: allAnswers['pricing.model'] || context.pricing.model,
        range: context.pricing.range,
      };
      updates.salesProcess = {
        orderProcess: allAnswers['salesProcess.orderProcess'] || context.salesProcess.orderProcess,
        paymentMethods: parseTags(allAnswers['salesProcess.paymentMethods']),
        deliveryOrAccess: context.salesProcess.deliveryOrAccess,
        salesFormat: context.salesProcess.salesFormat,
      };
      updates.channels = {
        acquisition: parseTags(allAnswers['channels.acquisition']),
        onlinePresence: parseTags(allAnswers['channels.onlinePresence']),
      };
      
      const advText = allAnswers['advantages'] || '';
      const parts = advText.split(/[.;]/).map(s => s.trim()).filter(Boolean);
      updates.advantages = parts.length > 0 ? parts : context.advantages;
    } else {
      updates.competitors = {
        known: parseTags(allAnswers['competitors.known']),
        directDefinition: context.competitors.directDefinition,
        indirectDefinition: context.competitors.indirectDefinition,
        attentionDefinition: context.competitors.attentionDefinition,
      };
      updates.searchCriteria = {
        mustHaveFeatures: parseTags(allAnswers['searchCriteria.mustHaveFeatures']),
        searchPlatforms: parseTags(allAnswers['searchCriteria.searchPlatforms']),
        count: allAnswers['searchCriteria.count'] || context.searchCriteria.count,
        geography: allAnswers['searchCriteria.geography'] || context.searchCriteria.geography,
        vkAudienceLimit: allAnswers['searchCriteria.vkAudienceLimit'] || context.searchCriteria.vkAudienceLimit,
        publicationFreshness: allAnswers['searchCriteria.publicationFreshness'] || context.searchCriteria.publicationFreshness,
        include: parseTags(allAnswers['searchCriteria.include']),
        exclude: parseTags(allAnswers['searchCriteria.exclude']),
        searchQueries: parseTags(allAnswers['searchCriteria.searchQueries']),
      };
    }
    
    updateContext(updates);
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">
            {block === 'business' ? '🎤 Интервью о бизнесе' : '🎯 Вопросы о конкурентах'}
          </h2>
          <span className="text-sm text-slate-400">
            {currentQ + 1} / {questions.length}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 bg-slate-700 rounded-full mb-8 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Question */}
        <div className="mb-8">
          <label className="block text-lg font-medium mb-4">{question.text}</label>
          
          {question.type === 'text' && (
            <input
              type="text"
              value={localValue}
              onChange={(e) => setLocalValue(e.target.value)}
              placeholder={question.placeholder}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors"
            />
          )}
          
          {question.type === 'textarea' && (
            <textarea
              value={localValue}
              onChange={(e) => setLocalValue(e.target.value)}
              placeholder={question.placeholder}
              rows={4}
              className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors resize-none"
            />
          )}
          
          {question.type === 'tags' && (
            <div>
              <textarea
                value={localValue}
                onChange={(e) => setLocalValue(e.target.value)}
                placeholder={question.placeholder}
                rows={3}
                className="w-full px-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors resize-none"
              />
              <p className="text-xs text-slate-500 mt-2">Разделяйте запятой или переносом строки</p>
              {localValue && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {parseTags(localValue).map((tag, i) => (
                    <span key={i} className="px-3 py-1 bg-blue-500/20 border border-blue-500/30 rounded-full text-sm text-blue-300">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex gap-3">
          {currentQ > 0 && (
            <button
              onClick={handlePrev}
              className="px-6 py-3 bg-slate-700 border border-slate-600 rounded-xl font-medium hover:bg-slate-600 transition-colors"
            >
              ← Назад
            </button>
          )}
          {!question.required && !isLast && (
            <button
              onClick={handleSkip}
              className="px-6 py-3 bg-slate-700/50 border border-slate-600/50 rounded-xl font-medium text-slate-400 hover:bg-slate-700 transition-colors"
            >
              Пропустить →
            </button>
          )}
          <button
            onClick={handleNext}
            className="flex-1 py-3 px-6 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl font-medium hover:opacity-90 transition-opacity"
          >
            {isLast ? (block === 'business' ? 'Завершить интервью →' : 'Завершить →') : 'Далее →'}
          </button>
        </div>

        {/* Skip indicator */}
        {!question.required && (
          <p className="text-xs text-slate-500 mt-4 text-center">
            Можно пропустить, оставив пустым
          </p>
        )}
      </div>
    </div>
  );
}

function parseTags(value: string): string[] {
  if (!value) return [];
  return value
    .split(/[,;\n]+/)
    .map(s => s.trim())
    .filter(Boolean);
}
