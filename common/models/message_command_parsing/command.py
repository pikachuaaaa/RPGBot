import asyncio
from typing import Callable, get_type_hints, Any
from types import FunctionType
import inspect


class Command:
    _prefix: str
    _name: str
    _func: FunctionType
    _is_async: bool

    _context_arg_name: str

    _args_info: dict[str, type]
    _required_params: tuple[str]
    _required_params_len: int

    _not_required_params: tuple[str]
    _not_required_params_len: int
    _function_defaults: dict[str, Any]

    def __init__(self, prefix: str, name: str, context_arg_name: str = "ctx"):
        self._prefix = prefix
        self._name = name
        self._context_arg_name = context_arg_name

        self._args_info = {}

        # these parameters will begin as list, later they will be converted into tuples
        self._required_params = []
        self._required_params_len = 0

        self._not_required_params = []
        self._not_required_params_len = 0

        self._function_defaults = {}
        CREATED_COMMANDS.append(self)

    def __call__(self, func: FunctionType):
        self._func = func

        func_sig = inspect.signature(func)

        for param_name, param in func_sig.parameters.items():

            # check if there are present type annotations, if not then parameters are considered as of string types
            if param.annotation is inspect.Parameter.empty:
                self._args_info[param_name] = type("")
            else:
                self._args_info[param_name] = param.annotation

            # check for default values and sum up all required and non-required parameters
            if param.default is not inspect.Parameter.empty:
                self._function_defaults[param_name] = param.default
                self._not_required_params.append(param_name)
                self._not_required_params_len += 1
            else:
                self._required_params.append(param_name)
                self._required_params_len += 1

        self._required_params = tuple(self._required_params)
        self._not_required_params = tuple(self._not_required_params)

        self._is_async = inspect.isawaitable(func)

        return self

    def invoke(self, **kwargs):
        self._func(**kwargs)

    async def invoke_async(self, **kwargs):
        await self._func(**kwargs)

    #----- Command Properties ------#

    def is_async(self) -> bool:
        return self._is_async

    def name(self):
        return self._name

    def prefix(self):
        return self._prefix

    def context_arg_name(self):
        return self._context_arg_name

    def get_args_info(self) -> dict[str, type]:
        return self._args_info

    def get_parameter_default_value(self, param_name: str) -> Any | None:
        return self._function_defaults.get(param_name)

    def get_required_params_count(self) -> int:
        return self._required_params_len

    def get_non_required_params_count(self)->int:
        return self._not_required_params_len

CREATED_COMMANDS: list[Command] = []
