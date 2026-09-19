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
          <div className="p-5 rounded-xl bg-slate-700/30 border border-slate-600/30">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-lg">🔗</span>
              <span className="font-medium text-blue-300">{context.sourceUrl}</span>
            </div>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></span>
              <span className="text-sm text-red-300">Недоступен для парсинга</span>
            </div>
            <p className="text-sm text-slate-400 mb-3">
              {context.sourceParseError}
            </p>
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <p className="text-sm text-amber-300">
                <strong>Рекомендация:</strong> В интервью ниже вы сможете вручную ввести всю информацию о бизнесе. 
                Если у вас есть скриншоты или текстовые описания со страницы VK, вы можете использовать их как подсказку.
              </p>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-700/30 border border-slate-600/30">
            <h3 className="font-medium mb-3 flex items-center gap-2">
              <span>📊</span> Что удалось определить из поиска
            </h3>
            <div className="space-y-2 text-sm text-slate-400">
              <p>• По идентификатору <code className="text-blue-300 bg-slate-700 px-1 rounded">shpmcourse</code> точных совпадений не найдено</p>
              <p>• Возможные интерпретации: ШПМ = Школа Парикмахерского Мастерства / Школа Профессионального Мастерства</p>
              <p>• Слово "course" указывает на образовательный формат</p>
            </div>
            <div className="mt-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <p className="text-sm text-blue-300">
                <strong>Предположение (не подтверждено):</strong> Возможно, это онлайн-школа или курсы парикмахерского мастерства. 
                Это будет уточнено в интервью.
              </p>
            </div>
          </div>

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
