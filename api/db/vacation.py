from datetime import date, timedelta
from enum import Enum
from typing import Self
from sqlalchemy.exc import NoResultFound
from sqlmodel import Field, select

from api.db.database import Database
from .user import User
from sqlmodel.main import SQLModel, Relationship


class NoMoreVacation(Exception):
    pass


class NotEnoughVacation(Exception):
    pass


class ConfirmationStatus(Enum):
    PENDING=0
    CONFIRMED=1
    DENIED=2


class Vacation(SQLModel, table=True):
    hidden_id: int | None = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.hidden_id")
    start: date
    end: date
    confirmed: ConfirmationStatus = Field(default=ConfirmationStatus.PENDING)
    denial_reason: str | None = Field(default=None)


    user: User = Relationship(back_populates="vacations")

    @classmethod
    async def create(cls, user_id: int, start: date, end: date | None = None):
        if end is None:
            end = start
        async with Database.session() as session:
            user: User = await session.get(User, user_id)  # type: ignore[reportAssignmentType]
        await user.refresh()
        if await user.get_remaining_vacation(end.year) == 0:
            raise NoMoreVacation()
        if start.year != end.year:
            await cls.create(user_id, start, date(day=31, month=12, year=start.year))
            start = date(day=1, month=1, year=end.year)
        async with Database.session() as session:
            vacation = cls(hidden_id=None, user_id=user_id, start=start, end=end)
            session.add(vacation)
            await session.commit()
        await vacation.refresh()
        if vacation.duration > await user.get_remaining_vacation(vacation.start.year):
            async with Database.session() as session:
                vacation: Self = await session.get(cls, vacation.id)  # type: ignore[reportAssignmentType]
                await session.delete(vacation)
                await session.commit()
            raise NotEnoughVacation()

    @classmethod
    async def from_id(cls, id):
        async with Database.session() as session:
            if vacation := await session.get(cls, id):
                await session.refresh(vacation, attribute_names=["user"])
                return vacation
        raise NoResultFound(f"No user with ID {id} could be found.")

    @classmethod
    async def from_year_range(
        cls, user_id: int, start_year: int, end_year: int
    ) -> list[Self]:
        start_date, end_date = (
            date(day=1, month=1, year=start_year),
            date(day=31, month=12, year=end_year),
        )
        search_query = select(cls).where(
            cls.user_id == user_id and cls.start >= start_date and cls.end <= end_date
        )
        async with Database.session() as session:
            return list(await session.exec(search_query))

    @property
    def id(self) -> int:
        if self.hidden_id:
            return self.hidden_id
        raise AttributeError("Model created but not refreshed.")

    @property
    def duration(self):
        delta = (self.end - self.start).days
        days = []
        return len(
            [
                self.start + timedelta(days=x)
                for x in range(delta)
                if (self.start + timedelta(days=x)).weekday() < 5
                and self.start + timedelta(days=x) not in self.user.national_holidays
            ]
        )

    async def confirm(self):
        async with Database.session() as session:
            vacation: Vacation = await session.get(Vacation, self.id)  # type: ignore[reportAssignmentType]
            vacation.confirmed = ConfirmationStatus.CONFIRMED
            if vacation.denial_reason:
                vacation.denial_reason = None
            session.add(vacation)
            await session.commit()
        await self.refresh()

    async def deny(self, reason: str | None = None):
        async with Database.session() as session:
            vacation: Vacation = await session.get(Vacation, self.id)  # type: ignore[reportAssignmentType]
            vacation.confirmed = ConfirmationStatus.DENIED
            vacation.denial_reason = reason
            session.add(vacation)
            await session.commit()
        await self.refresh()

    async def refresh(self):
        if vacation := await Vacation.from_id(self.id):
            self.__dict__ = vacation.__dict__
