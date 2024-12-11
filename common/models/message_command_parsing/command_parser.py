import re

from common.models.message_command_parsing.string_object_parsing import StringConverter
from common.models.message_command_parsing.command import Command
from common.models.message_command_parsing.exceptions import *
import Levenshtein
import string

ALLOWED_CHARACTERS = list(string.ascii_letters) + ['-', '_']

class CommandParserBuilder:
    _commands: list[Command] = None
    _supported_argument_packings: list[tuple[str,str]] = [('{','}'), ('(',')'), ('[',']'), ('"', '"')]
    _case_sensitive: bool = False
    _string_converter: StringConverter = StringConverter()

    def __init__(self):
        ...

    def with_commands(self, commands: list[Command]):
        self._commands = commands
        return self

    def with_supported_argument_packing(self, supported_argument_packings: list[tuple[str,str]]):
        self._supported_argument_packings = supported_argument_packings
        return self

    def with_case_sensitivity(self, case_sensitive):
        self._case_sensitive = case_sensitive
        return self

    def with_string_converter(self, converter: StringConverter):
        self._string_converter = converter
        return self

    def build(self):
        """

        :raises AmbiguousCommandError: if one of the commands has the same prefix and name as command added earlier
        :raises Exception: if no commands were given
        """

        if self._commands is None:
           raise Exception("Cannot build parser without commands")

        registered_commands: dict[str,list[Command]] = {}

        for command in self._commands:
            prefix_registered_commands: list[Command] = registered_commands.get(command.prefix())
            if prefix_registered_commands is None:
                registered_commands[command.prefix()] = [command]

            else:
                for registered_command in prefix_registered_commands:
                    registered_command_name = registered_command.name()
                    command_name = command.name()

                    if not self._case_sensitive:
                        registered_command_name = registered_command_name.lower()
                        command_name = command_name.lower()

                    if registered_command_name == command_name:
                        raise AmbiguousCommandError(command_name)

                registered_commands[command.prefix()].append(command)

        return CommandParser(registered_commands, self._case_sensitive, self._supported_argument_packings, self._string_converter)

class CommandParser:

    # splits all commands into smaller groups with the same prefix
    _registered_commands: dict[str,list[Command]]

    # all registered prefixes, it is faster to access this instead of pulling out list of prefixes from dictionary
    _all_prefixes: list[str]

    # used to indicate whether to check the letter case
    _case_sensitive: bool

    # list of pairs of characters a pair of characters denoting the beginning and end of a group of arguments
    _supported_argument_packing: dict[str,str]
    _reversed_argument_packing: dict[str,str]

    _string_converter: StringConverter


    def __init__(self, registered_commands: dict[str,list[Command]], case_sensitive: bool, supported_argument_packing: list[tuple[str,str]], string_converter: StringConverter):
        self._registered_commands = registered_commands
        self._case_sensitive = case_sensitive
        self._supported_argument_packing = { x[0]: x[1] for x in supported_argument_packing }
        self._reversed_argument_packing = { x[1]: x[0] for x in supported_argument_packing }
        self._string_converter = string_converter

        self._all_prefixes = []
        for registered_prefix in registered_commands:
            if ' ' in registered_prefix:
                raise ValueError("Whitespaces in prefixes are not supported")
            self._all_prefixes.append(registered_prefix)


    async def parse(self, command_string: str, execution_context) -> bool:
        command_tokens = self.get_command_tokens(command_string)

        # prefix should be contiguous and at the first place
        command_prefix = command_tokens.pop(0)

        # if any command doesn't have this prefix, then you shouldn't process command further
        if (command_list := self._registered_commands.get(command_prefix)) is None:
            return False

        # extract keyword arguments from tokens (keyword args are the last ones)
        keyword_arguments, other_tokens = self.get_command_keyword_args_tokens(command_tokens)

        # we have pulled out keyword args and prefix so the last things are command and positional arguments
        command, positional_arguments = self.get_command_from_tokens(other_tokens, command_list)

        positional_arguments = self.format_positional_args(positional_arguments)

        # command is None if there was no command with the same name found
        if command is None:
            command_name = ""
            for token in other_tokens:
                command_name += token+" "
            best_matching_command = self.get_best_matching_command(command_prefix, command_name)
            if best_matching_command is None:
                raise CommandNotFoundError(command_name )
            else:
                raise CommandNotFoundError(command_name, best_matching_command.name())

        args_info = command.get_args_info().copy()
        args_names = list(args_info.keys())
        args_names.pop(0)

        arg_count = len(keyword_arguments) + len(positional_arguments)

        # check if total amount of arguments is lesser than minimum argument count
        if arg_count < command.get_required_params_count() - 1:
            raise MissingArgumentError(args_names[-1])

        if len(positional_arguments) > (command.get_required_params_count() + command.get_non_required_params_count() - 1):
            raise RedundantArgumentError((len(args_names), positional_arguments[len(args_names)]))

        if len(positional_arguments) + len(keyword_arguments) > (command.get_required_params_count() + command.get_non_required_params_count() - 1):
            raise  RedundantArgumentError((len(args_names) + 1, keyword_arguments[(len(positional_arguments) + len(keyword_arguments) - len(args_names) - 1)]))


        command_args: dict[str, str] = {}

        for arg_index in range(len(positional_arguments)):
            command_args.update({args_names[arg_index]: positional_arguments[arg_index]})

        for arg in keyword_arguments:
            arg_parts = arg.split(':')
            command_args.update({arg_parts[0]: arg_parts[1]})

        for arg_name in args_names:

            # check if there are any missing arguments
            if command_args.get(arg_name) is None:

                # try pulling the default value for argument
                default_val = command.get_parameter_default_value(arg_name)
                if default_val is None:
                    raise MissingArgumentError(f"Missing argument \"{arg_name}\"")
                else:
                    command_args[arg_name] = default_val
            else:
                # parse arguments into specified type
                command_args[arg_name] = self._string_converter.convert_from_string(command_args[arg_name], args_info[arg_name])

        # add context parameter
        command_args.update({command.context_arg_name(): execution_context})

        # Invoke command
        await command.invoke_async(**command_args)

        return True

    def get_command_tokens(self, expr: str) -> list[str]:
        expr_len: int = len(expr)
        expr_i: int = 0
        tokens: list[str] = []
        current_token: str = ""

        while expr_i < expr_len:
            c = expr[expr_i]
            if c == ' ':
                if len(current_token) > 0:
                    tokens.append(current_token)
                    current_token = ""
            elif c == ':' or c == ',':
                if len(current_token) > 0:
                    tokens.append(current_token)
                    current_token = ""
                tokens.append(c)

            elif (pack_end := self._supported_argument_packing.get(c)) is not None:
                if len(current_token) > 0:
                    raise self.construct_syntax_error(f"Unexpected token \"{pack_end}\"", expr, expr_i)

                open_c = 1
                pack_end_i = expr_i+1
                while pack_end_i < expr_len:
                    if expr[pack_end_i] == pack_end:
                        open_c-=1
                    elif expr[pack_end_i] == c:
                        open_c+=1

                    if open_c == 0:
                        break

                    pack_end_i+=1

                if open_c != 0:
                    raise self.construct_syntax_error(f"Expected \"{pack_end}\" but it wasn't found", expr, expr_len - 1)

                tokens.append(expr[expr_i: pack_end_i+1])
                expr_i = pack_end_i
            else:
                current_token += c

            expr_i += 1

        if len(current_token) > 0:
            tokens.append(current_token)

        return tokens

    def get_command_keyword_args_tokens(self, command_tokens: list[str]) -> tuple[list[str],list[str]]:
        keyword_arguments: list[str] = []
        expr_i = len(command_tokens) - 1
        ct_len = len(command_tokens)
        last_keyword_arg: int = expr_i + 1

        while expr_i >= 0:
            if command_tokens[expr_i] == ':':
                arg_collector_i = expr_i+1
                arg = ""
                while arg_collector_i< ct_len and command_tokens[arg_collector_i] != ':':
                    arg_collector_i+=1

                if arg_collector_i == ct_len:
                    arg_collector_i -=1

                if command_tokens[arg_collector_i] == ':':
                    arg_collector_i -= 2

                arg_builder = expr_i+1
                while arg_builder <= arg_collector_i:
                    arg += command_tokens[arg_builder]
                    arg_builder+=1

                keyword_arguments.append(f"{command_tokens[expr_i - 1]}:{self.format_positional_args(arg)[0]}")
                last_keyword_arg = expr_i - 1

            expr_i -= 1

        return keyword_arguments, command_tokens[0: last_keyword_arg]

    def get_command_from_tokens(self, command_tokens: list[str], commands_source) -> tuple[Command | None, list[str]]:
        command_tokens_i : int = len(command_tokens) - 1

        while command_tokens_i >= 0:
            command_name = command_tokens[0]
            index = 1
            while index <= command_tokens_i:
                command_name+=" " + command_tokens[index]
                index+=1

            if not self._case_sensitive:
                command_name = command_name.lower()

            for command in commands_source:
                if (not self._case_sensitive and command_name == command.name().lower()) or command_name == command.name():
                    return command, command_tokens[command_tokens_i+1:]

            command_tokens_i -= 1

        return None, command_tokens

    def format_positional_args(self, pos_tokens) -> list[str]:
        positional_arguments: list[str] = []
        current_token: str = ""
        pos_tokens_len = len(pos_tokens)
        list_expr_begin: bool = False

        for token_i in range(pos_tokens_len):
            if token_i + 1 < pos_tokens_len:
                if pos_tokens[token_i + 1] == ',':
                    if list_expr_begin:
                        current_token += pos_tokens[token_i]
                    else:
                        current_token += "[" + pos_tokens[token_i]
                        list_expr_begin = True
                else:
                    if list_expr_begin:
                        if pos_tokens[token_i] == ',':
                            current_token += ','
                        else:
                            positional_arguments.append(current_token + pos_tokens[token_i] + "]")
                            list_expr_begin = False
                            current_token = ""
                    else:
                        positional_arguments.append(pos_tokens[token_i])
            else:
                if pos_tokens[token_i] == ',':
                    if list_expr_begin:
                        positional_arguments.append(current_token + "]")
                    else:
                        positional_arguments.append("[" + pos_tokens[token_i] + "]")
                else:
                    if list_expr_begin:
                        positional_arguments.append(current_token + pos_tokens[token_i] + "]")
                    else:
                        positional_arguments.append(pos_tokens[token_i])


        return positional_arguments


    def construct_syntax_error(self, err: str, expr: str, error_position: int):
        err_str: str = err + ": " + expr + "\n"
        err_off = len(err_str) + 2
        for expr_i in range(err_off):
            err_str += " "

        for expr_i in range(len(expr)):
            if error_position-1 <= expr_i <= error_position + 1:
                err_str += '^'
            else:
                err_str += ' '

        return SyntaxError(err_str)

    def get_best_matching_command(self, prefix: str, command_name) -> Command | None:
        current_command: Command = None
        best_similarity: float = 0
        current_similarity: float

        for command in self._registered_commands[prefix]:
            current_similarity = Levenshtein.ratio(command_name, command.name())
            if current_similarity > best_similarity:
                best_similarity = current_similarity
                current_command = command


        if best_similarity > 0.6:
            return current_command
        else:
            return None




