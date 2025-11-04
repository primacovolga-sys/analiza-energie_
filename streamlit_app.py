%%writefile streamlit_app.py
import streamlit as st
import pandas as pd
import io
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Analiza Energiei", layout="wide")
st.title("Analiza Interactivă a Energiei – Streamlit")

uploaded = st.file_uploader("Încarcă CSV/XLSX", type=["csv","xlsx"])
if uploaded:
    df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)

    # detect timp
    tc = [c for c in df.columns if c.lower() in ["datetime","date","timestamp","time","ora","data"]]
    if not tc:
        tc = [c for c in df.columns if any(k in c.lower() for k in ["date","time","ora","data"])]
    if not tc:
        st.error("Nu am găsit o coloană de timp."); st.stop()
    t = tc[0]
    df[t] = pd.to_datetime(df[t], errors="coerce")
    df = df.dropna(subset=[t]).sort_values(t)

    # derivate
    df["year"]=df[t].dt.year; df["month"]=df[t].dt.month

    # coloane energie
    num_cols = df.select_dtypes("number").columns.tolist()
    energy_cols = [c for c in num_cols if any(k in c.lower() for k in
      ["solar","fotovolta","pv","eolian","wind","hidro","hydro","nuclear","coal","carbune","gas","gaz"])]

    # filtre
    st.sidebar.header("Filtre")
    dmin, dmax = df[t].min(), df[t].max()
    r = st.sidebar.date_input("Interval de date", (dmin.date(), dmax.date()))
    if isinstance(r, tuple): (start, end) = r
    else: start, end = dmin.date(), dmax.date()
    df = df[(df[t] >= pd.Timestamp(start)) & (df[t] <= pd.Timestamp(end))]

    chosen = st.sidebar.multiselect("Tipuri de energie", options=energy_cols, default=energy_cols[:5])

    # grafice
    if chosen:
        st.subheader("Serii temporale (selectate)")
        st.plotly_chart(px.line(df, x=t, y=chosen), use_container_width=True)

        fm = df.set_index(t).groupby(pd.Grouper(freq="M"))[chosen].sum().reset_index()
        st.subheader("Agregare lunară (sumă)")
        st.plotly_chart(px.bar(fm, x=t, y=chosen, barmode="group"), use_container_width=True)

    # PDF simplu (HTML → bytes)
    if st.button("Generează raport PDF (simplu)"):
        import pdfkit, tempfile, os
        html = "<h1>Raport Energie</h1>"
        html += f"<p>Perioadă: {start} – {end}</p>"
        if chosen:
            html += "<p>Tipuri: " + ", ".join(chosen) + "</p>"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            tmp.write(html.encode("utf-8")); tmp.flush()
            pdf_bytes = None
            try:
                # necesită wkhtmltopdf pe unele platforme; pe Streamlit Cloud există container – alternativ poți afișa HTML simplu
                pdf_bytes = pdfkit.from_file(tmp.name, False)
            except Exception:
                pdf_bytes = html.encode("utf-8")  # fallback: oferim HTML dacă nu e pdfkit
        st.download_button("Descarcă raport", data=pdf_bytes, file_name="raport.pdf" if pdf_bytes else "raport.html")
