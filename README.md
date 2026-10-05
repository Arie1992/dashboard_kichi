# Market Insight Dashboard — reviewed baseline

- Satu URL: `?view=all` dan `?view=geprek`
- Sidebar hanya **ALL** dan **Ayam Geprek**
- Sidebar dapat di-hide; tombol ☰ muncul saat sidebar hidden
- ALL mempertahankan dashboard lama
- Geprek: UI V6 report yang dikunci (4 KPI, atribut, tren, review rating rendah, distribusi, detail)
- Tidak ada filter Outlet pada Geprek
- Source Geprek hanya direct SharePoint link yang diberikan user
- Cache data 60 detik
- Tidak ada dummy/local/CSV fallback untuk Geprek
- Jika SharePoint tidak menghasilkan workbook valid, tampilkan error source

- SharePoint source updated to the user-provided Market Insight - Ayam Geprek Kichi-Kichi.xlsx link (`e=MO7GY1`).
- `geprek_ui_reference_v6.html` refreshed from the latest UI reference supplied in chat.
