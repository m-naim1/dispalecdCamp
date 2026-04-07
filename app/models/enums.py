from enum import StrEnum


class UserRole(StrEnum):
    SUPERADMIN = "superadmin"
    MANAGER = "manager"
    BLOCK_HEAD = "block_head"
    FAMILY = "family"


class ResidencyStatus(StrEnum):
    DISPLACED = "displaced"
    RESIDENT = "resident"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class MaritalStatus(StrEnum):
    MARRIED = "married"  # متزوج/ة
    DIVORCED = "divorced"  # مطلق/ة
    WIDOWED = "widowed"  # ارمل/ة
    SINGLE = "single"  # اعزب/عزباء
    SECOND_WIFE = "second-wife"  # زوجة ثانية
    ABANDONED = "Abandoned"  # مهجورة


class HousingType(StrEnum):
    TENT = "tent"
    HOUSE = "house"
    CARAVAN = "caravan"
    GARAGE = "garage"
    ROOM = "room"
    SCHOOL = "school"
    OTHER = "other"
