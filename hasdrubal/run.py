from functools import partial, reduce
from typing import Any, Callable, Union

from args import ConfigData
from ast_sorter import topological_sort
from codegen import to_bytecode
from lex import infer_eols, lex, normalise_newlines, show_tokens, to_utf8, TokenStream
from log import logger
from parse_ import parse
from pprint_ import ASTPrinter, TypedASTPrinter
from type_inferer import infer_types
from type_var_resolver import resolve_type_vars

identity = lambda x: x
pipe = partial(reduce, lambda arg, func: func(arg))
to_string: Callable[[Union[bytes, str]], str] = lambda text: (
    text if isinstance(text, str) else to_utf8(text, "utf8")
)

function_generator = lambda config: {
    "lexing": {
        "before": (to_string, normalise_newlines),
        "main": lex,
        "after": (infer_eols,),
        "should_stop": config.show_tokens,
        "on_stop": show_tokens,
    },
    "parsing": {
        "before": (TokenStream,),
        "main": parse,
        "after": (),
        "should_stop": config.show_ast,
        "on_stop": ASTPrinter().run,
    },
    "type_checking": {
        "before": (
            resolve_type_vars,
            topological_sort if config.sort_defs else identity,
        ),
        "main": infer_types,
        "after": (),
        "should_stop": config.show_types,
        "on_stop": TypedASTPrinter().run,
    },
    "codegen": {
        "before": (),
        "main": to_bytecode,
        "after": (),
        "should_stop": False,
        "stop_callback": lambda _: None,
    },
}


def build_phase_runner(config: ConfigData):
    functions = function_generator(config)

    def inner(phase: str, initial: Any) -> Any:
        tasks = functions[phase]
        prepared_value = pipe(tasks["before"], initial)
        main_func = tasks["main"]
        main_value = main_func(prepared_value)
        processed_value = pipe(tasks["after"], main_value)
        return tasks["should_stop"], tasks["on_stop"], processed_value

    return inner


def run_code(source: Union[bytes, str], config: ConfigData) -> str:
    """
    This function actually runs the source code given to it.

    Parameters
    ----------
    source: Union[bytes, str]
        The source code to be run. If it is `bytes`, then it will be
        converted first.
    config: ConfigData
        Command line options that can change how the function runs.

    Returns
    -------
    str
        A string representation of the results of computation, whether
        that is an errors message or a message saying that it is done.
    """
    report, _ = config.writers
    try:
        run_phase = build_phase_runner(config)
        phases = ("lexing", "parsing", "type_checking", "codegen")
        for phase in phases:
            stop, callback, source = run_phase(phase, source)
            if stop:
                return callback(source)

        return ""
    except KeyboardInterrupt:
        return "Program aborted."
    except Exception as err:  # pylint: disable=W0703
        logger.exception("A fatal python error was encountered.", exc_info=True)
        return report(
            err, to_string(source), "" if config.file is None else str(config.file)
        )
