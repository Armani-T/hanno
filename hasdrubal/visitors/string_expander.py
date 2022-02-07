from os.path import sep as platform_path_separator
from re import ASCII, compile as re_compile
from typing import List, Mapping, Match

from asts.visitor import BaseASTVisitor
from asts.types_ import Type
from asts import base

ESCAPE_PATTERN = re_compile(
    (
        r"(?P<special>\\[abfnrvt/'\"\\])"
        r"|(?P<one_byte>\\[0-9A-Fa-f]{2})"
        r"|(?P<two_byte>\\u[0-9A-Fa-f]{4})"
        r"|(?P<three_byte>\\U[0-9A-Fa-f]{6})"
    ),
    ASCII,
)

SPECIAL_ESCAPES: Mapping[str, str] = {
    "\\a": "\a",
    "\\b": "\b",
    "\\f": "\f",
    "\\n": "\n",
    "\\r": "\r",
    "\\v": "\v",
    "\\t": "\t",
    "\\'": "'",
    '\\"': '"',
    "\\\\": "\\",
    "\\/": platform_path_separator,
}


def expand_strings(tree: base.ASTNode) -> base.ASTNode:
    """
    Expand out string literals containing Unicode escapes.

    Parameters
    ----------
    tree: base.ASTNode
        The tree containing unexpanded Unicode escapes in the strings.

    Returns
    -------
    base.ASTNode
        The same tree but with the Unicode escapes expanded properly.
    """
    expander = StringExpander()
    return expander.run(tree)


class StringExpander(BaseASTVisitor[base.ASTNode]):
    """
    Convert unexpanded Unicode escapes into the correct Unicode
    character.
    """

    def visit_block(self, node: base.Block) -> base.Block:
        return base.Block(
            node.span,
            [expr.visit(self) for expr in node.body],
        )

    def visit_cond(self, node: base.Cond) -> base.Cond:
        return base.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> base.Define:
        return base.Define(
            node.span,
            node.target.visit(self),
            node.value.visit(self),
        )

    def visit_func_call(self, node: base.FuncCall) -> base.FuncCall:
        return base.FuncCall(
            node.span,
            node.caller.visit(self),
            node.callee.visit(self),
        )

    def visit_function(self, node: base.Function) -> base.Function:
        return base.Function(
            node.span,
            node.param.visit(self),
            node.body.visit(self),
        )

    def visit_name(self, node: base.Name) -> base.Name:
        return node

    def visit_scalar(self, node: base.Scalar) -> base.Scalar:
        if isinstance(node.value, str):
            return base.Scalar(node.span, expand_string(node.value))
        return node

    def visit_type(self, node: Type) -> Type:
        return node

    def visit_vector(self, node: base.Vector) -> base.Vector:
        return base.Vector(
            node.span,
            node.vec_type,
            [elem.visit(self) for elem in node.elements],
        )


def expand_string(string: str) -> str:
    """
    Take the string value itself and expand all the escapes found
    inside it.

    Parameters
    ----------
    string: str
        The string value extracted from the `Scalar` node.

    Returns
    -------
    str
        The same string but with all the escapes replaced.
    """
    prev_end = 0
    string_parts: List[str] = []
    for match in ESCAPE_PATTERN.finditer(string):
        start, new_end = match.span()
        string_parts.append(string[prev_end:start])
        escaped_version = process_match(match)
        string_parts.append(escaped_version)
        prev_end = new_end

    return "".join(string_parts)


def process_match(match: Match[str]) -> str:
    """
    Take the match object and turn it into a Unicode character.

    Parameters
    ----------
    match: Match[str]
        The match object made by doing a regex match on the original
        string.

    Returns
    -------
    str
        The corresponding Unicode character.
    """
    if match.group("special") is not None:
        escape = match.group("special")
        return SPECIAL_ESCAPES.get(escape, escape)
    if match.group("one_byte") is not None:
        escape = match.group("one_byte")
        return chr(int(escape[1:], base=16))
    if match.group("two_byte") is not None:
        escape = match.group("two_byte")
        return chr(int(escape[2:], base=16))
    if match.group("three_byte") is not None:
        escape = match.group("three_byte")
        return chr(int(escape[2:], base=16))
    return match.string
