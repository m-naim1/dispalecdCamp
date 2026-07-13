from pydantic import BaseModel, ConfigDict


class LookupBase(BaseModel):
    code: str
    name_en: str
    name_ar: str


class LookupCreate(LookupBase):
    pass


class LookupUpdate(BaseModel):
    code: str | None = None
    name_en: str | None = None
    name_ar: str | None = None
    is_active: bool | None = None


class LookupResponse(LookupBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class CityCreate(LookupCreate):
    governor_id: int


class CityResponse(LookupResponse):
    governor_id: int


class ShelterCenterCreate(LookupCreate):
    city_id: int


class ShelterCenterResponse(LookupResponse):
    city_id: int


class ShelterBlockCreate(LookupCreate):
    shelter_center_id: int


class ShelterBlockResponse(LookupResponse):
    shelter_center_id: int
