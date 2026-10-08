# Kichi-Kichi Market Insight — Streamlit

Dashboard Streamlit yang membaca workbook SharePoint live (cache 60 detik).

## Fitur revisi
- Card **Rata-rata Nilai Atribut** dapat diklik.
- Popup detail menampilkan Reason, jumlah review, average rating, dan distribusi rating 1–5.
- Mapping menggunakan sheet Excel bernama **keyword** dengan kolom `Group`, `Keyword`, `Reason`.
- Keyword berbeda yang memiliki Reason sama digabung pada popup.
- Bagian **Rating Rendah & Review Terkait** menampilkan Reason hasil mapping, sedangkan komentar responden ditampilkan terpisah.
- Filter tanggal, outlet, aspek, dan batas rating tetap tersedia.

## Struktur repository GitHub
Upload isi ZIP langsung ke root repository:
- `streamlit_app.py`
- `requirements.txt`
- `geprek_ui_reference_v6.html`
- `.gitignore`
- `README.md`

## Deploy Streamlit Community Cloud
Pilih repository GitHub dan gunakan `streamlit_app.py` sebagai Main file path.

## Format workbook
Sheet data survei tetap seperti versi sebelumnya. Tambahkan/pertahankan sheet bernama `keyword` dengan kolom:
`Group | Keyword | Reason`

Aplikasi tidak menggunakan data dummy/fallback. Jika SharePoint gagal dibaca, dashboard menampilkan error.
