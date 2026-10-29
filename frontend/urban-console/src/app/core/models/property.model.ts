export interface Owner {
  id?: string;
  fullName: string;
  full_name?: string;
  mobileNumber: string;
  mobile_number?: string;
  email?: string;
  ownershipShare: number;
  ownership_share?: number;
}

export interface PropertyUnit {
  id?: string;
  ptin: string;
  unitNumber: string;
  unit_number?: string;
  floorNumber: number;
  floor_number?: number;
  usageCategory: string;
  usage_category?: string;
  carpetAreaSqft: number;
  carpet_area_sqft?: number;
  builtUpAreaSqft: number;
  built_up_area_sqft?: number;
  occupancyType: string;
  occupancy_type?: string;
  annualRentalValue?: number;
  annual_rental_value?: number;
  currentDemandAmount: number;
  current_demand_amount?: number;
  taxStatus: 'PAID' | 'DUE' | 'ARREARS' | 'EXEMPT';
  tax_status?: 'PAID' | 'DUE' | 'ARREARS' | 'EXEMPT';
  owners?: Owner[];
}

export interface Building {
  id?: string;
  buildingName?: string;
  building_name?: string;
  buildingType: string;
  building_type?: string;
  totalFloors: number;
  total_floors?: number;
  constructionYear?: number;
  construction_year?: number;
  buildingPermissionNo?: string;
  building_permission_no?: string;
  units?: PropertyUnit[];
}

export interface PropertySummary {
  id: string;
  ulpin: string;
  surveyNumber: string;
  survey_number?: string;
  address: string;
  wardNumber?: number;
  ward_number?: number;
  wardName?: string;
  ward_name?: string;
  buildingType?: string;
  building_type?: string;
  totalUnits: number;
  total_units?: number;
  ptin?: string;
  ownerName?: string;
  owner_name?: string;
  usageCategory?: string;
  usage_category?: string;
  currentDemandAmount: number;
  current_demand_amount?: number;
  taxStatus: 'PAID' | 'DUE' | 'ARREARS' | 'EXEMPT';
  tax_status?: 'PAID' | 'DUE' | 'ARREARS' | 'EXEMPT';
}

export interface PropertyDetail {
  id: string;
  tenantId: string;
  tenant_id?: string;
  ulpin: string;
  surveyNumber: string;
  survey_number?: string;
  plotNumber?: string;
  plot_number?: string;
  totalAreaSqyd: number;
  total_area_sqyd?: number;
  wardId: string;
  ward_id?: string;
  wardName?: string;
  ward_name?: string;
  wardNumber?: number;
  ward_number?: number;
  localityName?: string;
  locality_name?: string;
  latitude?: number;
  longitude?: number;
  address: string;
  buildings: Building[];
}

export interface Ward {
  id: string;
  zoneId: string;
  zone_id?: string;
  wardNumber: number;
  ward_number?: number;
  wardName: string;
  ward_name?: string;
  councilorName?: string;
  councilor_name?: string;
  totalProperties: number;
  total_properties?: number;
}

export interface DashboardStats {
  totalParcels: number;
  total_parcels?: number;
  totalUnits: number;
  total_units?: number;
  totalDemand: number;
  total_demand?: number;
  totalCollected: number;
  total_collected?: number;
  residentialCount: number;
  residential_count?: number;
  commercialCount: number;
  commercial_count?: number;
  wardCount: number;
  ward_count?: number;
}

export interface TenantInfo {
  tenantId: string;
  name: string;
  stateCode: string;
  district: string;
  createdAt?: string;
  totalParcels?: number;
  totalWards?: number;
}

