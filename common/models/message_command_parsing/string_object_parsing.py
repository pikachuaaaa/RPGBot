import re
from typing import get_type_hints, List, get_args, get_origin, Any

def parse_boolean(arg_expr: str)->bool:
    arg_expr = arg_expr.lower().strip()
    if arg_expr == 'true':
        return True
    elif arg_expr == 'false':
        return False
    else:
        raise SyntaxError(f"Cannot parse \"{arg_expr}\" as boolean value ")

def parse_string(arg_expr: str)->str:
    if arg_expr.startswith('\"') and arg_expr.endswith('\"'):
        return arg_expr[1:-1]
    elif not arg_expr.startswith('\"') and not arg_expr.endswith('\"'):
        return arg_expr
    else:
        raise SyntaxError("Invalid string argument")

def parse_int(arg_expr: str)->int:
    try:
        return int(arg_expr)
    except:
        raise SyntaxError(f"Cannot parse \"{arg_expr}\" as integer value")

def parse_float(arg_expr: str)->float:
    try:
        return float(arg_expr)
    except:
        raise SyntaxError(f"Cannot parse \"{arg_expr}\" as floating point value")



class StringConverter:
    _supported_conversions = {
        int: parse_int,
        float: parse_float,
        bool: parse_boolean,
        str: parse_string,
    }

    def convert_from_string(self, arg_expr: str, target_type: type) -> Any:
        # Handle simple types directly
        if target_type in self._supported_conversions:
            return self._supported_conversions[target_type](arg_expr)

        # Handle list types
        if get_origin(target_type) is list or target_type is list:
            if not (arg_expr.startswith('[') and arg_expr.endswith(']')):
                raise ValueError(f"Expected a list format (e.g., '[1, 2, 3]'), got: {arg_expr}")

            # Strip brackets and whitespace
            arg_expr = arg_expr[1:-1].strip()

            # Get the inner type of the list
            inner_type_tuple = get_args(target_type)
            inner_type: type

            if len(inner_type_tuple) == 0:
                inner_type = type("")
            else:
                inner_type = inner_type_tuple[0]

            # Split the list elements safely
            str_elements = re.split(r',\s*(?![^\[\]]*])', arg_expr)

            # Recursively convert each element
            return [self.convert_from_string(element.strip(), inner_type) for element in str_elements]

    def add_new_conversion(self, from_type: type, conversion_func):
        if from_type not in self._supported_conversions:
            self._supported_conversions[from_type] = conversion_func

    def has_conversion(self, from_type):
        return from_type in self._supported_conversions

