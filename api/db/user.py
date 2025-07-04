import bcrypt

from sqlalchemy.exc import NoResultFound
from sqlmodel.main import Field, SQLModel, Relationship
from .database import Database
from typing import Self
from datetime import date
from logging import getLogger
from holidays import HolidayBase, country_holidays

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vacation import Vacation

logger = getLogger(__name__)


class User(SQLModel, table=True):
    hidden_id: int | None = Field(primary_key=True)
    username: str = Field(unique=True)
    mail: str = Field(unique=True)
    passhash: str
    salt: str
    is_admin: bool = Field(default=False)
    vacation_amount: int = Field(default=20)
    country_code: str = Field(default="DE")
    join_date: date

    vacations: list["Vacation"] = Relationship(back_populates="user")

    @classmethod
    async def create(
        cls,
        username: str,
        mail: str,
        password: str,
        vacation_amount: int = 20,
        is_admin: bool = False,
        join_date: date | None = None,
    ) -> Self:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        async with Database.session() as session:
            user = cls(
                hidden_id=None,
                username=username,
                mail=mail,
                passhash=hashed_password,
                salt=salt.decode("utf-8"),
                vacation_amount=vacation_amount,
                is_admin=is_admin,
                join_date=join_date or date.today(),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user, attribute_names=["vacations"])
            return user

    @classmethod
    async def from_id(cls, id: int) -> Self:
        async with Database.session() as session:
            if user := await session.get(cls, id):
                await session.refresh(user, attribute_names=["vacations"])
                return user
        raise NoResultFound(f"No user with ID {id} could be found.")

    @property
    def id(self) -> int:
        if self.hidden_id:
            return self.hidden_id
        raise AttributeError("Model created but not refreshed.")

    @property
    def national_holidays(self) -> HolidayBase:
        return country_holidays(self.country_code)

    async def get_remaining_vacation(self, year: int | None = None):
        if year is None:
            year = date.today().year
        for vacation in self.vacations:
            await vacation.refresh()
        total_vacation = sum(
            [
                vacation.duration
                for vacation in self.vacations
                if vacation.start.year == year
                and vacation.confirmed
            ]
        )
        return self.vacation_amount - total_vacation

    async def add_vacation(self, start: date, end: date):
        from .vacation import Vacation

        await Vacation.create(user_id=self.id, start=start, end=end)
        await self.refresh()

    async def refresh(self):
        if user := await User.from_id(self.id):
            self.__dict__ = user.__dict__
