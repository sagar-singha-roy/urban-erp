from typing import List, Optional, Any, Dict
from app.schemas.tenant import CamelModel, ApiResponse


class ExecutiveDataStatus(CamelModel):
    """Says which values have a real source. Null metrics mean not available, never zero."""
    dataAvailable: bool = True
    unavailableReason: Optional[str] = None
    unavailableMetrics: List[str] = []


# 1. Overview System-Generated Metrics
class GlobalOverviewStats(ExecutiveDataStatus):
    totalRegisteredParcels: Optional[int] = None
    totalRevenueCollected: Optional[float] = None
    totalOutstandingRevenue: Optional[float] = None
    activeGrievances: Optional[int] = None
    resolvedGrievances: Optional[int] = None
    grievanceSlaCompliance: Optional[float] = None
    totalRegisteredCitizens: Optional[int] = None
    digitalServiceAdoptionPercentage: Optional[float] = None
    activeStateTenants: Optional[int] = None
    activeUlbTenants: Optional[int] = None
    stateBenchmarks: List[Dict[str, Any]] = []
    macroTrends: List[Dict[str, Any]] = []


# 2. Revenue Analytics Schemas
class RevenueAnalyticsStats(ExecutiveDataStatus):
    totalDemandTarget: Optional[float] = None
    totalCollection: Optional[float] = None
    arrearsCollected: Optional[float] = None
    currentYearCollected: Optional[float] = None
    collectionEfficiency: Optional[float] = None
    outstandingBalance: Optional[float] = None
    breakdown: List[Dict[str, Any]] = []
    monthlyTrend: List[Dict[str, Any]] = []


# 3. Parcel Statistics Schemas
class ParcelStatisticsStats(ExecutiveDataStatus):
    totalParcels: Optional[int] = None
    verifiedParcels: Optional[int] = None
    unverifiedParcels: Optional[int] = None
    gisMappedParcels: Optional[int] = None
    unmappedParcels: Optional[int] = None
    residentialParcels: Optional[int] = None
    commercialParcels: Optional[int] = None
    vacantParcels: Optional[int] = None
    gisCoveragePct: Optional[float] = None
    surveyDistribution: List[Dict[str, Any]] = []
    categoryBreakdown: List[Dict[str, Any]] = []


# 4. Grievance Overview Schemas
class GrievanceOverviewStats(ExecutiveDataStatus):
    totalGrievances: Optional[int] = None
    openGrievances: Optional[int] = None
    resolvedGrievances: Optional[int] = None
    overdueGrievances: Optional[int] = None
    averageResolutionTimeDays: Optional[float] = None
    slaCompliancePercentage: Optional[float] = None
    categoryBreakdown: List[Dict[str, Any]] = []
    departmentBreakdown: List[Dict[str, Any]] = []
    priorityBreakdown: List[Dict[str, Any]] = []


# 5. Citizen Adoption Schemas
class CitizenAdoptionStats(ExecutiveDataStatus):
    registeredCitizens: Optional[int] = None
    activeDigitalUsers: Optional[int] = None
    onlineApplications: Optional[int] = None
    onlinePayments: Optional[int] = None
    mobileAppAdoption: Optional[int] = None
    digitalTransactionPercentage: Optional[float] = None
    channelBreakdown: List[Dict[str, Any]] = []
    serviceAdoption: List[Dict[str, Any]] = []
    monthlyAdoptionTrend: List[Dict[str, Any]] = []


# 6. Filter Options
class ExecutiveFilterOptions(CamelModel):
    states: List[Dict[str, Any]] = []
    ulbs: List[Dict[str, Any]] = []
    departments: List[str] = []
    revenueModules: List[Dict[str, str]] = []
    revenueCategories: List[str] = []
    propertyCategories: List[str] = []
    grievanceCategories: List[str] = []
    digitalServices: List[str] = []
    registrationChannels: List[str] = []
    financialYears: List[str] = []
    geographicScopes: List[str] = []
    aggregationLevels: List[str] = []
    ulbCategories: List[str] = []
    rankingMethods: List[str] = []
    swachhCategories: List[str] = []
    swachhSources: List[str] = []


# 7. ADM-A02: State Comparison Schemas
class StateComparisonResponse(ExecutiveDataStatus):
    benchmarkName: str = ""
    financialYear: str = ""
    benchmarkPeriod: str = ""
    comparisonMethod: str = ""
    rankingMetric: str = ""
    notes: Optional[str] = None
    benchmarks: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}


# 8. ADM-A02: City Comparison Schemas
class CityComparisonResponse(ExecutiveDataStatus):
    stateTenant: str = ""
    financialYear: str = ""
    comparisonPeriod: str = ""
    rankingMethod: str = ""
    notes: Optional[str] = None
    benchmarks: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}


# 9. ADM-A02: DCB Recovery Schemas (Demand, Collection, Balance)
class DcbRecoveryResponse(ExecutiveDataStatus):
    financialYear: str = ""
    totalDemand: Optional[float] = None
    totalCollection: Optional[float] = None
    totalBalance: Optional[float] = None
    recoveryPercentage: Optional[float] = None
    moduleBreakdown: List[Dict[str, Any]] = []
    tenantBreakdown: List[Dict[str, Any]] = []
    monthlyTrend: List[Dict[str, Any]] = []


# 10. ADM-A02: SLA Compliance Schemas
class SlaComplianceResponse(ExecutiveDataStatus):
    reportingPeriod: str = ""
    slaTargetHours: Optional[int] = None
    totalCases: Optional[int] = None
    casesWithinSla: Optional[int] = None
    casesBeyondSla: Optional[int] = None
    averageResolutionTime: Optional[float] = None
    slaCompliancePercentage: Optional[float] = None
    departmentMatrix: List[Dict[str, Any]] = []
    serviceCategoryMatrix: List[Dict[str, Any]] = []
    criticalBreaches: List[Dict[str, Any]] = []


# 11. ADM-A02: Swachh Rankings Schemas
class SwachhRankingsResponse(ExecutiveDataStatus):
    assessmentYear: str = ""
    assessmentCycle: str = ""
    rankingCategory: str = ""
    externalRankingSource: str = ""
    dataVerificationStatus: str = ""
    verifiedOfficialNotice: str = ""
    nationalRankings: List[Dict[str, Any]] = []
    statePerformance: List[Dict[str, Any]] = []
    indicatorScores: Dict[str, float] = {}


# ==============================================================================
# ADM-A03: CONSOLIDATED FINANCIAL LEDGER SCHEMAS
# ==============================================================================

# 12. Grants Overview Schemas
class GrantsOverviewStats(ExecutiveDataStatus):
    totalSanctionedGrants: Optional[float] = None
    totalReleasedAmount: Optional[float] = None
    totalAllocatedAmount: Optional[float] = None
    totalUtilisedAmount: Optional[float] = None
    unutilisedBalance: Optional[float] = None
    utilisationPercentage: Optional[float] = None
    schemeBreakdown: List[Dict[str, Any]] = []
    stateBreakdown: List[Dict[str, Any]] = []


# 13. Grant Allocation Schemas
class GrantAllocationItem(CamelModel):
    id: str = ""
    grantRef: str = ""
    grantScheme: str = ""
    fundingAuthority: str = ""
    financialYear: str = ""
    sanctionOrderNo: str = ""
    sanctionOrderDate: str = ""
    stateTenant: str = ""
    targetUlb: str = ""
    sanctionedAmount: float = 0.0
    releasedAmount: float = 0.0
    allocationAmount: float = 0.0
    releaseDate: str = ""
    deadline: Optional[str] = None
    grantPurpose: str = ""
    sanctionDoc: str = ""
    allocationRemarks: Optional[str] = None
    approvalAuthority: str = ""
    status: str = "Disbursed"


class GrantAllocationCreate(CamelModel):
    grantScheme: str
    fundingAuthority: str
    financialYear: str
    sanctionOrderNo: str
    sanctionOrderDate: str
    stateTenant: str
    targetUlb: Optional[str] = None
    sanctionedAmount: float
    releasedAmount: float
    allocationAmount: float
    releaseDate: Optional[str] = None
    deadline: Optional[str] = None
    grantPurpose: str
    sanctionDoc: Optional[str] = None
    allocationRemarks: Optional[str] = None
    approvalAuthority: str


class GrantAllocationResponse(ExecutiveDataStatus):
    allocations: List[GrantAllocationItem] = []
    summary: Dict[str, Any] = {}


# 14. Financial Summary Schemas
class FinancialSummaryStats(ExecutiveDataStatus):
    openingBalance: Optional[float] = None
    totalReceipts: Optional[float] = None
    totalExpenditure: Optional[float] = None
    closingBalance: Optional[float] = None
    totalAssets: Optional[float] = None
    totalLiabilities: Optional[float] = None
    revenueSurplusDeficit: Optional[float] = None
    receiptsBreakdown: List[Dict[str, Any]] = []
    expenditureBreakdown: List[Dict[str, Any]] = []
    accountHeadSummary: List[Dict[str, Any]] = []


# 15. Tenant-wise Ledger Schemas
class TenantLedgerResponse(ExecutiveDataStatus):
    totalTransactions: Optional[int] = None
    totalDebit: Optional[float] = None
    totalCredit: Optional[float] = None
    netBalance: Optional[float] = None
    transactions: List[Dict[str, Any]] = []


# 16. Reconciliation Schemas
class ReconciliationResponse(ExecutiveDataStatus):
    reconciliationName: str = ""
    financialYear: str = ""
    stateTenant: str = ""
    reconciliationType: str = ""
    sourceLedger: str = ""
    targetLedger: str = ""
    matchedTransactions: Optional[int] = None
    unmatchedTransactions: Optional[int] = None
    matchRatePct: Optional[float] = None
    debitDifference: Optional[float] = None
    creditDifference: Optional[float] = None
    reconciliationStatus: str = ""
    completionDate: str = ""
    reconciliationItems: List[Dict[str, Any]] = []



