# Kichi-Kichi Market Insight — Ayam Geprek

Streamlit dashboard yang membaca workbook SharePoint live (cache 60 detik) dan mempertahankan tampilan HTML referensi.

## Deploy
Upload hanya file berikut ke root GitHub:
- `streamlit_app.py`
- `requirements.txt`
- `geprek_ui_reference_v6.html`
- `.gitignore`

`streamlit_app.py` tidak memakai data dummy/fallback. Jika SharePoint tidak dapat diunduh, aplikasi menampilkan error agar data palsu tidak muncul.
