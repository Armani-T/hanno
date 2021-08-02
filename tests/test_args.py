# pylint: disable=C0116, W0612
from codecs import lookup

from pytest import mark

from context import args
from utils import FakeNamespace


@mark.cmd
@mark.parametrize(
    "cmd_args,expected_",
    (
        ((), {}),
        (("-?",), {"show_help": True}),
        (
            ("--lex", "-e", "utf16"),
            {"encoding": "utf16", "show_tokens": True},
        ),
    ),
)
def test_build_config(cmd_args, expected_):
    namespace = FakeNamespace()
    args.parser.parse_args(args=cmd_args, namespace=namespace)
    config = args.build_config(namespace)
    expected = args.DEFAULT_CONFIG | expected_

    assert callable(config.report_error)
    assert callable(config.write)
    assert lookup(config.encoding) == lookup(actual_expected.encoding)
    assert config.file == actual_expected.file
    assert config.show_help == actual_expected.show_help
    assert config.show_version == actual_expected.show_version
    assert config.show_tokens == actual_expected.show_tokens
