# Laporan Bug

---

## Bug 1: Keyword tidak dikenali saat ditulis huruf kecil

Ditemukan oleh: Elang — Diperbaiki oleh: Zehan

### Gejala
Input `select id from t` menghasilkan token `IDENT` untuk kata `select` dan `from`, padahal seharusnya `KEYWORD`. Parser gagal mengenali statement karena tidak menemukan keyword `SELECT`. Menurut SPESIFIKASI.md bagian 2.2, keyword tidak peka huruf besar/kecil.

### Reproduksi minimal
```sql
select id from t
```

### Akar masalah
Di fungsi `_word()` pada `lexer.py`, teks mentah langsung dibandingkan dengan set `KEYWORDS` yang isinya huruf besar semua. Karena Python membandingkan string secara case-sensitive, `"select" in KEYWORDS` bernilai `False`.

Menurut Crafting Interpreters Bab 4, scanner seharusnya menormalisasi teks sebelum mencocokkan dengan reserved words. Identifikasi jenis token berdasarkan makna, bukan representasi hurufnya.

### Perbaikan
File `crud/lexer.py`, fungsi `_word()`. Tambah `upper = text.upper()` lalu cocokkan `upper` dengan `KEYWORDS`. Jika cocok, simpan versi uppercase sebagai value token.

Alternatif yang ditolak: mengubah isi `KEYWORDS` jadi lowercase. Ditolak karena melanggar konvensi codebase bahwa keyword selalu uppercase.

### Test regresi
`test_regresi_keyword_case_insensitive` di `tests/test_tambahan.py`

### Peran AI
AI membantu mengidentifikasi bahwa perbandingan di `_word()` bersifat case-sensitive. Verifikasi: jalankan `tokenize("select")` dan cek token type sebelum dan sesudah perbaikan.

---

## Bug 2: Kutip tunggal ganda di dalam string tidak ditangani

Ditemukan oleh: Zehan — Diperbaiki oleh: Elang

### Gejala
String `'O''Brien'` diparsing jadi token `STRING("O")` lalu kutip kedua memulai string baru. Menurut SPESIFIKASI.md bagian 2.4, `''` di dalam string mewakili satu karakter kutip, jadi hasilnya harus `STRING("O'Brien")`.

### Reproduksi minimal
```sql
SELECT * FROM t WHERE nama = 'O''Brien'
```

### Akar masalah
Di fungsi `_string()` pada `lexer.py`, saat scanner menemukan karakter kutip, langsung `break` keluar loop tanpa cek apakah karakter berikutnya juga kutip. Padahal di SQL, `''` adalah escape sequence.

Menurut Crafting Interpreters Bab 4, scanner harus menangani escape sequence secara eksplisit. Saat menemukan delimiter penutup, periksa dulu apakah itu bagian dari escape sebelum mengakhiri token.

### Perbaikan
File `crud/lexer.py`, fungsi `_string()`. Setelah menemukan kutip, cek `peek() == "'"`. Jika ya, advance sekali lagi, tambahkan satu kutip ke buffer, lalu continue. Jika tidak, baru break.

Alternatif yang ditolak: pakai backslash sebagai escape (`\'`). Ditolak karena bukan standar SQL.

### Test regresi
`test_regresi_string_escaped_quote` di `tests/test_tambahan.py`

### Peran AI
AI menunjukkan pola escape di SQL standar. Verifikasi: jalankan `tokenize("'O''Brien'")` dan pastikan hasilnya satu token bernilai `O'Brien`.

---

## Bug 3: Operator <> tidak dikenali

Ditemukan oleh: Elang — Diperbaiki oleh: Zehan

### Gejala
SQL `WHERE catatan <> 'isi'` menghasilkan parse error. Operator `<>` dipecah jadi dua token `<` dan `>`. Parser menerima `<` sebagai operator perbandingan, lalu menemukan `>` yang bukan ekspresi valid. Error muncul di `laporan_penjualan.sql` baris 6.

### Reproduksi minimal
```sql
SELECT * FROM t WHERE a <> 1
```

### Akar masalah
Di `_scan_token()` pada `lexer.py`, blok untuk karakter `<` hanya memeriksa apakah diikuti `=` (untuk `<=`), tapi tidak memeriksa `>` (untuk `<>`).

Ini melanggar prinsip maximal munch di Crafting Interpreters Bab 4: scanner harus selalu mengambil token terpanjang yang cocok.

### Perbaikan
File `crud/lexer.py`, fungsi `_scan_token()`, blok `ch == "<"`. Tambahkan pengecekan `elif self._match(">")` untuk membentuk `"<>"`.

Alternatif: tidak ada alternatif yang signifikan, ini perbaikan langsung.

### Test regresi
`test_regresi_operator_diamond` di `tests/test_tambahan.py`

### Peran AI
AI membantu melacak parse error di baris 6 kembali ke lexer. Verifikasi: jalankan `tokenize("a <> b")` dan pastikan menghasilkan satu token OP bernilai `<>`.

---

## Bug 4: Presedensi AND dan OR sama

Ditemukan oleh: Zehan — Diperbaiki oleh: Elang

### Gejala
Ekspresi `a = 1 OR b = 2 AND c = 3` diparsing menjadi `(a = 1 OR b = 2) AND c = 3`. Menurut SPESIFIKASI.md bagian 3.1, AND mengikat lebih kuat dari OR, jadi seharusnya `a = 1 OR (b = 2 AND c = 3)`.

### Reproduksi minimal
```sql
SELECT id FROM t WHERE a = 1 OR b = 2 AND c = 3
```

### Akar masalah
Di `parser.py`, fungsi `_logical()` menangani AND dan OR dalam satu loop `while self._check_kw("AND", "OR")`. Keduanya diperlakukan sebagai operator dengan presedensi yang sama dan asosiatif kiri.

Menurut Crafting Interpreters Bab 6, setiap tingkat presedensi diwakili oleh satu fungsi parsing tersendiri. Fungsi presedensi rendah memanggil fungsi presedensi tinggi sebagai operand. Karena OR dan AND punya presedensi berbeda, mereka harus dipisah ke dua fungsi.

### Perbaikan
File `crud/parser.py`. Pecah `_logical()` menjadi dua fungsi: `_or()` yang memanggil `_and()`, dan `_and()` yang memanggil `_not()`. Ganti `_expr()` agar memanggil `_or()`.

Alternatif yang ditolak: Pratt parser dengan tabel presedensi. Ditolak karena lebih sulit dibaca dan tidak konsisten dengan gaya recursive descent di codebase.

### Test regresi
`test_regresi_presedensi_and_or` di `tests/test_tambahan.py`

### Peran AI
AI membantu mengidentifikasi bahwa satu fungsi menangani dua tingkat presedensi. Verifikasi: cetak AST dari `audit.sql` baris 2 dan pastikan OR jadi root.

---

## Bug 5: Error recovery membuang semua token sampai EOF

Ditemukan oleh: Elang — Diperbaiki oleh: Zehan

### Gejala
Di `campuran_error.sql`, statement baris 4 mengandung error. Seharusnya statement valid di baris 6 dan 8 tetap diproses, tapi semua statement setelah error diabaikan.

### Reproduksi minimal
```sql
SELECT FROM;
SELECT id FROM t;
```

### Akar masalah
Di `parser.py`, fungsi `_synchronize()` punya loop yang membuang semua token sampai EOF. Menurut SPESIFIKASI.md bagian 6 dan Crafting Interpreters Bab 6 (panic mode), parser harus membuang token hanya sampai titik sinkronisasi berikutnya, yaitu semicolon.

Analoginya: kalau ada satu kalimat salah di paragraf, skip sampai titik berikutnya, bukan skip seluruh paragraf.

### Perbaikan
File `crud/parser.py`, fungsi `_synchronize()`. Tambahkan pengecekan `if self._peek().type == T.SEMICOLON`, konsumsi semicolon lalu return.

Alternatif yang ditolak: berhenti juga di keyword statement seperti di Crafting Interpreters untuk Lox. Ditolak karena keyword SQL sering muncul di tengah statement (misal SELECT di subquery).

### Test regresi
`test_regresi_synchronize_lanjut_setelah_error` di `tests/test_tambahan.py`

### Peran AI
AI menunjukkan bahwa loop di `_synchronize()` tidak punya kondisi berhenti selain EOF. Verifikasi: parsing `campuran_error.sql` dan pastikan ada 3 statement valid + 1 error.

---

## Bug 6: Scope DELETE tidak ditutup

Ditemukan oleh: Zehan — Diperbaiki oleh: Elang

### Gejala
Jika ada `DELETE FROM sesi s` diikuti statement lain, alias `s` dari DELETE bocor ke statement berikutnya. Menurut SPESIFIKASI.md bagian 4.5, setiap statement berdiri sendiri dan alias tidak boleh bocor.

### Reproduksi minimal
```sql
DELETE FROM sesi s WHERE s.id = 1;
SELECT s.nama FROM pelanggan s;
```

### Akar masalah
Di `resolver.py`, fungsi `_delete()` memanggil `_push()` untuk membuat scope baru tapi tidak pernah memanggil `_pop()` untuk menutupnya. Bandingkan dengan `_update()` yang punya `_push()` dan `_pop()` berpasangan.

Menurut Crafting Interpreters Bab 11, setiap `beginScope()` harus berpasangan dengan `endScope()`. Jika scope tidak ditutup, binding di dalamnya tetap aktif dan mencemari lingkungan untuk kode setelahnya.

### Perbaikan
File `crud/resolver.py`, fungsi `_delete()`. Tambahkan `self._pop()` di akhir fungsi.

Alternatif yang ditolak: pakai context manager agar push/pop otomatis. Ditolak karena mengubah arsitektur terlalu banyak.

### Test regresi
`test_regresi_delete_scope_tidak_bocor` di `tests/test_tambahan.py`

### Peran AI
AI menemukan ketidaksimetrisan antara `_delete()` dan `_update()`. Verifikasi: resolve dua statement berturutan dan pastikan alias dari DELETE tidak muncul di scope SELECT.

---

## Bug 7: Pencarian scope dari luar ke dalam (terbalik)

Ditemukan oleh: Elang — Diperbaiki oleh: Zehan

### Gejala
Pada `audit.sql` baris 12-14, ada subquery yang pakai alias `x` sama dengan outer query. Kolom `x.pelanggan_id` di subquery seharusnya resolve ke `pesanan` (inner) tapi malah resolve ke `pelanggan` (outer). Shadowing tidak bekerja.

### Reproduksi minimal
```sql
SELECT x.id FROM pelanggan x
WHERE x.id IN (SELECT x.pelanggan_id FROM pesanan x)
```

### Akar masalah
Di `resolver.py`, fungsi `_lookup()` membangun list dari scope terdalam ke terluar, lalu iterasi `reversed()` sehingga pencarian dimulai dari scope terluar. Entry terluar yang pertama ditemukan langsung dipakai, inner scope tidak punya kesempatan meng-shadow.

Menurut Crafting Interpreters Bab 11, variable resolution harus dimulai dari scope terdalam. Ini yang membuat shadowing bekerja: deklarasi di inner scope menutupi deklarasi dengan nama sama di outer scope.

### Perbaikan
File `crud/resolver.py`, fungsi `_lookup()`. Hapus list `chain` dan `reversed()`. Iterasi langsung dari `self.scope` ke atas via `.parent`, return entry pertama yang ditemukan.

Alternatif: tetap pakai list tapi jangan di-reverse. Dipilih yang langsung karena lebih simpel.

### Test regresi
`test_regresi_lookup_dari_dalam_ke_luar` di `tests/test_tambahan.py`

### Peran AI
AI menemukan bahwa `reversed()` membalik urutan pencarian. Verifikasi: resolve query dengan alias `x` di inner dan outer, pastikan inner menang.

---

## Bug 8: Subquery di UPDATE ditandai U bukan R

Ditemukan oleh: Zehan — Diperbaiki oleh: Elang

### Gejala
UPDATE dengan subquery di WHERE menandai tabel di subquery sebagai U. Menurut SPESIFIKASI.md bagian 5, tabel di subquery selalu R, hanya tabel target UPDATE yang U.

### Reproduksi minimal
```sql
UPDATE pesanan SET status = 'x'
WHERE id IN (SELECT pesanan_id FROM arsip)
```

### Akar masalah
Di `analyzer.py`, fungsi `analyze_statement()`, bagian UPDATE: `_collect(assignment.value, usage, "U")` dan `_collect(stmt.where, usage, "U")` meneruskan operasi U ke seluruh ekspresi termasuk subquery. Padahal subquery di SET dan WHERE itu membaca data, bukan mengubahnya.

Aturan CRUD bagian 5: hanya tabel target yang mendapat operasi statement-nya. Tabel yang diakses lewat subquery selalu R.

### Perbaikan
File `crud/analyzer.py`, fungsi `analyze_statement()`. Ganti `"U"` jadi `"R"` pada kedua pemanggilan `_collect()` di blok UPDATE. Baris `usage[stmt.table.name].add("U")` tetap U karena itu tabel target.

### Test regresi
`test_regresi_update_subquery_operasi_read` di `tests/test_tambahan.py`

### Peran AI
AI menemukan inkonsistensi antara spesifikasi dan argumen di `_collect`. Verifikasi: analisis UPDATE dengan subquery dan pastikan tabel di subquery hanya mendapat R.

---

## Bug 9: LEFT OUTER JOIN menyebabkan parse error

Ditemukan oleh: Elang — Diperbaiki oleh: Zehan

### Gejala
`pemeliharaan.sql` baris 5 menggunakan `LEFT OUTER JOIN` tapi parser error. Setelah mengonsumsi LEFT, parser langsung mengharapkan JOIN tapi menemukan OUTER. Bug ini tersembunyi karena file dimulai dengan komentar blok yang gagal duluan di T3.

### Reproduksi minimal
```sql
SELECT a.id FROM a LEFT OUTER JOIN b ON b.a_id = a.id
```

### Akar masalah
Di `parser.py`, fungsi `_join()` hanya menangani INNER dan LEFT lalu langsung `_expect_kw("JOIN")`. Grammar di SPESIFIKASI.md bagian 3 menyatakan OUTER bersifat opsional setelah LEFT.

Menurut Crafting Interpreters Bab 6, elemen opsional di grammar (notasi kurung siku) harus dipetakan ke `match` yang bersifat opsional, bukan diabaikan. Kalau diabaikan, token opsional itu menyangkut dan menghambat parsing token berikutnya.

### Perbaikan
File `crud/parser.py`, fungsi `_join()`. Setelah `_match_kw("LEFT")`, tambahkan `self._match_kw("OUTER")`. Karena `_match_kw` bersifat opsional, kalau tidak ada OUTER tidak terjadi apa-apa.

Alternatif yang ditolak: buat keyword compound LEFT_OUTER di lexer. Ditolak karena mengubah arsitektur dan memperumit token type.

### Test regresi
`test_regresi_left_outer_join` di `tests/test_tambahan.py`

### Peran AI
AI menemukan bug ini saat mencocokkan grammar join di spesifikasi dengan implementasi `_join()`. Verifikasi: parsing `pemeliharaan.sql` setelah T3 selesai dan pastikan tidak ada parse error.

---
