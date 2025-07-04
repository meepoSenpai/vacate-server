from api.db.user import User
from api.db.vacation import NotEnoughVacation, NoMoreVacation
from datetime import date, timedelta

import pytest


async def test_create():
    user = await User.create(username="User", password="password", mail="test@mail.com")
    found_user = await User.from_id(user.id)
    assert user.id == found_user.id


async def test_create_duplicate_user():
    await User.create(username="User", password="password", mail="test@mail.com")
    with pytest.raises(Exception):
        await User.create(username="User", password="password", mail="test@mail.com")


async def test_add_vacation_and_remaining_vacation(sample_user: User):
    with pytest.raises(NotEnoughVacation):
        await sample_user.request_vacation(
            start=date(day=1, month=1, year=2001), end=date(day=31, month=12, year=2001)
        )
    await sample_user.request_vacation(
        start=date(day=1, month=1, year=2001), end=date(day=1, month=1, year=2001) + timedelta(days=6)
    )
    assert len(sample_user.vacations) == 1
    assert await sample_user.get_remaining_vacation(2001) == 20
    for vacation in sample_user.vacations:
        await vacation.confirm()
    assert await sample_user.get_remaining_vacation(2001) == 16
    await sample_user.request_vacation(
        start=date(day=31, month=12, year=2002), end=date(day=31, month=12, year=2002) + timedelta(days=1)
    )
    await sample_user.refresh()
    assert len(sample_user.vacations) == 3

    await sample_user.request_vacation(
        start=date(day=8, month=1, year=2001), end=date(day=30, month=1, year=2001)
    )
    for vacation in sample_user.vacations:
        await vacation.confirm()
    with pytest.raises(NoMoreVacation):
        await sample_user.request_vacation(
            start=date(day=31, month=1, year=2001)
        )
