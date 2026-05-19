import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship




class Base(DeclarativeBase):
    pass


class UserRole(PyEnum):
    parent = "parent"
    child = "child"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=True
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="owner", cascade="all, delete-orphan"
    )
    is_active: Mapped[bool] = mapped_column(
    Boolean, server_default=text("true"), default=True, nullable=False
)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = {"schema": "app"}

    hardware_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    hardware_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ← nowe
    platform: Mapped[str] = mapped_column(
        String(50),
        server_default=text("'android'::character varying"),
        nullable=False,
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    owner: Mapped["User"] = relationship("User", back_populates="devices")
    pairing_codes: Mapped[list["PairingCode"]] = relationship(
        "PairingCode", back_populates="device", cascade="all, delete-orphan"
    )
    child_pairs: Mapped[list["DevicePair"]] = relationship(
        "DevicePair",
        foreign_keys="DevicePair.child_device_id",
        back_populates="child_device",
        cascade="all, delete-orphan",
    )
    guardian_pairs: Mapped[list["DevicePair"]] = relationship(
        "DevicePair",
        foreign_keys="DevicePair.guardian_device_id",
        back_populates="guardian_device",
        cascade="all, delete-orphan",
    )


class PairingCode(Base):
    __tablename__ = "pairing_codes"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    child_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    device: Mapped["Device"] = relationship("Device", back_populates="pairing_codes")


class DevicePair(Base):
    __tablename__ = "device_pairs"
    __table_args__ = (
        CheckConstraint(
            "child_device_id != guardian_device_id",
            name="ck_device_pairs_no_self_pair",
        ),
        {"schema": "app"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    guardian_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    child_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    paired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
    Boolean, server_default=text("true"), default=True, nullable=False
    )

    child_device: Mapped["Device"] = relationship(
        "Device", foreign_keys=[child_device_id], back_populates="child_pairs"
    )
    guardian_device: Mapped["Device"] = relationship(
        "Device", foreign_keys=[guardian_device_id], back_populates="guardian_pairs"
    )


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint(
            "battery_level >= 0 AND battery_level <= 100",
            name="locations_battery_level_check",
        ),
        {"schema": "app"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    accuracy_meters: Mapped[float | None] = mapped_column(
        Numeric(6, 1), nullable=True
    )
    battery_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    device: Mapped["Device"] = relationship("Device")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    sender_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    receiver_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app.devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    sender: Mapped["Device"] = relationship(
        "Device", foreign_keys=[sender_device_id]
    )
    receiver: Mapped["Device"] = relationship(
        "Device", foreign_keys=[receiver_device_id]
    )

class SosAlert(Base):
    __tablename__ = "sos_alerts"
    __table_args__ = {"schema": "app"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    child_device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app.devices.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    child_device: Mapped["Device"] = relationship("Device")