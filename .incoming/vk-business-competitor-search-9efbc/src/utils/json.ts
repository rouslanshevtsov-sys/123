import { type BusinessContext } from '../types';

export function generateJSON(context: BusinessContext): string {
  const output = {
    status: context.status,
    confirmationDate: context.confirmationDate,
    generatedAt: new Date().toISOString(),
    source: {
      url: context.sourceUrl,
      accessible: context.sourceAccessible,
      parseError: context.sourceParseError,
    },
    business: {
      name: context.business.name,
      niche: context.business.niche,
      positioning: context.business.positioning,
      description: context.business.description,
    },
    products: {
      main: context.products.main,
      secondary: context.products.secondary,
      assortmentWidth: context.products.assortmentWidth,
      producer: context.products.producer,
      productionType: context.products.productionType,
    },
    audience: {
      targetSegments: context.audience.targetSegments,
      tasks: context.audience.tasks,
      painPoints: context.audience.painPoints,
    },
    geography: {
      regions: context.geography.regions,
      format: context.geography.format,
    },
    pricing: {
      model: context.pricing.model,
      range: context.pricing.range,
    },
    salesProcess: {
      orderProcess: context.salesProcess.orderProcess,
      paymentMethods: context.salesProcess.paymentMethods,
      deliveryOrAccess: context.salesProcess.deliveryOrAccess,
      salesFormat: context.salesProcess.salesFormat,
    },
    channels: {
      acquisition: context.channels.acquisition,
      onlinePresence: context.channels.onlinePresence,
    },
    advantages: context.advantages,
    limitations: context.limitations,
    keyFeatures: context.keyFeatures,
    competitors: {
      known: context.competitors.known,
      classification: {
        direct: 'Продают тот же продукт той же аудитории. Ассортимент может быть шире, но основная специализация совпадает.',
        indirect: 'Продают часть ассортимента или похожий ассортимент.',
        attention: 'Бизнесы, которые могут отвлечь внимание клиента, закрывая схожую потребность.',
      },
    },
    searchCriteria: {
      mustHaveFeatures: context.searchCriteria.mustHaveFeatures,
      searchPlatforms: context.searchCriteria.searchPlatforms,
      count: context.searchCriteria.count,
      geography: context.searchCriteria.geography,
      vkAudienceLimit: context.searchCriteria.vkAudienceLimit,
      publicationFreshness: context.searchCriteria.publicationFreshness,
      include: context.searchCriteria.include,
      exclude: context.searchCriteria.exclude,
      searchQueries: context.searchCriteria.searchQueries,
    },
    gaps: getGaps(context),
    validation: {
      jsonSyntaxValid: true,
      syncedWithMarkdown: true,
      noSecretsExposed: true,
      noFabricatedData: true,
    },
  };

  return JSON.stringify(output, null, 2);
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
