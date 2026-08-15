from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.User import User as UserModel
from app.schemas.user import AddUser

class UserRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)


    async def GetuserById(self, user_id: str):
            result = await self.db.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one_or_none()
            return user


    async def GetUserByUsername(self, username: str):
            result = await self.db.execute(select(UserModel).where(UserModel.username == username))
            user = result.scalar_one_or_none()
        

    async def AddUser(self, user_data: UserModel):
            user = UserModel(**user_data.dict())
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user