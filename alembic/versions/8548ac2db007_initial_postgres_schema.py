"""initial postgres schema

Revision ID: 8548ac2db007
Revises:
Create Date: 2026-06-25 17:37:56.258201

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8548ac2db007"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. INDEPENDENT LOOKUP TABLES (No Foreign Keys)
    op.create_table(
        "governors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=False),
        sa.Column("name_ar", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "relationships_to_head",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=False),
        sa.Column("name_ar", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "shelter_quality",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=False),
        sa.Column("name_ar", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # 2. DEPENDENT LOOKUP TABLES
    op.create_table(
        "cities",
        sa.Column("governor_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=False),
        sa.Column("name_ar", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["governor_id"],
            ["governors.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "shelter_centers",
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=False),
        sa.Column("name_ar", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "shelter_block",
        sa.Column("shelter_center_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=False),
        sa.Column("name_ar", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["shelter_center_id"],
            ["shelter_centers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # 3. USERS
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "SUPERADMIN",
                "MANAGER",
                "BLOCK_HEAD",
                "FAMILY",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("block_id", sa.Integer(), nullable=True),
        sa.Column("shelter_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["shelter_block.id"],
        ),
        sa.ForeignKeyConstraint(
            ["shelter_id"],
            ["shelter_centers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_block_id"), "users", ["block_id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # 4. FAMILIES (Notice we REMOVED the foreign keys to `members` here to break the circular dependency)
    op.create_table(
        "families",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("head_id", sa.Integer(), nullable=True),
        sa.Column("spouse_id", sa.Integer(), nullable=True),
        sa.Column(
            "residency_status",
            sa.Enum("DISPLACED", "RESIDENT", name="residencystatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("female_headed", sa.Boolean(), nullable=False),
        sa.Column("child_headed", sa.Boolean(), nullable=False),
        sa.Column("primary_phone_number", sa.String(), nullable=False),
        sa.Column("secondary_phone_number", sa.String(), nullable=True),
        sa.Column("original_governor_id", sa.Integer(), nullable=False),
        sa.Column("original_city_id", sa.Integer(), nullable=False),
        sa.Column("current_governor_id", sa.Integer(), nullable=False),
        sa.Column("current_city_id", sa.Integer(), nullable=False),
        sa.Column("current_shelter_center_id", sa.Integer(), nullable=False),
        sa.Column("shelter_block_id", sa.Integer(), nullable=False),
        sa.Column(
            "housing_type",
            sa.Enum(
                "TENT",
                "HOUSE",
                "CARAVAN",
                "GARAGE",
                "ROOM",
                "SCHOOL",
                "OTHER",
                name="housingtype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("shelter_quality_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["current_city_id"],
            ["cities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["current_governor_id"],
            ["governors.id"],
        ),
        sa.ForeignKeyConstraint(
            ["current_shelter_center_id"],
            ["shelter_centers.id"],
        ),
        # ❌ REMOVED: sa.ForeignKeyConstraint(['head_id'], ['members.id'], ),
        sa.ForeignKeyConstraint(
            ["original_city_id"],
            ["cities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["original_governor_id"],
            ["governors.id"],
        ),
        sa.ForeignKeyConstraint(
            ["shelter_block_id"],
            ["shelter_block.id"],
        ),
        sa.ForeignKeyConstraint(
            ["shelter_quality_id"],
            ["shelter_quality.id"],
        ),
        # ❌ REMOVED: sa.ForeignKeyConstraint(['spouse_id'], ['members.id'], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_families_head_id"), "families", ["head_id"], unique=True)
    op.create_index(op.f("ix_families_id"), "families", ["id"], unique=False)
    op.create_index(
        op.f("ix_families_is_active"), "families", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_families_spouse_id"), "families", ["spouse_id"], unique=False
    )

    # 5. MEMBERS (Now that `families` exists, we can safely reference it)
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column(
            "gender",
            sa.Enum("MALE", "FEMALE", name="gender", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "marital_status",
            sa.Enum(
                "MARRIED",
                "DIVORCED",
                "WIDOWED",
                "SINGLE",
                "SECOND_WIFE",
                "ABANDONED",
                name="maritalstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("relationship_to_head_id", sa.Integer(), nullable=False),
        sa.Column("has_chronic_disease", sa.Boolean(), nullable=False),
        sa.Column("injured", sa.Boolean(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("pregnant", sa.Boolean(), nullable=False),
        sa.Column("breastfeeding", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["families.id"],
        ),
        sa.ForeignKeyConstraint(
            ["relationship_to_head_id"],
            ["relationships_to_head.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_members_id"), "members", ["id"], unique=False)

    # 6. ADD THE DEFERRED FOREIGN KEYS (Linking families back to members)
    op.create_foreign_key(
        "fk_families_head_id", "families", "members", ["head_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_families_spouse_id", "families", "members", ["spouse_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop the deferred foreign keys first
    op.drop_constraint("fk_families_head_id", "families", type_="foreignkey")
    op.drop_constraint("fk_families_spouse_id", "families", type_="foreignkey")

    # 2. Drop tables in reverse order of creation
    op.drop_index(op.f("ix_members_id"), table_name="members")
    op.drop_table("members")

    op.drop_index(op.f("ix_families_spouse_id"), table_name="families")
    op.drop_index(op.f("ix_families_is_active"), table_name="families")
    op.drop_index(op.f("ix_families_id"), table_name="families")
    op.drop_index(op.f("ix_families_head_id"), table_name="families")
    op.drop_table("families")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_block_id"), table_name="users")
    op.drop_table("users")

    op.drop_table("shelter_block")
    op.drop_table("shelter_centers")
    op.drop_table("cities")
    op.drop_table("shelter_quality")
    op.drop_table("relationships_to_head")
    op.drop_table("governors")
