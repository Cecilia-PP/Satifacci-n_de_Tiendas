import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import glob
import os

# Configuración de pantalla ancha y título
st.set_page_config(page_title="Tablero Satisfacción de Tienda", layout="wide")

# Bloqueo de traducción automática del navegador
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# Inyección CSS específica para obligar a Streamlit a saltar línea en los encabezados de las tablas
st.markdown("""
<style>
    /* Forzar el wrap de texto en encabezados de st.dataframe */
    div[data-testid="stTable"] th, div[data-testid="stDataFrame"] th {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        text-align: center !important;
        vertical-align: middle !important;
    }
    div[data-testid="stDataFrame"] [data-testid="stHeader"] {
        white-space: pre-wrap !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📦 Tablero Satisfacción de Tienda")

@st.cache_data
def cargar_datos():
    ruta_local = r"C:\Users\cpe021ar\Documents\Python\Tablero_Satifacción_de_Tienda"
    archivo_parquet = os.path.join(ruta_local, "Tablero_Satifacción_de_Tienda.parquet")
    
    if os.path.exists(archivo_parquet):
        df = pd.read_parquet(archivo_parquet)
    else:
        archivos = glob.glob("*.parquet") + glob.glob("Datos_mensales/*.parquet") + glob.glob("Datos_mensuales/*.parquet")
        if not archivos:
            raise FileNotFoundError("No se encontró 'Tablero_Satifacción_de_Tienda.parquet'. Ejecuta primero 'crear_historico.py'.")
        df = pd.concat([pd.read_parquet(f) for f in archivos], ignore_index=True)

    df.columns = df.columns.str.strip()
    
    # 1. Identificación de columnas desde el SQL DB2
    col_tienda_grabo = None
    for c in ["Tienda que Grabo", "TIEND que grabo", "Tienda que grabo", "BDTIEN", "Tienda_Que_Grabo"]:
        if c in df.columns:
            col_tienda_grabo = c
            break

    col_nudvre = None
    for c in ["NUDVRE", "Num Dev", "Nota", "Num Nota", "NUM_DEV", "BDNDV", "Num_Nota_Devolucion", "Num_Movimiento", "Num_Mov"]:
        if c in df.columns:
            col_nudvre = c
            break

    col_artik = None
    for c in ["ARTIK", "BDART", "Artículo", "Articulo"]:
        if c in df.columns:
            col_artik = c
            break

    # 2. Tratamiento de Tiendas
    if col_tienda_grabo:
        df["Tienda que Grabo_Limpia"] = df[col_tienda_grabo].fillna("Sin Registro").astype(str).str.replace(r"\.0$", "", regex=True)
    else:
        df["Tienda que Grabo_Limpia"] = "Sin Registro"

    # 3. Mapeo del Estado de Rectificación
    col_estado = "Estado" if "Estado" in df.columns else ("ESTCDR" if "ESTCDR" in df.columns else None)
    if col_estado:
        estado_limpio = df[col_estado].fillna("N").astype(str).str.strip().str.upper()
        estado_limpio = estado_limpio.replace({"NAN": "N", "": "N", "NONE": "N", "(EN BLANCO)": "N"})
        
        mapa_estados = {
            "M": "Confirmada",
            "R": "Anuladas",
            "P": "Pendientes",
            "A": "Automática",
            "N": "N - Nulo"
        }
        df["Estado Rectificación"] = estado_limpio.map(mapa_estados).fillna("N - Nulo")
    else:
        df["Estado Rectificación"] = "N - Nulo"

    # 4. Identificador de Operación / Nota
    if col_nudvre:
        df["Nota_Operacion"] = df[col_nudvre].fillna("Sin Nota").astype(str).str.replace(r"\.0$", "", regex=True)
    else:
        df["Nota_Operacion"] = "Sin Nota"

    # 5. Campos de Fecha
    col_fecha = "Fecha del Movimiento" if "Fecha del Movimiento" in df.columns else [c for c in df.columns if "FEC" in c.upper()][0]
    df["Fecha_DT"] = pd.to_datetime(df[col_fecha].astype(str), format="%Y%m%d", errors="coerce")
    df["Fecha Formateada"] = df["Fecha_DT"].dt.strftime("%d/%m/%Y").fillna("Sin Fecha")
    df["Año"] = df["Fecha_DT"].dt.year
    df["Mes"] = df["Fecha_DT"].dt.month
    df["N° Semana"] = df["Fecha_DT"].dt.isocalendar().week
    df["Día"] = df["Fecha_DT"].dt.day

    # 6. Tratamiento de Área
    col_area = "AREA" if "AREA" in df.columns else ("Area" if "Area" in df.columns else None)
    if col_area:
        df["AREA_Limpia"] = df[col_area].fillna("Sin Área").astype(str).str.replace(r"\.0$", "", regex=True)

    # 7. Conversión Numérica Limpia de Unidades y Costo Monetario Directo
    col_unidades = None
    for u in ["Total Unidades", "Total_Unidades", "UNIDADES", "QTY", "CANTIDAD"]:
        if u in df.columns:
            col_unidades = u
            break

    col_costo = None
    for c in ["Precio medio de coste", "Precio_medio_de_coste", "PRECIO", "COSTO", "COSTE", "PRECIO_MEDIO"]:
        if c in df.columns:
            col_costo = c
            break

    if col_unidades:
        df["Total Unidades_Num"] = pd.to_numeric(
            df[col_unidades].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce"
        ).fillna(0)
    else:
        df["Total Unidades_Num"] = 0

    if col_costo:
        df["Costo_Linea"] = pd.to_numeric(
            df[col_costo].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce"
        ).fillna(0)
    else:
        df["Costo_Linea"] = 0
            
    return df

try:
    df = cargar_datos()

    # Sidebar: Filtros laterales
    st.sidebar.header("🔍 Filtros de Búsqueda")

    if "Tienda que Grabo_Limpia" in df.columns:
        tiendas_grabo = sorted([str(x) for x in df["Tienda que Grabo_Limpia"].unique()])
        tienda_grabo_sel = st.sidebar.multiselect("Tienda que Grabó:", tiendas_grabo, default=tiendas_grabo)
        df = df[df["Tienda que Grabo_Limpia"].isin(tienda_grabo_sel)]

    if "AREA_Limpia" in df.columns:
        areas = sorted([str(x) for x in df["AREA_Limpia"].unique()])
        area_sel = st.sidebar.multiselect("Área:", areas, default=areas)
        df = df[df["AREA_Limpia"].isin(area_sel)]

    if "Estado Rectificación" in df.columns:
        estados = sorted([str(x) for x in df["Estado Rectificación"].unique()])
        estado_sel = st.sidebar.multiselect("Estado Rectificación:", estados, default=estados)
        df = df[df["Estado Rectificación"].isin(estado_sel)]

    if "Almacen" in df.columns:
        almacenes = sorted([str(x) for x in df["Almacen"].fillna("Sin Almacén").astype(str).unique()])
        almacen_sel = st.sidebar.multiselect("Almacén:", almacenes, default=almacenes)
        df = df[df["Almacen"].fillna("Sin Almacén").astype(str).isin(almacen_sel)]

    if "Año" in df.columns and df["Año"].notna().any():
        anios = sorted([int(x) for x in df["Año"].dropna().unique()], reverse=True)
        if anios:
            anio_sel = st.sidebar.multiselect("Año:", anios, default=anios)
            df = df[df["Año"].isin(anio_sel) | df["Año"].isna()]

    if "Mes" in df.columns and df["Mes"].notna().any():
        meses = sorted([int(x) for x in df["Mes"].dropna().unique()])
        if meses:
            mes_sel = st.sidebar.multiselect("Mes:", meses, default=meses)
            df = df[df["Mes"].isin(mes_sel) | df["Mes"].isna()]

    if "N° Semana" in df.columns and df["N° Semana"].notna().any():
        semanas = sorted([int(x) for x in df["N° Semana"].dropna().unique()])
        if semanas:
            semana_sel = st.sidebar.multiselect("N° Semana:", semanas, default=semanas)
            df = df[df["N° Semana"].isin(semana_sel) | df["N° Semana"].isna()]

    if "Día" in df.columns and df["Día"].notna().any():
        dias = sorted([int(x) for x in df["Día"].dropna().unique()])
        if dias:
            dia_sel = st.sidebar.multiselect("Día del Mes:", dias, default=dias)
            df = df[df["Día"].isin(dia_sel) | df["Día"].isna()]

    # CÁLCULO DE UNIDADES Y PORCENTAJES POR TIENDA
    if "Tienda que Grabo_Limpia" in df.columns and "Estado Rectificación" in df.columns:
        df_rect_all = df[df["Estado Rectificación"] != "N - Nulo"].copy()

        base_t = df.groupby("Tienda que Grabo_Limpia", as_index=False).agg(
            unidades_despachadas=("Total Unidades_Num", "sum")
        )
        piv_t = df_rect_all.groupby(["Tienda que Grabo_Limpia", "Estado Rectificación"])["Total Unidades_Num"].sum().unstack(fill_value=0)

        tab_t = base_t.merge(piv_t, on="Tienda que Grabo_Limpia", how="left").fillna(0)
        for est_col in ["Confirmada", "Pendientes", "Anuladas", "Automática"]:
            if est_col not in tab_t.columns:
                tab_t[est_col] = 0

        tab_t["unidades_reclamadas_totales"] = tab_t["Confirmada"] + tab_t["Pendientes"] + tab_t["Anuladas"] + tab_t["Automática"]
        tab_t["unidades_efectivas"] = tab_t["Confirmada"] + tab_t["Automática"]
        
        tab_t["pct_rectificadas_num"] = (tab_t["unidades_efectivas"] / tab_t["unidades_despachadas"]) * 100
        tab_t["pct_rectificadas_num"] = tab_t["pct_rectificadas_num"].fillna(0)

        # CÁLCULO DE PERCENTILES P70 Y P90
        p70 = float(tab_t["pct_rectificadas_num"].quantile(0.70))
        p90 = float(tab_t["pct_rectificadas_num"].quantile(0.90))

        def calificar_icono(pct):
            if pct > p90 and p90 > 0:
                return "🔴"
            elif pct >= p70 and p70 > 0:
                return "🟡"
            else:
                return "🟢"

        def calificar_texto(pct):
            if pct > p90 and p90 > 0:
                return f"🔴 Alta Insatisfacción (>{p90:.2f}%)"
            elif pct >= p70 and p70 > 0:
                return f"🟡 Media Insatisfacción ({p70:.2f}% - {p90:.2f}%)"
            else:
                return f"🟢 Baja Insatisfacción (<{p70:.2f}%)"

        tab_t["Semaforo_Icono"] = tab_t["pct_rectificadas_num"].apply(calificar_icono)
        tab_t["Semaforo_Texto"] = tab_t["pct_rectificadas_num"].apply(calificar_texto)

        total_tiendas_count = len(tab_t)
        cant_rojas = (tab_t["pct_rectificadas_num"] > p90).sum() if p90 > 0 else 0
        cant_amarillas = ((tab_t["pct_rectificadas_num"] >= p70) & (tab_t["pct_rectificadas_num"] <= p90)).sum() if p70 > 0 else 0
        cant_verdes = (tab_t["pct_rectificadas_num"] < p70).sum() if p70 > 0 else total_tiendas_count

        pct_rojas = (cant_rojas / total_tiendas_count * 100) if total_tiendas_count > 0 else 0
        pct_amarillas = (cant_amarillas / total_tiendas_count * 100) if total_tiendas_count > 0 else 0
        pct_verdes = (cant_verdes / total_tiendas_count * 100) if total_tiendas_count > 0 else 0
    else:
        tab_t = pd.DataFrame()
        p70, p90 = 0.0, 0.0
        total_tiendas_count, cant_rojas, cant_amarillas, cant_verdes = 0, 0, 0, 0
        pct_rojas, pct_amarillas, pct_verdes = 0, 0, 0

    # Pestañas principales
    tab_resumen, tab_graficos, tab_tiendas, tab_notas = st.tabs([
        "📊 Resumen General", 
        "📈 Visualización Temporal", 
        "🏪 Detalle por Tienda (Unidades)",
        "📋 Análisis por Cantidad de Notas"
    ])

    with tab_resumen:
        st.subheader("📌 Métricas Generales: Unidades Despachadas vs. Rectificadas")
        
        unidades_despachadas = int(df["Total Unidades_Num"].sum(skipna=True))
        
        unidades_confirmadas = int(df[df["Estado Rectificación"] == "Confirmada"]["Total Unidades_Num"].sum(skipna=True))
        unidades_pendientes = int(df[df["Estado Rectificación"] == "Pendientes"]["Total Unidades_Num"].sum(skipna=True))
        unidades_anuladas = int(df[df["Estado Rectificación"] == "Anuladas"]["Total Unidades_Num"].sum(skipna=True))
        unidades_automaticas = int(df[df["Estado Rectificación"] == "Automática"]["Total Unidades_Num"].sum(skipna=True))
        
        unidades_rectificadas_efectivas = unidades_confirmadas + unidades_automaticas
        unidades_reclamadas_totales = unidades_rectificadas_efectivas + unidades_pendientes + unidades_anuladas
        
        costo_rectificadas_efectivas = float(df[df["Estado Rectificación"].isin(["Confirmada", "Automática"])]["Costo_Linea"].sum(skipna=True))

        pct_rectificadas_global = (unidades_rectificadas_efectivas / unidades_despachadas * 100) if unidades_despachadas > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Unidades Despachadas", f"{unidades_despachadas:,}")
        m2.metric("Unidades Rectificadas Efectivas (M + A)", f"{unidades_rectificadas_efectivas:,}")
        m3.metric("% Unidades Rectificadas Efectivas", f"{pct_rectificadas_global:.2f}%", help="Fórmula: (Confirmadas M + Automáticas A) / Unidades Despachadas")
        m4.metric("Costo Rectificaciones Efectivas", f"")

        st.caption(f"ℹ️ **Aclaración de Unidades:** Se registraron **{unidades_reclamadas_totales:,}** unidades reclamadas en total (incluyendo {unidades_anuladas:,} anuladas y {unidades_pendientes:,} pendientes). El porcentaje del **{pct_rectificadas_global:.2f}%** se calcula sobre las **{unidades_rectificadas_efectivas:,}** unidades efectivamente rectificadas (Confirmadas + Automáticas).")

        st.markdown("---")

        st.subheader("🚦 Distribución de Tiendas por Nivel de Insatisfacción (Semáforo Estadístico)")
        
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Total Tiendas Analizadas", f"{total_tiendas_count}")
        s2.metric(
            f"🔴 Alta Insatisfacción (>{p90:.2f}%)", 
            f"{cant_rojas} ({pct_rojas:.1f}%)",
            help="Clasificación basada en el percentil 90 (P90) del período. Aísla al 10% de las tiendas con desvíos más críticos de la cadena."
        )
        s3.metric(
            f"🟡 Media Insatisfacción ({p70:.2f}% - {p90:.2f}%)", 
            f"{cant_amarillas} ({pct_amarillas:.1f}%)",
            help="Clasificación ubicada entre los percentiles P70 y P90 del período. Representa al 20% de las tiendas en zona intermedia de seguimiento."
        )
        s4.metric(
            f"🟢 Baja Insatisfacción (<{p70:.2f}%)", 
            f"{cant_verdes} ({pct_verdes:.1f}%)",
            help="Clasificación hasta el percentil 70 (P70) del período. Agrupa al 70% de las tiendas con mejor desempeño y desvíos dentro de tolerancias operativas."
        )

        if not tab_t.empty:
            col_chart, col_empty = st.columns([1, 1])
            with col_chart:
                df_sem = tab_t["Semaforo_Texto"].value_counts().reset_index()
                df_sem.columns = ["Nivel", "Cantidad"]
                
                colors_map = {
                    f"🔴 Alta Insatisfacción (>{p90:.2f}%)": "#CC0000",
                    f"🟡 Media Insatisfacción ({p70:.2f}% - {p90:.2f}%)": "#F1C232",
                    f"🟢 Baja Insatisfacción (<{p70:.2f}%)": "#38761D"
                }

                fig_donut = px.pie(
                    df_sem, 
                    names="Nivel", 
                    values="Cantidad", 
                    hole=0.4,
                    color="Nivel",
                    color_discrete_map=colors_map,
                    title="Proporción de Tiendas por Semáforo Estadístico"
                )
                fig_donut.update_traces(textinfo="percent+value")
                fig_donut.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_donut, width="stretch", key="grafico_semaforo_donut")

        st.markdown("---")

        st.subheader("📊 Desglose de Unidades por Estado de Rectificación")
        e1, e2, e3, e4, e5 = st.columns(5)
        if "Estado Rectificación" in df.columns:
            unidades_nulas = int(df[df["Estado Rectificación"] == "N - Nulo"]["Total Unidades_Num"].sum(skipna=True))
            e1.metric("Confirmadas (M)", f"{unidades_confirmadas:,}")
            e2.metric("Anuladas (R)", f"{unidades_anuladas:,}")
            e3.metric("Pendientes (P)", f"{unidades_pendientes:,}")
            e4.metric("Automáticas (A)", f"{unidades_automaticas:,}")
            e5.metric("Nulas / Vacías (N)", f"{unidades_nulas:,}")

    with tab_graficos:
        st.subheader("📈 Análisis de Tendencias Temporales por Unidades")
        
        opciones_eje_x = {
            "Año": "Año",
            "Mes": "Mes",
            "Semana": "N° Semana",
            "Fecha": "Fecha Formateada"
        }
        
        nivel_seleccionado = st.selectbox(
            "Nivel de detalle para el Eje X de los gráficos:",
            options=list(opciones_eje_x.keys()),
            index=1,
            key="select_nivel_eje_x"
        )
        
        col_eje_x = opciones_eje_x[nivel_seleccionado]

        c1, c2 = st.columns(2)

        if col_eje_x in df.columns:
            df_graf = df[df[col_eje_x].notna()].copy()
            
            if nivel_seleccionado == "Fecha":
                grouped = df_graf.groupby(["Fecha_DT", col_eje_x], as_index=False).agg(
                    unidades_despachadas=("Total Unidades_Num", "sum"),
                    unidades_rectificadas=("Total Unidades_Num", lambda x: x[df_graf.loc[x.index, "Estado Rectificación"].isin(["Confirmada", "Automática"])].sum())
                )
                grouped = grouped.sort_values(by="Fecha_DT").reset_index(drop=True)
            else:
                grouped = df_graf.groupby(col_eje_x, as_index=False).agg(
                    unidades_despachadas=("Total Unidades_Num", "sum"),
                    unidades_rectificadas=("Total Unidades_Num", lambda x: x[df_graf.loc[x.index, "Estado Rectificación"].isin(["Confirmada", "Automática"])].sum())
                )
                grouped = grouped.sort_values(by=col_eje_x).reset_index(drop=True)

            grouped["pct_rectificadas"] = (grouped["unidades_rectificadas"] / grouped["unidades_despachadas"]) * 100
            grouped["pct_rectificadas"] = grouped["pct_rectificadas"].fillna(0)
            eje_x_labels = grouped[col_eje_x].astype(str)

            with c1:
                st.markdown(f"**Unidades despachadas vs % unidades rectificadas efectivas (M+A)**")
                fig1 = go.Figure()

                fig1.add_trace(go.Bar(
                    x=eje_x_labels,
                    y=grouped["unidades_despachadas"],
                    name="Unidades despachadas",
                    marker_color="#E06666",
                    text=[f"{int(v):,}" for v in grouped["unidades_despachadas"]],
                    textposition="auto",
                    textfont=dict(color="#262626"),
                    hovertemplate="Unidades despachadas: %{y:,}<extra></extra>"
                ))

                fig1.add_trace(go.Scatter(
                    x=eje_x_labels,
                    y=grouped["pct_rectificadas"],
                    name="% unidades rectificadas (M+A)",
                    mode="lines+markers+text",
                    text=[f"{pct:.2f}%" for pct in grouped["pct_rectificadas"]],
                    textposition="top center",
                    textfont=dict(size=10, color="#262626"),
                    line=dict(color="#1155CC", width=3),
                    marker=dict(color="#1155CC", size=7),
                    yaxis="y2",
                    hovertemplate="% Rectificados: %{y:.2f}%<extra></extra>"
                ))

                fig1.update_layout(
                    template="streamlit",
                    font=dict(color="#262626"),
                    xaxis=dict(
                        title=dict(text=nivel_seleccionado, font=dict(color="#262626")), 
                        type="category",
                        categoryorder="array",
                        categoryarray=list(eje_x_labels),
                        tickangle=-45, 
                        tickfont=dict(size=10, color="#262626")
                    ),
                    yaxis=dict(title="", showgrid=True, tickformat=",", tickfont=dict(color="#262626")),
                    yaxis2=dict(title="", overlaying="y", side="right", ticksuffix=" %", showgrid=False, tickfont=dict(color="#262626")),
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="left", 
                        x=0,
                        font=dict(size=12, color="#262626")
                    ),
                    margin=dict(l=20, r=20, t=40, b=30),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig1, width="stretch", key="grafico_lineas_despachadas")

            if "Estado Rectificación" in df_graf.columns:
                df_rect = df_graf[df_graf["Estado Rectificación"].isin(["Anuladas", "Confirmada", "Pendientes"])].copy()
                
                if not df_rect.empty:
                    if nivel_seleccionado == "Fecha":
                        pivot_rect = df_rect.groupby(["Fecha_DT", col_eje_x, "Estado Rectificación"])["Total Unidades_Num"].sum().unstack(fill_value=0)
                        pivot_rect = pivot_rect.reset_index().sort_values(by="Fecha_DT").set_index(col_eje_x).drop(columns=["Fecha_DT"])
                    else:
                        pivot_rect = df_rect.groupby([col_eje_x, "Estado Rectificación"])["Total Unidades_Num"].sum().unstack(fill_value=0)
                        pivot_rect = pivot_rect.sort_index()

                    pivot_pct = pivot_rect.div(pivot_rect.sum(axis=1), axis=0) * 100
                    pivot_pct = pivot_pct.fillna(0)
                    eje_x_rect_labels = pivot_pct.index.astype(str)

                    with c2:
                        st.markdown(f"**Resolución unidades rectificadas**")
                        fig2 = go.Figure()

                        colors = {
                            "Anuladas": "#E69138",
                            "Confirmada": "#4A90E2",
                            "Pendientes": "#F1C232"
                        }

                        for estado in ["Anuladas", "Confirmada", "Pendientes"]:
                            if estado in pivot_pct.columns:
                                fig2.add_trace(go.Bar(
                                    x=eje_x_rect_labels,
                                    y=pivot_pct[estado],
                                    name=estado,
                                    marker_color=colors.get(estado, "#CCCCCC"),
                                    text=[f"{v:.2f}%" if v > 0 else "" for v in pivot_pct[estado]],
                                    textposition="inside",
                                    textfont=dict(color="#000000", size=10)
                                ))

                        fig2.update_layout(
                            template="streamlit",
                            barmode="stack",
                            font=dict(color="#262626"),
                            xaxis=dict(
                                title=dict(text=nivel_seleccionado, font=dict(color="#262626")), 
                                type="category",
                                categoryorder="array",
                                categoryarray=list(eje_x_rect_labels),
                                tickangle=-45, 
                                tickfont=dict(size=10, color="#262626")
                            ),
                            yaxis=dict(ticksuffix="%", range=[0, 100], showgrid=True, tickfont=dict(color="#262626")),
                            legend=dict(
                                orientation="h", 
                                yanchor="bottom", 
                                y=1.02, 
                                xanchor="left", 
                                x=0,
                                font=dict(size=12, color="#262626")
                            ),
                            margin=dict(l=20, r=20, t=40, b=30),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)"
                        )
                        st.plotly_chart(fig2, width="stretch", key="grafico_resolucion_rectificadas")
                else:
                    with c2:
                        st.markdown(f"**Resolución unidades rectificadas**")
                        st.info("No hay rectificaciones registradas para el nivel de filtro seleccionado.")

    # HOJA 3: DETALLE POR TIENDA
    with tab_tiendas:
        st.subheader("🏪 Detalle de Rectificaciones por Tienda (Unidades)")
        
        st.info(f"💡 **Leyenda del Semáforo de Insatisfacción:** Se calcula con el **% Unidades Rectificadas Efectivas** (Confirmadas M + Automáticas A / Despachadas). Umbrales: 🔴 **Alta** (>{p90:.2f}%) &nbsp;&nbsp;|&nbsp;&nbsp; 🟡 **Media** ({p70:.2f}% - {p90:.2f}%) &nbsp;&nbsp;|&nbsp;&nbsp; 🟢 **Baja** (<{p70:.2f}%)")
        
        if not tab_t.empty:
            tab_t_sorted = tab_t.sort_values(by="pct_rectificadas_num", ascending=False).reset_index(drop=True)

            tot_unidades_despachadas = int(df["Total Unidades_Num"].sum(skipna=True))
            tot_unidades_confirmadas = int(df[df["Estado Rectificación"] == "Confirmada"]["Total Unidades_Num"].sum(skipna=True))
            tot_unidades_pendientes = int(df[df["Estado Rectificación"] == "Pendientes"]["Total Unidades_Num"].sum(skipna=True))
            tot_unidades_anuladas = int(df[df["Estado Rectificación"] == "Anuladas"]["Total Unidades_Num"].sum(skipna=True))
            tot_unidades_automaticas = int(df[df["Estado Rectificación"] == "Automática"]["Total Unidades_Num"].sum(skipna=True))
            tot_unidades_reclamadas_totales = tot_unidades_confirmadas + tot_unidades_pendientes + tot_unidades_anuladas + tot_unidades_automaticas
            tot_unidades_efectivas = tot_unidades_confirmadas + tot_unidades_automaticas
            tot_pct_rectificados = (tot_unidades_efectivas / tot_unidades_despachadas * 100) if tot_unidades_despachadas > 0 else 0

            tab_t_sorted = tab_t_sorted.rename(columns={
                "Tienda que Grabo_Limpia": "Tienda",
                "Semaforo_Icono": "Nivel Insatisf.",
                "unidades_despachadas": "Unid. Despachadas",
                "unidades_reclamadas_totales": "Unid. Reclamadas Totales",
                "unidades_efectivas": "Unid. Rectif. Efectivas",
                "pct_rectificadas_num": "% Rectif. Efectivo",
                "Confirmada": "Confirmadas (M)",
                "Pendientes": "Pendientes (P)",
                "Anuladas": "Anuladas (R)",
                "Automática": "Automáticas (A)"
            })

            cols_select = [
                "Tienda", "Nivel Insatisf.", "Unid. Despachadas", 
                "Unid. Reclamadas Totales", "Unid. Rectif. Efectivas", 
                "Confirmadas (M)", "Pendientes (P)", "Anuladas (R)", "Automáticas (A)", 
                "% Rectif. Efectivo"
            ]

            df_tiendas_disp = tab_t_sorted[cols_select].copy()

            fila_total = pd.DataFrame([{
                "Tienda": "Total",
                "Nivel Insatisf.": "—",
                "Unid. Despachadas": int(tot_unidades_despachadas),
                "Unid. Reclamadas Totales": int(tot_unidades_reclamadas_totales),
                "Unid. Rectif. Efectivas": int(tot_unidades_efectivas),
                "Confirmadas (M)": int(tot_unidades_confirmadas),
                "Pendientes (P)": int(tot_unidades_pendientes),
                "Anuladas (R)": int(tot_unidades_anuladas),
                "Automáticas (A)": int(tot_unidades_automaticas),
                "% Rectif. Efectivo": tot_pct_rectificados
            }])

            df_final_tiendas = pd.concat([df_tiendas_disp, fila_total], ignore_index=True)

            st.dataframe(
                df_final_tiendas, 
                width="stretch", 
                hide_index=True, 
                key="tabla_resumen_tiendas",
                column_config={
                    "Tienda": st.column_config.Column("Tienda"),
                    "Nivel Insatisf.": st.column_config.Column("Nivel Insatisf."),
                    "Unid. Despachadas": st.column_config.NumberColumn("Unid. Despachadas", format="%d"),
                    "Unid. Reclamadas Totales": st.column_config.NumberColumn("Unid. Reclamadas Totales", format="%d"),
                    "Unid. Rectif. Efectivas": st.column_config.NumberColumn("Unid. Rectif. Efectivas (M+A)", format="%d"),
                    "Confirmadas (M)": st.column_config.NumberColumn("Confirmadas (M)", format="%d"),
                    "Pendientes (P)": st.column_config.NumberColumn("Pendientes (P)", format="%d"),
                    "Anuladas (R)": st.column_config.NumberColumn("Anuladas (R)", format="%d"),
                    "Automáticas (A)": st.column_config.NumberColumn("Automáticas (A)", format="%d"),
                    "% Rectif. Efectivo": st.column_config.NumberColumn("% Rectif. Efectivo", format="%.2f %%")
                }
            )

    # HOJA 4: ANÁLISIS DE NOTAS / OPERACIONES
    with tab_notas:
        st.subheader("📋 Análisis de Carga Administrativa por Cantidad de Notas / Operaciones")
        st.caption("Esta sección analiza la frecuencia de reclamos creados por las tiendas (Cuenta de Operaciones/Notas), permitiendo medir el impacto operativo independientemente del volumen de unidades.")

        df_rect_notas = df[df["Estado Rectificación"] != "N - Nulo"]
        
        cant_confirmadas_n = (df["Estado Rectificación"] == "Confirmada").sum()
        cant_anuladas_n = (df["Estado Rectificación"] == "Anuladas").sum()
        cant_pendientes_n = (df["Estado Rectificación"] == "Pendientes").sum()
        cant_automaticas_n = (df["Estado Rectificación"] == "Automática").sum()
        cant_totales_n = cant_confirmadas_n + cant_anuladas_n + cant_pendientes_n + cant_automaticas_n

        n1, n2, n3, n4, n5 = st.columns(5)
        n1.metric("Total Notas Creadas", f"{cant_totales_n:,}")
        n2.metric("Confirmadas (M)", f"{cant_confirmadas_n:,}")
        n3.metric("Anuladas (R)", f"{cant_anuladas_n:,}")
        n4.metric("Pendientes (P)", f"{cant_pendientes_n:,}")
        n5.metric("Automáticas (A)", f"{cant_automaticas_n:,}")

        st.markdown("---")

        st.markdown("**Top 10 Tiendas con Mayor Cantidad de Notas (Desglose por Estado de Rectificación)**")
        
        top_tiendas_counts = df_rect_notas["Tienda que Grabo_Limpia"].value_counts().head(10)
        top_tiendas_list = top_tiendas_counts.index.tolist()
        
        df_top_stacked = df_rect_notas[df_rect_notas["Tienda que Grabo_Limpia"].isin(top_tiendas_list)]

        grouped_stacked = df_top_stacked.groupby(["Tienda que Grabo_Limpia", "Estado Rectificación"]).size().reset_index(name="Notas")
        grouped_stacked["Tienda_Label"] = "Tienda " + grouped_stacked["Tienda que Grabo_Limpia"].astype(str)
        
        orden_tiendas = ["Tienda " + str(x) for x in top_tiendas_list]

        fig_top_stacked = px.bar(
            grouped_stacked,
            y="Tienda_Label",
            x="Notas",
            color="Estado Rectificación",
            orientation="h",
            text="Notas",
            color_discrete_map={
                "Confirmada": "#4A90E2",
                "Anuladas": "#E69138",
                "Pendientes": "#F1C232",
                "Automática": "#38761D"
            },
            category_orders={"Tienda_Label": orden_tiendas}
        )

        fig_top_stacked.update_traces(textposition="inside", textfont=dict(color="#FFFFFF", size=11))
        fig_top_stacked.update_layout(
            barmode="stack",
            height=450,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Cantidad de Notas / Operaciones", showgrid=True),
            yaxis=dict(title="", autorange="reversed"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="right",
                x=1,
                title=dict(text="Estado Rectificación:")
            ),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_top_stacked, width="stretch", key="grafico_top_tiendas_stacked_full")

        st.markdown("---")
        st.markdown("##### 🏪 Tabla Detalle de Notas Creadas por Tienda")

        pivot_notas = df_rect_notas.groupby(["Tienda que Grabo_Limpia", "Estado Rectificación"]).size().unstack(fill_value=0)
        for est_c in ["Confirmada", "Pendientes", "Anuladas", "Automática"]:
            if est_c not in pivot_notas.columns:
                pivot_notas[est_c] = 0

        pivot_notas["Total Notas"] = pivot_notas["Confirmada"] + pivot_notas["Pendientes"] + pivot_notas["Anuladas"] + pivot_notas["Automática"]
        pivot_notas = pivot_notas.sort_values(by="Total Notas", ascending=False).reset_index()

        pivot_notas = pivot_notas.rename(columns={
            "Tienda que Grabo_Limpia": "Tienda",
            "Confirmada": "Notas Confirmadas (M)",
            "Pendientes": "Notas Pendientes (P)",
            "Anuladas": "Notas Anuladas (R)",
            "Automática": "Notas Automáticas (A)"
        })

        cols_notas = ["Tienda", "Total Notas", "Notas Confirmadas (M)", "Notas Pendientes (P)", "Notas Anuladas (R)", "Notas Automáticas (A)"]
        df_disp_notas = pivot_notas[cols_notas].copy()

        fila_tot_notas = pd.DataFrame([{
            "Tienda": "Total",
            "Total Notas": int(cant_totales_n),
            "Notas Confirmadas (M)": int(cant_confirmadas_n),
            "Notas Pendientes (P)": int(cant_pendientes_n),
            "Notas Anuladas (R)": int(cant_anuladas_n),
            "Notas Automáticas (A)": int(cant_automaticas_n)
        }])

        df_final_notas = pd.concat([df_disp_notas, fila_tot_notas], ignore_index=True)

        st.dataframe(
            df_final_notas,
            width="stretch",
            hide_index=True,
            key="tabla_detalle_notas_tienda",
            column_config={
                "Tienda": st.column_config.Column("Tienda"),
                "Total Notas": st.column_config.NumberColumn("Total Notas", format="%d"),
                "Notas Confirmadas (M)": st.column_config.NumberColumn("Notas Confirmadas (M)", format="%d"),
                "Notas Pendientes (P)": st.column_config.NumberColumn("Notas Pendientes (P)", format="%d"),
                "Notas Anuladas (R)": st.column_config.NumberColumn("Notas Anuladas (R)", format="%d"),
                "Notas Automáticas (A)": st.column_config.NumberColumn("Notas Automáticas (A)", format="%d")
            }
        )

except FileNotFoundError as e:
    st.error(f"⚠️ {e}")
except Exception as e:
    st.error(f"Error procesando los datos: {e}")
