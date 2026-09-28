export interface BusinessContext {
  status: 'draft' | 'confirmed';
  confirmationDate: string | null;
  sourceUrl: string;
  sourceAccessible: boolean;
  sourceParseError: string;
  business: {
    name: string | null;
    niche: string | null;
    positioning: string | null;
    description: string | null;
  };
  products: {
    main: string[];
    secondary: string[];
    assortmentWidth: string | null;
    producer: string | null;
    productionType: string | null;
  };
  audience: {
    targetSegments: string[];
    tasks: string[];
    painPoints: string[];
  };
  geography: {
    regions: string[];
    format: string | null;
  };
  pricing: {
    model: string | null;
    range: string | null;
  };
  salesProcess: {
    orderProcess: string | null;
    paymentMethods: string[];
    deliveryOrAccess: string | null;
    salesFormat: string | null;
  };
  channels: {
    acquisition: string[];
    onlinePresence: string[];
  };
  advantages: string[];
  limitations: string[];
  keyFeatures: string[];
  competitors: {
    known: string[];
    directDefinition: string;
    indirectDefinition: string;
    attentionDefinition: string;
  };
  searchCriteria: {
    mustHaveFeatures: string[];
    searchPlatforms: string[];
    count: string | null;
    geography: string | null;
    vkAudienceLimit: string | null;
    publicationFreshness: string | null;
    include: string[];
    exclude: string[];
    searchQueries: string[];
  };
  gaps: string[];
}

export interface InterviewAnswers {
  [key: string]: string;
}

export interface Question {
  id: string;
  text: string;
  placeholder: string;
  type: 'text' | 'textarea' | 'tags' | 'select';
  options?: string[];
  contextKey: string;
  required?: boolean;
  block: 'business' | 'competitors';
}
