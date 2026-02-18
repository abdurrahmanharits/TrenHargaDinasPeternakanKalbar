import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_FILE = "2 Pemantauan Harga 2026 (1).xlsx"
INPUT_CSV = "data_input.csv"


@st.cache_data(show_spinner=False)
def load_choice():
    df = pd.read_excel(DATA_FILE, sheet_name="choice")
    komoditi = df["komoditi"].dropna().astype(str).unique().tolist()
    tingkatan = df["tingkatan"].dropna().astype(str).unique().tolist()
    provinsi = df["Provinsi"].dropna().astype(str).unique().tolist()
    return komoditi, tingkatan, provinsi


@st.cache_data(show_spinner=False)
def load_daily_data():
    sheets = ["jan26", "feb26"]
    frames = []
    for s in sheets:
        df = pd.read_excel(DATA_FILE, sheet_name=s)
        # Identify date columns (datetime) and keep base metadata columns.
        date_cols = [c for c in df.columns if isinstance(c, pd.Timestamp)]
        base_cols = [" ", "Komoditi", "Tingkat", "Prov/Kab/Kota"]
        base_cols = [c for c in base_cols if c in df.columns]
        melted = df[base_cols + date_cols].melt(
            id_vars=base_cols, var_name="Tanggal", value_name="Harga"
        )
        frames.append(melted)
    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=["Harga"])
    out["Harga"] = pd.to_numeric(out["Harga"], errors="coerce")
    out = out.dropna(subset=["Harga"])
    out.rename(
        columns={" ": "Sumber", "Prov/Kab/Kota": "Provinsi"}, inplace=True
    )
    out["Tanggal"] = pd.to_datetime(out["Tanggal"]).dt.date
    return out


def load_input_data():
    if os.path.exists(INPUT_CSV):
        df = pd.read_csv(INPUT_CSV, parse_dates=["Tanggal"])
        df["Tanggal"] = df["Tanggal"].dt.date
        return df
    return pd.DataFrame(
        columns=["Sumber", "Komoditi", "Tingkat", "Provinsi", "Tanggal", "Harga"]
    )


def append_input_row(row):
    df = load_input_data()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(INPUT_CSV, index=False)


def main():
    st.set_page_config(page_title="Dashboard Harga Komoditas", layout="wide")
    st.title("Dashboard Harga Komoditas")

    if not os.path.exists(DATA_FILE):
        st.error(f"File data tidak ditemukan: {DATA_FILE}")
        return

    komoditi, tingkatan, provinsi = load_choice()
    daily_data = load_daily_data()
    input_data = load_input_data()

    tab_input, tab_rekap, tab_tren = st.tabs(
        ["Input Data", "Rekapan Tabular", "Tren Harga Harian"]
    )

    with tab_input:
        st.subheader("Input Data")
        with st.form("input_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                komoditi_val = st.selectbox("Komoditi", komoditi)
                harga_val = st.number_input(
                    "Harga", min_value=0.0, step=100.0, format="%.0f"
                )
            with col2:
                tingkat_val = st.selectbox("Tingkatan", tingkatan)
                tanggal_val = st.date_input("Tanggal", value=date.today())
            with col3:
                provinsi_val = st.selectbox("Provinsi", provinsi)
                sumber_val = st.text_input("Sumber", value="SP2KP")

            submitted = st.form_submit_button("Simpan")
            if submitted:
                row = {
                    "Sumber": sumber_val.strip(),
                    "Komoditi": komoditi_val,
                    "Tingkat": tingkat_val,
                    "Provinsi": provinsi_val,
                    "Tanggal": tanggal_val,
                    "Harga": float(harga_val),
                }
                append_input_row(row)
                st.success("Data berhasil disimpan.")

        st.markdown("**Data Input Tersimpan**")
        st.dataframe(load_input_data(), use_container_width=True, height=300)

    with tab_rekap:
        st.subheader("Rekapan Tabular")
        st.caption("Gabungan data historis (Jan-Feb 2026) dan data input.")
        combined = pd.concat([daily_data, input_data], ignore_index=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            kom_filter = st.multiselect("Filter Komoditi", komoditi, default=komoditi[:1])
        with col2:
            ting_filter = st.multiselect("Filter Tingkatan", tingkatan, default=tingkatan[:1])
        with col3:
            prov_filter = st.multiselect("Filter Provinsi", provinsi, default=provinsi[:1])

        filtered = combined[
            combined["Komoditi"].isin(kom_filter)
            & combined["Tingkat"].isin(ting_filter)
            & combined["Provinsi"].isin(prov_filter)
        ]
        st.dataframe(filtered.sort_values("Tanggal"), use_container_width=True, height=400)

    with tab_tren:
        st.subheader("Tren Harga Harian per Komoditas")
        combined = pd.concat([daily_data, input_data], ignore_index=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            kom_plot = st.multiselect("Komoditi", komoditi, default=komoditi[:2])
        with col2:
            ting_plot = st.multiselect("Tingkatan", tingkatan, default=tingkatan[:1])
        with col3:
            prov_plot = st.multiselect("Provinsi", provinsi, default=provinsi[:1])

        if not combined.empty:
            min_date = combined["Tanggal"].min()
            max_date = combined["Tanggal"].max()
        else:
            min_date = date.today()
            max_date = date.today()

        date_range = st.date_input(
            "Rentang Tanggal", value=(min_date, max_date)
        )

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = min_date
            end_date = max_date

        plot_df = combined[
            combined["Komoditi"].isin(kom_plot)
            & combined["Tingkat"].isin(ting_plot)
            & combined["Provinsi"].isin(prov_plot)
            & (combined["Tanggal"] >= start_date)
            & (combined["Tanggal"] <= end_date)
        ].copy()

        if plot_df.empty:
            st.warning("Tidak ada data untuk filter yang dipilih.")
        else:
            fig = px.line(
                plot_df.sort_values("Tanggal"),
                x="Tanggal",
                y="Harga",
                color="Komoditi",
                line_group="Provinsi",
                markers=True,
            )
            fig.update_layout(
                xaxis_title="Tanggal",
                yaxis_title="Harga",
                legend_title="Komoditi",
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
