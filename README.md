# Kichi-Kichi Market Insight — Exact HTML Revision

This revision fixes the visual mismatch in the previous package.

- Ayam Geprek view now renders `geprek_ui_reference_v6.html` directly as the visual source of truth.
- No custom sidebar/layout is injected into the Ayam Geprek reference view.
- The SharePoint loader remains in `streamlit_app.py` and is cached for 60 seconds.
- IMPORTANT: the exact reference currently contains its original demo JS values. The next integration step is data-binding without changing its DOM/CSS.
