from api.db.user import User
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
    await sample_user.add_vacation(
        start=date.today(), end=date.today() + timedelta(days=7)
    )
    assert len(sample_user.vacations) == 1
    assert await sample_user.get_remaining_vacation() == 15
    await sample_user.add_vacation(
        start=date.today(), end=date(day=5, month=1, year=date.today().year + 1)
    )
    await sample_user.refresh()
    assert len(sample_user.vacations) == 3
