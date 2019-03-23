import enum


class BaseIntEnum(int, enum.Enum):
    def __str__(self):
        return str(int(self))


class BaseStrEnum(str, enum.Enum):
    def __str__(self):
        return str(self.value)

