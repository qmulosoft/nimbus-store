from abc import ABC, ABCMeta, abstractmethod
import typing


class Field:
    """ Represents a single field on a data model class """
    def __init__(self, description: str, _type, writable=True, name=None):
        self._name = name
        self._desc = description
        self._type = _type
        self._writable = writable
        self._value = self._type()

    @property
    def name(self):
        """ The name of the database table column, if different from the class field name """
        return self._name

    @property
    def desc(self):
        return self._desc

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = self._type(new_value)

    @property
    def writable(self):
        return self._writable

    def copy(self):
        return Field(self.desc, self._type, name=self.name, writable=self.writable)


class ModelMeta(ABCMeta):
    """ Metaclass that builds model attributes based on fields dictionary """
    def __init__(cls, name, bases, clsdict):
        super().__init__(name, bases, clsdict)
        if len(cls.mro()) > 2:  # Don't try to treat Model, just subclasses of Model
            for name, value in cls.fields.items():
                if value.name is None:
                    value._name = name
                setattr(cls, name, value)


class Model(metaclass=ModelMeta):

    _writable_cols = None
    _cols = None

    @property
    @abstractmethod
    def fields(cls) -> typing.Dict[str, Field]:
        """ The names of the database columns, and their respective configuration """

    @property
    @abstractmethod
    def table_name(cls) -> str:
        """The name of the database table corresponding to this model"""

    @classmethod
    def writable_cols(cls) -> typing.List[str]:
        if cls._writable_cols is None:
            cls._writable_cols = [v.name for k, v in cls.fields.items() if v.writable]
        return cls._writable_cols

    @classmethod
    def cols(cls) -> typing.List[str]:
        if cls._cols is None:
            cls._cols = [v.name for k, v in cls.fields.items()]
        return cls._cols

    def __init__(self, **values):
        for field_name, field in self.fields.items():
            instance_field = field.copy()
            if field_name in values:
                instance_field.value = values[field_name]
            setattr(self, field_name, instance_field)

    @classmethod
    def from_db_row(cls, row):
        values = {}
        for name, value in zip(cls.cols(), row):
            if name in cls.fields:
                values[name] = value
            else:
                for key, field in cls.fields.items():
                    if field.name == name:
                        values[key] = value
                        break
        return cls(**values)

    @classmethod
    def from_dict(cls, dict):
        # TODO validate and make sensible errors, e.g can't set non-writable fields
        return cls(**dict)

    def to_dict(self) -> dict:
        """ Render the model object into a flat dictionary for marshalling to json, etc. """
        d = {}
        for name in self.fields:
            d[name] = getattr(self, name).value
        return d

    # SQL formatting/generation methods. They are escaped and should be sanitized
    @classmethod
    def insert_columns(cls, *extra_fields: Field):
        extra = [field.name for field in extra_fields]
        return ", ".join(f"[{each}]" for each in cls.writable_cols() + extra)

    @classmethod
    def select_columns(cls):
        return ", ".join(f"[{each}]" for each in cls.cols())

    @classmethod
    def db_columns(cls):
        return ", ".join(f"[{name}]" for name, field in cls.fields.items())

    @classmethod
    def find_by_id_statement(cls) -> str:
        return f"SELECT {cls.select_columns()} FROM [{cls.table_name}] WHERE {cls.id.name} = ?"

    @classmethod
    def find_statement(cls, field: Field) -> str:
        return f"SELECT {cls.select_columns()} FROM [{cls.table_name}] WHERE {field.name} = ?"

    def insert_statement(self, *extra_fields: Field) -> typing.Tuple[str, list]:
        """ Returns a formatted, simple INSERT INTO VALUES statement and parameters
        By default, only inserts writable fields. If you need to set a non-writable field
        then provide the fields as variadic parameters. """
        placeholders = ",".join(["?"] * (len(self.writable_cols()) + len(extra_fields)))
        stmt = f"INSERT INTO {self.table_name}({self.insert_columns(*extra_fields)})"\
               f" VALUES ({placeholders})"
        values = [getattr(self, name).value for name, value in self.fields.items() if value.writable]
        return stmt, values + [field.value for field in extra_fields]
