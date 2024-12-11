class MissingArgumentError(Exception):
    def __init__(self, param_name: str):
        super().__init__(f"Missing argument \"{param_name}\"")

class RedundantArgumentError(Exception):
    def __init__(self, arg_info: tuple[int, str]):
        if arg_info is not None:
            super().__init__(f"Redundant argument on position {arg_info[0]} (\"{arg_info[1]}\")")
        else:
            super().__init__(f"Passed to many arguments")

class AmbiguousCommandError(Exception):
    def __init__(self, command_name):
        super().__init__(f"There is another command with the same name of \"{command_name}\"")

class CommandNotFoundError(Exception):
    def __init__(self, command_name: str, most_similar_command_name: str | None = None):
        if most_similar_command_name is None:
            super().__init__(f"Cannot find command with name of \"{command_name}\"")
        else:
            super().__init__(f"Cannot find command with name of \"{command_name}\" (do you mean \"{most_similar_command_name}\"?)")