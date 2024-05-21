import enum


class UniqueValueEnumMeta(enum.EnumMeta):
    def __new__(metacls, clsname, bases, classdict):
        # Extract values from classdict before creating the Enum class
        values = [value for key, value in classdict.items() if not key.startswith("_")]

        # Check for duplicates
        if len(values) != len(set(values)):
            duplicates = [item for item in set(values) if values.count(item) > 1]
            raise ValueError(f"duplicate values found in enum {clsname}: {duplicates}")

        return super().__new__(metacls, clsname, bases, classdict)


class UniqueValueEnum(enum.Enum, metaclass=UniqueValueEnumMeta): ...
