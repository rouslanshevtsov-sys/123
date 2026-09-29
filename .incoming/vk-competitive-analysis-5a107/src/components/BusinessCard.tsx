import { type BusinessContext } from '../types';

interface Props {
  context: BusinessContext;
  onConfirm: () => void;
  onEdit: () => void;
}

export function BusinessCard({ context, onConfirm, onEdit }: Props) {
  const sections = [
    {
      title: '🏢 Бизнес',
      items: [
        { label: 'Название', value: context.business.name },
        { label: 'Ниша', value: context.business.niche },
        { label: 'Позиционирование', value: context.business.positioning },
        { label: 'Описание', value: context.business.description },
      ],
    },
    {
      title: '📦 Продукты',
      items: [
        { label: 'Основные', value: context.products.main.join(', ') || null },
        { label: 'Второстепенные', value: context.products.secondary.join(', ') || null },
        { label: 'Широта ассортимента', value: context.products.assortmentWidth },
        { label: 'Производитель', value: context.products.producer },
        { label: 'Тип производства', value: context.products.productionType },
      ],
    },
    {
      title: '👥 Аудитория',
      items: [
        { label: 'Сегменты', value: context.audience.targetSegments.join(', ') || null },
        { label: 'Задачи клиентов', value: context.audience.tasks.join(', ') || null },
        { label: 'Боли', value: context.audience.painPoints.join(', ') || null },
      ],
    },
    {
      title: '🌍 География',
      items: [
        { label: 'Регионы', value: context.geography.regions.join(', ') || null },
        { label: 'Формат', value: context.geography.format },
      ],
    },
    {
      title: '💰 Цены',
      items: [
        { label: 'Модель', value: context.pricing.model },
        { label: 'Диапазон', value: context.pricing.range },
      ],
    },
    {
      title: '🛒 Процесс продаж',
      items: [
        { label: 'Процесс заказа', value: context.salesProcess.orderProcess },
        { label: 'Способы оплаты', value: context.salesProcess.paymentMethods.join(', ') || null },
        { label: 'Доступ/доставка', value: context.salesProcess.deliveryOrAccess },
        { label: 'Формат продаж', value: context.salesProcess.salesFormat },
      ],
    },
    {
      title: '📢 Каналы',
      items: [
        { label: 'Привлечение', value: context.channels.acquisition.join(', ') || null },
        { label: 'Присутствие онлайн', value: context.channels.onlinePresence.join(', ') || null },
      ],
    },
    {
      title: '⚡ Преимущества и ограничения',
      items: [
        { label: 'Преимущества', value: context.advantages.join('; ') || null },
        { label: 'Ограничения', value: context.limitations.join('; ') || null },
      ],
    },
    {
      title: '🔑 Ключевые особенности',
      items: [
        { label: 'Особенности', value: context.keyFeatures.join('; ') || null },
      ],
    },
    {
      title: '🎯 Конкуренты',
      items: [
        { label: 'Известные', value: context.competitors.known.join(', ') || null },
      ],
    },
    {
      title: '🔍 Критерии поиска конкурентов',
      items: [
        { label: 'Обязательные особенности', value: context.searchCriteria.mustHaveFeatures.join(', ') || null },
        { label: 'Платформы поиска', value: context.searchCriteria.searchPlatforms.join(', ') || null },
        { label: 'Количество', value: context.searchCriteria.count },
        { label: 'География поиска', value: context.searchCriteria.geography },
        { label: 'Мин. аудитория VK', value: context.searchCriteria.vkAudienceLimit },
        { label: 'Свежесть публикаций', value: context.searchCriteria.publicationFreshness },
        { label: 'Включить', value: context.searchCriteria.include.join(', ') || null },
        { label: 'Исключить', value: context.searchCriteria.exclude.join(', ') || null },
        { label: 'Поисковые запросы', value: context.searchCriteria.searchQueries.join(', ') || null },
      ],
    },
  ];

  const filledCount = sections.reduce((acc, section) => {
    return acc + section.items.filter(item => item.value && item.value !== 'не указано').length;
  }, 0);
  const totalCount = sections.reduce((acc, section) => acc + section.items.length, 0);
  const fillPercent = Math.round((filledCount / totalCount) * 100);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">📋 Карточка бизнеса</h2>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Draft — ожидает подтверждения
          </span>
        </div>

        {/* Fill progress */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Заполненность карточки</span>
            <span className="text-sm font-medium text-white">{fillPercent}%</span>
          </div>
          <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${
                fillPercent >= 80 ? 'bg-green-500' : fillPercent >= 50 ? 'bg-blue-500' : 'bg-amber-500'
              }`}
              style={{ width: `${fillPercent}%` }}
            />
          </div>
        </div>

        <p className="text-slate-400 mb-6">
          Проверьте собранную информацию ниже. Если что-то неверно — вернитесь к редактированию.
        </p>

        <div className="space-y-6 mb-8">
          {sections.map((section, si) => {
            const sectionFilled = section.items.filter(item => item.value && item.value !== 'не указано').length;
            const sectionTotal = section.items.length;
            
            return (
              <div key={si} className="p-5 rounded-xl bg-slate-700/20 border border-slate-600/20">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-lg">{section.title}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    sectionFilled === sectionTotal 
                      ? 'bg-green-500/20 text-green-300' 
                      : sectionFilled > 0 
                        ? 'bg-blue-500/20 text-blue-300' 
                        : 'bg-slate-600/30 text-slate-500'
                  }`}>
                    {sectionFilled}/{sectionTotal}
                  </span>
                </div>
                <div className="space-y-3">
                  {section.items.map((item, ii) => (
                    <div key={ii} className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-4">
                      <span className="text-sm text-slate-400 sm:w-48 flex-shrink-0">{item.label}:</span>
                      <span className={`text-sm ${item.value ? 'text-white' : 'text-slate-500 italic'}`}>
                        {item.value || 'не указано'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Classification rules */}
        <div className="p-5 rounded-xl bg-slate-700/20 border border-slate-600/20 mb-6">
          <h3 className="font-semibold text-lg mb-3">📐 Правила классификации конкурентов</h3>
          <div className="space-y-3 text-sm">
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-red-300 font-medium">Прямые конкуренты</p>
              <p className="text-red-300/70">Продают тот же продукт той же аудитории. Ассортимент может быть шире (и обязательно должен включать большинство позиций), но основная специализация должна совпадать.</p>
            </div>
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <p className="text-amber-300 font-medium">Косвенные конкуренты</p>
              <p className="text-amber-300/70">Продают часть ассортимента или похожий ассортимент.</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <p className="text-blue-300 font-medium">Конкуренты за внимание</p>
              <p className="text-blue-300/70">Бизнесы, которые могут отвлечь внимание клиента, закрывая схожую потребность. Условный клиент может совершить покупку одновременно или в дополнение к покупке у вас.</p>
            </div>
          </div>
        </div>

        {/* Source note */}
        <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 mb-6">
          <p className="text-sm text-blue-300">
            <strong>Примечание:</strong> Источник <code className="bg-slate-700 px-1 rounded">vk.ru/shpmcourse</code> не был доступен для прямого парсинга. 
            Информация получена из интервью и косвенных источников (поиск). Статус: <strong>draft</strong>.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onEdit}
            className="px-6 py-3 bg-slate-700 border border-slate-600 rounded-xl font-medium hover:bg-slate-600 transition-colors"
          >
            ✏️ Редактировать
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-3 px-6 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl font-medium hover:opacity-90 transition-opacity"
          >
            ✓ Подтвердить карточку
          </button>
        </div>
      </div>
    </div>
  );
}
