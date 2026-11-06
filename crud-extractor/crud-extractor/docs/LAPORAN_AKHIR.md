# Laporan Akhir

## 1. Hasil evaluasi

```
Dievaluasi: audit.sql, campuran_error.sql, laporan_penjualan.sql, pemeliharaan.sql (27 triple)

Metode   Precision  Recall     F1
parser        1.00    1.00   1.00
regex         0.65    0.81   0.72
```

Parser mencapai skor sempurna pada semua 27 triple. Regex hanya 0.72 F1 karena banyak false positive (12) dan false negative (5).


## 2. Tiga kasus di mana regex salah

### Kasus 1 — Komentar baris dianggap SQL

Di `laporan_penjualan.sql` baris 2 ada komentar `-- DELETE FROM pelanggan`. Regex menemukan pola `DELETE FROM pelanggan` dan menghasilkan false positive operasi D untuk tabel pelanggan. Parser tidak terkecoh karena lexer sudah membuang komentar saat scanning — token tidak pernah dibuat untuk teks di dalam komentar. Ini menunjukkan keunggulan pipeline lexer ke parser: konteks sintaksis dipahami sejak tahap scanning (CI Bab 4).

### Kasus 2 — String literal dianggap nama tabel

Di `laporan_penjualan.sql` baris 6 ada klausa `o.catatan <> 'FROM rahasia'`. Regex mencocokkan pola `FROM rahasia` di dalam string literal dan menghasilkan false positive tabel `rahasia` dengan operasi R. Parser tidak salah karena lexer mengenali `'FROM rahasia'` sebagai satu token STRING. Kata `FROM` di dalamnya tidak pernah jadi keyword.

### Kasus 3 — Komentar blok dianggap SQL

Di `pemeliharaan.sql` baris 1-2 ada komentar blok yang mengandung teks `UPDATE pelanggan_lama`. Regex menemukan pola ini dan menghasilkan false positive operasi U untuk tabel `pelanggan_lama` yang bahkan tidak ada di database. Parser mengenali blok komentar dan melewatinya tanpa membuat token.


## 3. Batas pendekatan kami

### Batas 1 — CTE (WITH ... AS)

SQL seperti `WITH aktif AS (SELECT id FROM pelanggan WHERE aktif = 1) SELECT * FROM aktif` tidak bisa diparsing karena grammar tidak mendukung keyword WITH. Tool akan menghasilkan parse error. Untuk menangani ini dibutuhkan aturan grammar baru dan logika di resolver untuk mendaftarkan nama CTE sebagai tabel virtual di scope.

### Batas 2 — UNION / INTERSECT / EXCEPT

Query seperti `SELECT id FROM a UNION SELECT id FROM b` akan error karena setelah statement pertama selesai, parser menemukan keyword UNION yang tidak diharapkan. Padahal kedua tabel seharusnya R. Untuk mendukung ini, grammar select_stmt perlu diperluas dengan aturan compound select.

### Batas 3 — DDL (CREATE TABLE, ALTER TABLE, DROP TABLE)

Statement seperti `CREATE TABLE log (id INT)` tidak dikenali karena CREATE bukan keyword dan `_statement()` hanya menangani SELECT, INSERT, UPDATE, DELETE. DDL penting di dunia nyata karena CREATE bisa dianggap C dan DROP bisa dianggap D. Perlu menambah keyword dan aturan grammar baru.


## 4. Pembagian kerja

Anggota 1: Elang Permadi Lau
NIM: 251524042
Fokus: Pengerjaan dan analisis pada komponen lexer dan parser (implementasi T1 INSERT...SELECT, perbaikan bug B1, B3, B5, B7, B9), pembuatan kerangka pengujian test regresi dan test kasus tepi.

Anggota 2: Raden Muhammad Zehan Fadillah
NIM: 251524061
Fokus: Pengerjaan dan analisis pada komponen resolver dan analyzer (implementasi T2 kolom tanpa qualifier, implementasi T3 komentar blok, perbaikan bug B2, B4, B6, B8), pelabelan data ground truth secara manual untuk evaluasi.

Kolaborasi:
Keduanya menerapkan metode pair programming secara bergantian (driver dan navigator tiap 30 menit). Setiap perbaikan kode ditinjau bersama melalui code review sebelum diintegrasikan. Keduanya saling menguji pemahaman konsep dan akar masalah setiap bug berdasarkan bab-bab acuan di Crafting Interpreters untuk persiapan sesi demo individu.
