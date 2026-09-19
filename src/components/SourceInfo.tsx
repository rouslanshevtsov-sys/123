import { type BusinessContext } from '../types';

interface Props {
  context: BusinessContext;
  onNext: () => void;
}

export function SourceInfo({ context, onNext }: Props) {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 p-8">
        <h2 className="text-2xl font-bold mb-6">📡 Анализ источников</h2>
        
        <div className="space-y-6 mb-8">
          {/* Source status */}
          <div className="p-5 rounded-xl bg-slate-700/30 border border-slate-600/30">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-lg">🔗</span>
              <span className="font-medium text-blue-300">{context.sourceUrl}</span>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></span>
              <span className="text-sm text-red-300">Недоступен для прямого парсинга</span>
            </div>
            <p className="text-sm text-slate-400 mb-3">
              {context.sourceParseError}
            </p>
          </div>

          {/* What we found */}
          <div className="p-5 rounded-xl bg-slate-700/30 border border-slate-600/30">
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <span>🔍</span> Что удалось установить из открытых источников
            </h3>
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                <p className="text-sm text-green-300 font-medium mb-2">✓ Установлено:</p>
                <ul className="text-sm text-green-300/80 space-y-1.5">
                  <li>• <strong>SHPM</strong> = <strong>Школа Практического Маркетинга</strong></li>
                  <li>• <strong>Автор/эксперт:</strong> Руслан Шевцов</li>
                  <li>• <strong>Связь:</strong> Церебро Таргет — сервис продвижения и рекламы бизнеса в VK</li>
                  <li>• <strong>Формат:</strong> наставничество, обучение маркетингу (тренинги, настройка, подсказки)</li>
                  <li>• <strong>Ниша:</strong> практический маркетинг / digital-маркетинг</li>
                  <li>• <strong>Платформа:</strong> ВКонтакте (сообщество shpmcourse)</li>
                </ul>
              </div>
              
              <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <p className="text-sm text-amber-300 font-medium mb-2">⚠️ Предполагается (не подтверждено):</p>
                <ul className="text-sm text-amber-300/80 space-y-1.5">
                  <li>• Аудитория: маркетологи, таргетологи, владельцы бизнеса</li>
                  <li>• Продукт: курс/наставничество по маркетингу и продвижению</li>
                  <li>• Формат обучения: онлайн, практические задания</li>
                  <li>• Возможная специализация: таргетированная реклама VK</li>
                </ul>
              </div>

              <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <p className="text-sm text-blue-300 font-medium mb-2">📋 Источники данных:</p>
                <ul className="text-sm text-blue-300/80 space-y-1">
                  <li>• Пост Руслана Шевцова: «"Маркетинга" — vk.com/shpmcourse. Там я буду тебя тренировать, настраивать, подсказывать»</li>
                  <li>• Pressfeed: «руководитель проекта Школа Практического Маркетинга»</li>
                  <li>• Связь с сообществом «Церебро Таргет | продвижение и реклама бизнеса»</li>
                </ul>
              </div>
            </div>
          </div>

          {/* VK API */}
          <div className="p-5 rounded-xl bg-slate-700/30 border border-slate-600/30">
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <span>⚙️</span> VK API
            </h3>
            <p className="text-sm text-slate-400 mb-3">
              Токен VK API не обнаружен в рабочей папке. Для автоматического парсинга сообщества потребуется:
            </p>
            <ul className="text-sm text-slate-400 space-y-1 list-disc list-inside">
              <li>Валидный токен доступа VK API</li>
              <li>ID сообщества (отрицательное число)</li>
              <li>Доступ к методам wall.get, groups.getById</li>
            </ul>
          </div>

          {/* Recommendation */}
          <div className="p-5 rounded-xl bg-purple-500/10 border border-purple-500/20">
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <span>💡</span> Рекомендация
            </h3>
            <p className="text-sm text-slate-300">
              В интервью ниже подтвердите или опровергните найденную информацию. 
              Укажите точное название бизнеса, продукты, цены и другие детали, 
              которые не удалось получить из открытых источников.
            </p>
          </div>
        </div>

        <button
          onClick={onNext}
          className="w-full py-3 px-6 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl font-medium hover:opacity-90 transition-opacity"
        >
          Перейти к интервью о бизнесе →
        </button>
      </div>
    </div>
  );
}
