from enum import StrEnum


class UserRole(StrEnum):
    SUPERADMIN = "SUPERADMIN"
    MANAGER = "MANAGER"
    BLOCK_HEAD = "BLOCK_HEAD"
    FAMILY = "FAMILY"


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
    ABANDONED = "abandoned"  # مهجورة


class HousingType(StrEnum):
    TENT = "tent"
    HOUSE = "house"
    CARAVAN = "caravan"
    GARAGE = "garage"
    ROOM = "room"
    SCHOOL = "school"
    OTHER = "other"


class UpdateRequestType(StrEnum):
    ADD_MEMBER = "ADD_MEMBER"
    CHANGE_HEAD = "CHANGE_HEAD"
    UPDATE_FAMILY_INFO = "UPDATE_FAMILY_INFO"
    UPDATE_MEMBER_INFO = "UPDATE_MEMBER_INFO"


class UpdateRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
