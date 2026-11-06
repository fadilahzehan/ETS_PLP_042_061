"""Test tambahan buatan kelompok.

Isi dengan:
1. Satu test regresi untuk setiap bug yang kalian perbaiki (gagal sebelum perbaikan,
   lulus sesudahnya). Beri nama yang menjelaskan bug-nya.
2. Lima test kasus tepi, masing-masing dengan komentar singkat mengapa kasus itu berisiko.
"""
import pytest

from crud.lexer import LexError, TokenType as T, tokenize
from crud import ast_nodes as ast
from crud.parser import parse_sql, ParseError
from crud.resolver import Resolver
from crud.analyzer import analyze_statement
from crud.pipeline import analyze_source

def test_regresi_presedensi_and_or():
    """AND mengikat lebih kuat dari OR: a OR b AND c = a OR (b AND c) (§3.1)."""
    s = parse_sql("SELECT id FROM t WHERE a = 1 OR b = 2 AND c = 3")
    stmt = s.statements[0]
    # Root WHERE harus OR, dengan sisi kanan berupa AND
    assert isinstance(stmt.where, ast.BinaryOp)
    assert stmt.where.op == "OR"
    assert stmt.where.right.op == "AND"


def test_regresi_keyword_case_insensitive():
    toks = tokenize("select FROM Update delete")
    keywords = [(t.type, t.value) for t in toks if t.type == T.KEYWORD]
    assert keywords == [
        (T.KEYWORD, "SELECT"),
        (T.KEYWORD, "FROM"),
        (T.KEYWORD, "UPDATE"),
        (T.KEYWORD, "DELETE"),
    ]


def test_regresi_string_escaped_quote():
    toks = tokenize("'O''Brien'")
    assert toks[0].type == T.STRING
    assert toks[0].value == "O'Brien"


def test_regresi_operator_diamond():
    toks = tokenize("a <> b")
    ops = [t for t in toks if t.type == T.OP]
    assert len(ops) == 1 and ops[0].value == "<>"


def test_regresi_synchronize_lanjut_setelah_error():
    script = parse_sql("SELECT FROM;\nSELECT id FROM t;")
    assert len(script.errors) == 1
    assert len(script.statements) == 1
    assert isinstance(script.statements[0], ast.Select)


def test_regresi_left_outer_join():
    s = parse_sql("SELECT a.id FROM a LEFT OUTER JOIN b ON b.a_id = a.id").statements[0]
    assert len(s.joins) == 1
    assert s.joins[0].kind == "LEFT"
    assert s.joins[0].source.name == "b"


