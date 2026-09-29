import { type BusinessContext } from '../types';

export function generateMarkdown(context: BusinessContext): string {
  const lines: string[] = [];
  
  lines.push(`# Карточка бизнеса: ${context.business.name || '(не указано)'}`);
  lines.push('');
  lines.push(`**Статус:** ${context.status === 'confirmed' ? '✅ Подтверждено' : '📝 Draft'}`);
  lines.push(`**Дата подтверждения:** ${context.confirmationDate || '—'}`);
  lines.push(`**Источник:** ${context.sourceUrl}`);
  lines.push(`**Доступность источника:** ${context.sourceAccessible ? 'Доступен' : 'Недоступен (защита капчей)'}`);
  lines.push('');
  lines.push('---');
  lines.push('');
  
  // Business
  lines.push('## 🏢 Описание бизнеса');
  lines.push('');
  lines.push(`**Название:** ${context.business.name || '⚠️ Не указано'}`);
  lines.push(`**Ниша:** ${context.business.niche || '⚠️ Не указано'}`);
  lines.push(`**Позиционирование:** ${context.business.positioning || '⚠️ Не указано'}`);
  lines.push(`**Описание:** ${context.business.description || '⚠️ Не указано'}`);
  lines.push('');
  
  // Products
  lines.push('## 📦 Продукты и ассортимент');
  lines.push('');
  lines.push('### Основные продукты:');
  if (context.products.main.length > 0) {
    context.products.main.forEach(p => lines.push(`- ${p}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  lines.push('### Второстепенные продукты:');
  if (context.products.secondary.length > 0) {
    context.products.secondary.forEach(p => lines.push(`- ${p}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  lines.push(`**Широта ассортимента:** ${context.products.assortmentWidth || '⚠️ Не указано'}`);
  lines.push(`**Производитель/поставщик:** ${context.products.producer || '⚠️ Не указано'}`);
  lines.push(`**Тип производства:** ${context.products.productionType || '⚠️ Не указано'}`);
  lines.push('');
  
  // Audience
  lines.push('## 👥 Аудитория');
  lines.push('');
  lines.push('### Целевые сегменты:');
  if (context.audience.targetSegments.length > 0) {
    context.audience.targetSegments.forEach(s => lines.push(`- ${s}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  lines.push('### Задачи клиентов:');
  if (context.audience.tasks.length > 0) {
    context.audience.tasks.forEach(t => lines.push(`- ${t}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  lines.push('### Боли:');
  if (context.audience.painPoints.length > 0) {
    context.audience.painPoints.forEach(p => lines.push(`- ${p}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  
  // Geography
  lines.push('## 🌍 География');
  lines.push('');
  lines.push(`**Регионы:** ${context.geography.regions.length > 0 ? context.geography.regions.join(', ') : '⚠️ Не указаны'}`);
  lines.push(`**Формат:** ${context.geography.format || '⚠️ Не указано'}`);
  lines.push('');
  
  // Pricing
  lines.push('## 💰 Цены');
  lines.push('');
  lines.push(`**Модель:** ${context.pricing.model || '⚠️ Не указано'}`);
  lines.push(`**Диапазон:** ${context.pricing.range || '⚠️ Не указано'}`);
  lines.push('');
  
  // Sales process
  lines.push('## 🛒 Процесс продаж');
  lines.push('');
  lines.push(`**Порядок заказа:** ${context.salesProcess.orderProcess || '⚠️ Не указано'}`);
  lines.push(`**Способы оплаты:** ${context.salesProcess.paymentMethods.length > 0 ? context.salesProcess.paymentMethods.join(', ') : '⚠️ Не указаны'}`);
  lines.push(`**Доставка/доступ:** ${context.salesProcess.deliveryOrAccess || '⚠️ Не указано'}`);
  lines.push(`**Формат продаж:** ${context.salesProcess.salesFormat || '⚠️ Не указано'}`);
  lines.push('');
  
  // Channels
  lines.push('## 📢 Каналы');
  lines.push('');
  lines.push('### Привлечение клиентов:');
  if (context.channels.acquisition.length > 0) {
    context.channels.acquisition.forEach(c => lines.push(`- ${c}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  lines.push('### Присутствие в интернете:');
  if (context.channels.onlinePresence.length > 0) {
    context.channels.onlinePresence.forEach(c => lines.push(`- ${c}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  
  // Advantages
  lines.push('## ⚡ Преимущества и ограничения');
  lines.push('');
  lines.push('### Преимущества:');
  if (context.advantages.length > 0) {
    context.advantages.forEach(a => lines.push(`- ${a}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  lines.push('### Ограничения:');
  if (context.limitations.length > 0) {
    context.limitations.forEach(l => lines.push(`- ${l}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  
  // Key features
  if (context.keyFeatures.length > 0) {
    lines.push('## 🔑 Ключевые особенности');
    lines.push('');
    context.keyFeatures.forEach(f => lines.push(`- ${f}`));
    lines.push('');
  }
  
  // Competitors
  lines.push('## 🎯 Конкуренты');
  lines.push('');
  lines.push('### Известные конкуренты:');
  if (context.competitors.known.length > 0) {
    context.competitors.known.forEach(c => lines.push(`- ${c}`));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  lines.push('### Правила классификации:');
  lines.push('');
  lines.push('**Прямые конкуренты** — продают тот же продукт той же аудитории. У прямого конкурента ассортимент может быть шире (и обязательно должен включать большинство позиций), но основная специализация должна совпадать.');
  lines.push('');
  lines.push('**Косвенные конкуренты** — продают часть ассортимента или похожий ассортимент.');
  lines.push('');
  lines.push('**Конкуренты за внимание** — бизнесы, которые могут отвлечь внимание клиента, закрывая схожую потребность.');
  lines.push('');
  
  // Search criteria
  lines.push('## 🔍 Критерии поиска конкурентов');
  lines.push('');
  lines.push(`**Обязательные особенности:** ${context.searchCriteria.mustHaveFeatures.length > 0 ? context.searchCriteria.mustHaveFeatures.join(', ') : '⚠️ Не указаны'}`);
  lines.push(`**Платформы поиска:** ${context.searchCriteria.searchPlatforms.length > 0 ? context.searchCriteria.searchPlatforms.join(', ') : '⚠️ Не указаны'}`);
  lines.push(`**Количество:** ${context.searchCriteria.count || '⚠️ Не указано'}`);
  lines.push(`**География:** ${context.searchCriteria.geography || '⚠️ Не указано'}`);
  lines.push(`**Мин. аудитория VK:** ${context.searchCriteria.vkAudienceLimit || '⚠️ Не указано'}`);
  lines.push(`**Свежесть публикаций:** ${context.searchCriteria.publicationFreshness || '⚠️ Не указано'}`);
  lines.push('');
  lines.push('### Включить:');
  if (context.searchCriteria.include.length > 0) {
    context.searchCriteria.include.forEach(i => lines.push(`- ${i}`));
  } else {
    lines.push('- Не указано');
  }
  lines.push('');
  lines.push('### Исключить:');
  if (context.searchCriteria.exclude.length > 0) {
    context.searchCriteria.exclude.forEach(e => lines.push(`- ${e}`));
  } else {
    lines.push('- Не указано');
  }
  lines.push('');
  
  // Search queries
  lines.push('### Предполагаемые поисковые запросы:');
  if (context.searchCriteria.searchQueries.length > 0) {
    context.searchCriteria.searchQueries.forEach(q => lines.push(`- \`${q}\``));
  } else {
    lines.push('- ⚠️ Не указаны');
  }
  lines.push('');
  
  // Gaps
  lines.push('## ⚠️ Оставшиеся пробелы');
  lines.push('');
  const gaps = getGaps(context);
  if (gaps.length > 0) {
    gaps.forEach(g => lines.push(`- ${g}`));
  } else {
    lines.push('- Все основные поля заполнены');
  }
  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push(`*Файл сгенерирован: ${new Date().toISOString().split('T')[0]}*`);
  lines.push(`*Статус: ${context.status}*`);
  
  return lines.join('\n');
}

function getGaps(context: BusinessContext): string[] {
  const gaps: string[] = [];
  if (!context.business.name) gaps.push('Название бизнеса не указано');
  if (!context.business.niche) gaps.push('Маркетинговая ниша не определена');
  if (!context.business.description) gaps.push('Описание бизнеса отсутствует');
  if (context.products.main.length === 0) gaps.push('Основные продукты не перечислены');
  if (!context.products.producer) gaps.push('Не указано, кто производит/поставляет продукты');
  if (context.audience.targetSegments.length === 0) gaps.push('Целевые сегменты не определены');
  if (context.geography.regions.length === 0) gaps.push('География работы не указана');
  if (!context.pricing.model) gaps.push('Модель ценообразования не описана');
  if (!context.salesProcess.orderProcess) gaps.push('Процесс заказа не описан');
  if (context.channels.acquisition.length === 0) gaps.push('Каналы привлечения не указаны');
  if (context.advantages.length === 0) gaps.push('Преимущества не перечислены');
  if (context.competitors.known.length === 0) gaps.push('Известные конкуренты не указаны');
  if (!context.searchCriteria.count) gaps.push('Количество конкурентов для поиска не указано');
  return gaps;
}
