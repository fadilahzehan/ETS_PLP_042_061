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
    