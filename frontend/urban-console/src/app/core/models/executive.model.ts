export interface ExecutiveDataStatus {
  dataAvailable?: boolean;
  unavailableReason?: string | null;
  unavailableMetrics?: string[];
}

export interface StateBenchmark {
  stateCode: string;
  stateName: string;
  ulbCount: number;
  parcels: number;
  demand: number;
  collected: number;
  efficiency: number;
  grievanceSla: number;
  digitalAdoption: number;
  status: string;
}

export interface MacroTrendPoint {
  period: string;
  revenueCr: number;
  parcelsK: number;
  grievances: number;
  digitalPct: number;
}

export interface GlobalOverviewStats {
  totalRegisteredParcels: number;
  totalRevenueCollected: number;
  totalOutstandingRevenue: number;
  activeGrievances: number;
  resolvedGrievances: number;
  grievanceSlaCompliance: number;
  totalRegisteredCitizens: number;
  digitalServiceAdoptionPercentage: number;
  activeStateTenants: number;
  activeUlbTenants: number;
  stateBenchmarks: StateBenchmark[];
  macroTrends: MacroTrendPoint[];
}

export interface RevenueBreakdownItem {
  name: string;
  demand: number;
  collected: number;
  arrears: number;
  efficiency: number;
  sharePct: number;
}

export interface MonthlyRevenueTrend {
  month: string;
  demandCr: number;
  collectedCr: number;
  efficiency: number;
}

export interface RevenueAnalyticsStats {
  totalDemandTarget: number;
  totalCollection: number;
  arrearsCollected: number;
  currentYearCollected: number;
  collectionEfficiency: number;
  outstandingBalance: number;
  breakdown: RevenueBreakdownItem[];
  monthlyTrend: MonthlyRevenueTrend[];
}

export interface SurveyDistributionItem {
  method: string;
  count: number;
  pct: number;
  status: string;
}

export interface PropertyCategoryBreakdown {
  category: string;
  count: number;
  pct: number;
  revenueContribution: string;
}

export interface ParcelStatisticsStats {
  totalParcels: number;
  verifiedParcels: number;
  unverifiedParcels: number;
  gisMappedParcels: number;
  unmappedParcels: number;
  residentialParcels: number;
  commercialParcels: number;
  vacantParcels: number;
  gisCoveragePct: number;
  surveyDistribution: SurveyDistributionItem[];
  categoryBreakdown: PropertyCategoryBreakdown[];
}

export interface GrievanceCategoryItem {
  category: string;
  total: number;
  resolved: number;
  overdue: number;
  slaPct: number;
  avgDays: number;
}

export interface GrievanceDepartmentItem {
  department: string;
  active: number;
  resolved: number;
  slaCompliance: number;
}

export interface GrievancePriorityItem {
  priority: string;
  count: number;
  resolvedPct: number;
  slaHours: string;
}

export interface GrievanceOverviewStats {
  totalGrievances: number;
  openGrievances: number;
  resolvedGrievances: number;
  overdueGrievances: number;
  averageResolutionTimeDays: number;
  slaCompliancePercentage: number;
  categoryBreakdown: GrievanceCategoryItem[];
  departmentBreakdown: GrievanceDepartmentItem[];
  priorityBreakdown: GrievancePriorityItem[];
}

export interface CitizenChannelItem {
  channel: string;
  users: number;
  txVolume: number;
  sharePct: number;
  rating: string;
}

export interface CitizenServiceItem {
  service: string;
  onlineTransactions: number;
  digitalPct: number;
  growthYoY: string;
}

export interface CitizenTrendPoint {
  month: string;
  digitalPct: number;
  activeUsersM: number;
  onlineTxM: number;
}

export interface CitizenAdoptionStats {
  registeredCitizens: number;
  activeDigitalUsers: number;
  onlineApplications: number;
  onlinePayments: number;
  mobileAppAdoption: number;
  digitalTransactionPercentage: number;
  channelBreakdown: CitizenChannelItem[];
  serviceAdoption: CitizenServiceItem[];
  monthlyAdoptionTrend: CitizenTrendPoint[];
}

export interface StateFilterOption {
  code: string;
  name: string;
  stateCode: string;
}

export interface UlbFilterOption {
  code: string;
  name: string;
  stateCode: string;
}

export interface RevenueModuleOption {
  code: string;
  name: string;
}

export interface ExecutiveFilterOptions {
  states: StateFilterOption[];
  ulbs: UlbFilterOption[];
  departments: string[];
  revenueModules: RevenueModuleOption[];
  revenueCategories: string[];
  propertyCategories: string[];
  grievanceCategories: string[];
  digitalServices: string[];
  registrationChannels: string[];
  financialYears: string[];
  geographicScopes: string[];
  aggregationLevels: string[];
  ulbCategories?: string[];
  rankingMethods?: string[];
  swachhCategories?: string[];
  swachhSources?: string[];
}

// ==============================================================================
// ADM-A02: STATE & CITY BENCHMARKING MATRIX MODELS
// ==============================================================================

export interface StateComparisonBenchmark {
  rank: number;
  stateCode: string;
  stateName: string;
  compositeScore: number;
  demand: number;
  collected: number;
  recoveryPct: number;
  slaCompliancePct: number;
  avgResolutionHours: number;
  digitalAdoptionPct: number;
  swachhRank: number;
  swachhScore: number;
  ulbCount: number;
  parcels: number;
  performanceTier: string;
  radar: {
    revenue: number;
    sla: number;
    digital: number;
    swachh: number;
    governance: number;
  };
}

export interface StateComparisonResponse {
  benchmarkName: string;
  financialYear: string;
  benchmarkPeriod: string;
  comparisonMethod: string;
  rankingMetric: string;
  notes?: string;
  benchmarks: StateComparisonBenchmark[];
  summary: {
    topPerformer: string;
    topScore: number;
    medianScore: number;
    avgRecoveryPct: number;
    avgSlaCompliance: number;
    evaluatedStatesCount: number;
  };
}

export interface CityComparisonBenchmark {
  rank: number;
  ulbCode: string;
  ulbName: string;
  stateCode: string;
  category: string;
  district: string;
  population: number;
  parcels: number;
  compositeScore: number;
  dcbDemand: number;
  dcbCollection: number;
  dcbBalance: number;
  dcbRecoveryPct: number;
  grievancesTotal: number;
  grievanceSlaPct: number;
  avgResolutionDays: number;
  swachhNationalRank: number;
  swachhScore: number;
  gfcStarRating: string;
  digitalPenetrationPct: number;
  growthTrajectory: string;
}

export interface CityComparisonResponse {
  stateTenant: string;
  financialYear: string;
  comparisonPeriod: string;
  rankingMethod: string;
  notes?: string;
  benchmarks: CityComparisonBenchmark[];
  summary: {
    bestUlb: string;
    topScore: number;
    avgRecoveryPct: number;
    avgSlaCompliance: number;
    totalParcelsCovered: number;
    totalCities: number;
  };
}

export interface DcbModuleItem {
  moduleCode: string;
  moduleName: string;
  demand: number;
  collection: number;
  balance: number;
  recoveryPct: number;
  trend: string;
}

export interface DcbTenantItem {
  tenantCode: string;
  tenantName: string;
  demand: number;
  collection: number;
  balance: number;
  recoveryPct: number;
  status: string;
}

export interface DcbMonthlyItem {
  month: string;
  demand: number;
  collection: number;
  recoveryPct: number;
}

export interface DcbRecoveryResponse {
  financialYear: string;
  totalDemand: number;
  totalCollection: number;
  totalBalance: number;
  recoveryPercentage: number;
  moduleBreakdown: DcbModuleItem[];
  tenantBreakdown: DcbTenantItem[];
  monthlyTrend: DcbMonthlyItem[];
}

export interface SlaDepartmentMatrixItem {
  department: string;
  totalCases: number;
  casesWithin: number;
  casesBeyond: number;
  compliancePct: number;
  avgHours: number;
  breachRisk: string;
}

export interface SlaServiceCategoryItem {
  category: string;
  slaHours: number;
  total: number;
  compliancePct: number;
  status: string;
}

export interface SlaBreachItem {
  ticketId: string;
  citizen: string;
  category: string;
  ulb: string;
  elapsedHours: number;
  targetHours: number;
  status: string;
}

export interface SlaComplianceResponse {
  reportingPeriod: string;
  slaTargetHours: number;
  totalCases: number;
  casesWithinSla: number;
  casesBeyondSla: number;
  averageResolutionTime: number;
  slaCompliancePercentage: number;
  departmentMatrix: SlaDepartmentMatrixItem[];
  serviceCategoryMatrix: SlaServiceCategoryItem[];
  criticalBreaches: SlaBreachItem[];
}

export interface SwachhNationalItem {
  rank: number;
  ulbName: string;
  stateName: string;
  populationCat: string;
  totalScore: number;
  gfcStar: string;
  waterPlus: string;
  doorToDoorPct: number;
  sourceSegregationPct: number;
  processingCapacityPct: number;
  verifiedDate: string;
}

export interface SwachhStateItem {
  stateRank: number;
  stateName: string;
  avgCityScore: number;
  cleanCitiesCount: number;
  topCity: string;
  status: string;
}

export interface SwachhRankingsResponse {
  assessmentYear: string;
  assessmentCycle: string;
  rankingCategory: string;
  externalRankingSource: string;
  dataVerificationStatus: string;
  verifiedOfficialNotice: string;
  nationalRankings: SwachhNationalItem[];
  statePerformance: SwachhStateItem[];
  indicatorScores: Record<string, number>;
}

// ==============================================================================
// ADM-A03: CONSOLIDATED FINANCIAL LEDGER MODELS
// ==============================================================================

export interface SchemeGrantBreakdown {
  schemeCode: string;
  schemeName: string;
  authority: string;
  sanctioned: number;
  released: number;
  allocated: number;
  utilised: number;
  unutilised: number;
  utilisationPct: number;
  status: string;
}

export interface StateGrantBreakdown {
  stateName: string;
  sanctioned: number;
  released: number;
  utilised: number;
  utilisationPct: number;
  status: string;
}

export interface GrantsOverviewStats {
  totalSanctionedGrants: number;
  totalReleasedAmount: number;
  totalAllocatedAmount: number;
  totalUtilisedAmount: number;
  unutilisedBalance: number;
  utilisationPercentage: number;
  schemeBreakdown: SchemeGrantBreakdown[];
  stateBreakdown: StateGrantBreakdown[];
}

export interface GrantAllocationItem {
  id: string;
  grantRef: string;
  grantScheme: string;
  fundingAuthority: string;
  financialYear: string;
  sanctionOrderNo: string;
  sanctionOrderDate: string;
  stateTenant: string;
  targetUlb: string;
  sanctionedAmount: number;
  releasedAmount: number;
  allocationAmount: number;
  releaseDate: string;
  deadline?: string;
  grantPurpose: string;
  sanctionDoc: string;
  allocationRemarks?: string;
  approvalAuthority: string;
  status: string;
}

export interface GrantAllocationCreate {
  grantScheme: string;
  fundingAuthority: string;
  financialYear: string;
  sanctionOrderNo: string;
  sanctionOrderDate: string;
  stateTenant: string;
  targetUlb?: string;
  sanctionedAmount: number;
  releasedAmount: number;
  allocationAmount: number;
  releaseDate?: string;
  deadline?: string;
  grantPurpose: string;
  sanctionDoc?: string;
  allocationRemarks?: string;
  approvalAuthority: string;
}

export interface GrantAllocationResponse {
  allocations: GrantAllocationItem[];
  summary: {
    totalAllocations: number;
    totalAllocatedSum: number;
    totalReleasedSum: number;
    activeSchemesCount: number;
  };
}

export interface FinancialReceiptItem {
  category: string;
  amount: number;
  sharePct: number;
  type: string;
}

export interface FinancialExpenditureItem {
  category: string;
  amount: number;
  sharePct: number;
  type: string;
}

export interface AccountHeadSummaryItem {
  code: string;
  head: string;
  budget: number;
  actuals: number;
  utilPct: number;
}

export interface FinancialSummaryStats {
  openingBalance: number;
  totalReceipts: number;
  totalExpenditure: number;
  closingBalance: number;
  totalAssets: number;
  totalLiabilities: number;
  revenueSurplusDeficit: number;
  receiptsBreakdown: FinancialReceiptItem[];
  expenditureBreakdown: FinancialExpenditureItem[];
  accountHeadSummary: AccountHeadSummaryItem[];
}

export interface LedgerTransactionItem {
  id: string;
  date: string;
  ulb: string;
  voucher: string;
  accountHead: string;
  debit: number;
  credit: number;
  balance: number;
  status: string;
}

export interface TenantLedgerResponse {
  totalTransactions: number;
  totalDebit: number;
  totalCredit: number;
  netBalance: number;
  transactions: LedgerTransactionItem[];
}

export interface ReconciliationItem {
  id: string;
  txnRef: string;
  date: string;
  sourceAmount: number;
  targetAmount: number;
  variance: number;
  matchStatus: string;
  utr: string;
  remarks: string;
}

export interface ReconciliationResponse {
  reconciliationName: string;
  financialYear: string;
  stateTenant: string;
  reconciliationType: string;
  sourceLedger: string;
  targetLedger: string;
  matchedTransactions: number;
  unmatchedTransactions: number;
  matchRatePct: number;
  debitDifference: number;
  creditDifference: number;
  reconciliationStatus: string;
  completionDate: string;
  reconciliationItems: ReconciliationItem[];
}



