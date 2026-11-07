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


def test_regresi_delete_scope_tidak_bocor():
    sql = "DELETE FROM sesi s WHERE s.id = 1;\nSELECT s.nama FROM pelanggan s;"
    script = parse_sql(sql)
    diags = Resolver().resolve_script(script)
    cols = [n for n in ast.iter_nodes(script) if isinstance(n, ast.ColumnRef)]
    select_col = [c for c in cols if c.name == "nama"][0]
    assert select_col.resolved == "pelanggan"
    errors = [d for d in diags if d.level == "error"]
    assert errors == []


def test_regresi_lookup_dari_dalam_ke_luar():
    sql = ("SELECT x.id FROM pelanggan x "
           "WHERE x.id IN (SELECT x.pelanggan_id FROM pesanan x)")
    script = parse_sql(sql)
    Resolver().resolve_script(script)
    inner_cols = [n for n in ast.iter_nodes(script)
                  if isinstance(n, ast.ColumnRef) and n.name == "pelanggan_id"]
    assert len(inner_cols) == 1
    assert inner_cols[0].resolved == "pesanan"


def test_regresi_update_subquery_operasi_read():
    usage = analyze_statement(
        parse_sql("UPDATE pesanan SET status = 'x' "
                  "WHERE id IN (SELECT pesanan_id FROM arsip)").statements[0])
    assert usage["pesanan"] == {"U"}
    assert usage["arsip"] == {"R"}


# ============================================================
# Test kasus tepi
# ============================================================

def test_edge_input_kosong():
    # Input kosong bisa crash jika scanner/parser tidak menangani EOF di awal.
    script = parse_sql("")
    assert script.statements == [] and script.errors == []


def test_edge_semicolon_berturutan():
    # Semicolon berturutan (;;;) harus diabaikan tanpa menghasilkan error,
    # karena grammar script mengizinkan { ";" | statement }.
    script = parse_sql(";;; SELECT id FROM t ;;;")
    assert len(script.statements) == 1 and script.errors == []


def test_edge_subquery_tiga_level():
    # Subquery bersarang tiga level menguji scope chain tidak rusak di kedalaman.
    sql = ("SELECT id FROM a WHERE id IN "
           "(SELECT id FROM b WHERE id IN "
           "(SELECT id FROM c))")
    res = analyze_source(sql)
    assert res.matrix() == {"a": "R", "b": "R", "c": "R"}


def test_edge_multi_join_dan_group_order():
    # Query kompleks dengan multiple join, WHERE, GROUP BY, dan ORDER BY.
    sql = ("SELECT p.id, COUNT(*) FROM pelanggan p "
           "INNER JOIN pesanan o ON o.pelanggan_id = p.id "
           "WHERE p.aktif = 1 "
           "GROUP BY p.id "
           "ORDER BY p.id DESC")
    res = analyze_source(sql)
    assert res.matrix() == {"pelanggan": "R", "pesanan": "R"}


def test_edge_semua_crud_satu_file():
    # Satu file dengan keempat operasi CRUD memastikan matrix gabungan benar.
    sql = ("SELECT id FROM produk;\n"
           "INSERT INTO log (pesan) VALUES ('ok');\n"
           "UPDATE produk SET stok = 0;\n"
           "DELETE FROM log WHERE id = 1;")
    res = analyze_source(sql)
    assert res.matrix() == {"log": "CD", "produk": "RU"}





