from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class SignInRequest(CamelModel):
    usernameOrEmail: Optional[str] = None
    username_or_email: Optional[str] = None
    password: str

    @property
    def identifier(self) -> str:
        return (self.usernameOrEmail or self.username_or_email or "").strip()


class SignUpRequest(CamelModel):
    username: str
    email: EmailStr
    password: str
    fullName: str
    role: str = "citizen"
    tenantId: Optional[str] = "GWMC"
    assignedZone: Optional[str] = None
    assignedWard: Optional[str] = None

class UserProfileResponse(CamelModel):
    id: str
    username: str
    email: str
    fullName: str
    role: str
    tenantId: str
    assignedModules: List[str]
    assignedZone: Optional[str] = None
    assignedWard: Optional[str] = None

class AuthResponse(CamelModel):
    accessToken: str
    tokenType: str = "bearer"
    user: UserProfileResponse

class ModuleMetadata(CamelModel):
    code: str
    name: str
    domain: str
    phase: int
    icon: str
    description: str
    hasAccess: bool = False
    route: str

