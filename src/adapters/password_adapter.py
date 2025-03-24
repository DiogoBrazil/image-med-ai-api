from passlib.hash import argon2


class PasswordAdapter:
    @staticmethod
    async def hash_password(password: str) -> str:
        return argon2.hash(password)

    @staticmethod
    async def verify_password(password: str, hash_password: str) -> bool:
        return argon2.verify(password, hash_password)
