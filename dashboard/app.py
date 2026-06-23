"""
Dashboard Adolfo Dominguez
==========================
Lee la coleccion procesada desde MongoDB (actualizada cada lunes por el ETL).
Muestra Ventas, Stock, Sell-through y Low Rotation, con vista de SEMANA y ACUMULADO del anio.

Ejecutar:  streamlit run app.py
"""

import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
from pymongo import MongoClient

st.set_page_config(
    page_title="Adolfo Dominguez - Dashboard",
    page_icon="·",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Estilo ejecutivo: fondo blanco, tipografia limpia, paleta sobria
# ----------------------------------------------------------------------------
INK = "#1A1A2E"        # texto principal (casi negro azulado)
MUTED = "#6B7280"      # texto secundario
ACCENT = "#1F3A5F"     # azul marino ejecutivo
LINE = "#E5E7EB"       # bordes / divisores

# Paleta de graficos: neutros elegantes con un acento marino
PALETTE = ["#1F3A5F", "#3D6098", "#8A9BB5", "#C2A878", "#A8443B", "#5C5C70"]

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, sans-serif;
        background-color: #FFFFFF;
        color: {INK};
    }}
    .stApp {{ background-color: #FFFFFF; }}

    /* Sidebar claro */
    section[data-testid="stSidebar"] {{
        background-color: #FAFAFB;
        border-right: 1px solid {LINE};
    }}

    /* Titulos */
    h1 {{
        font-weight: 700; letter-spacing: -0.02em; color: {INK};
        font-size: 1.9rem !important;
    }}
    h2, h3 {{ font-weight: 600; color: {INK}; letter-spacing: -0.01em; }}

    /* KPIs como tarjetas */
    div[data-testid="stMetric"] {{
        background: #FFFFFF;
        border: 1px solid {LINE};
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(16,24,40,0.04);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {MUTED}; font-weight: 500; font-size: 0.8rem;
        text-transform: uppercase; letter-spacing: 0.04em;
    }}
    div[data-testid="stMetricValue"] {{
        color: {INK}; font-weight: 700; font-size: 1.7rem;
    }}

    /* Divisores mas suaves */
    hr {{ border-color: {LINE}; }}

    /* Tablas */
    div[data-testid="stDataFrame"] {{
        border: 1px solid {LINE}; border-radius: 10px;
    }}

    /* Radio horizontal mas limpio */
    div[role="radiogroup"] label {{ color: {INK}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Template de Plotly propio: blanco, limpio, ejecutivo (no muta el built-in)
import copy
_exec = copy.deepcopy(pio.templates["plotly_white"])
_exec.layout.font.family = "Inter, sans-serif"
_exec.layout.font.color = INK
_exec.layout.colorway = PALETTE
_exec.layout.paper_bgcolor = "#FFFFFF"
_exec.layout.plot_bgcolor = "#FFFFFF"
_exec.layout.title.font.size = 16
_exec.layout.xaxis.gridcolor = LINE
_exec.layout.yaxis.gridcolor = LINE
_exec.layout.margin = dict(l=10, r=10, t=30, b=10)
pio.templates["exec"] = _exec
pio.templates.default = "exec"

def _secret(nombre, default=None):
    """Lee de st.secrets (Streamlit Cloud) o de variables de entorno."""
    try:
        if nombre in st.secrets:
            return st.secrets[nombre]
    except Exception:
        pass
    return os.getenv(nombre, default)


MONGO_URI = _secret("MONGO_URI", "")
MONGO_DB = "adolfo_dominguez"
COL_VENTAS = "dashboard_ad"        # serie diaria de ventas (con Dia/Mes/Anio)
COL_STOCK = "dashboard_ad_stock"   # snapshot de stock (sin fecha)


@st.cache_data(ttl=3600)
def cargar(coleccion: str) -> pd.DataFrame:
    client = MongoClient(MONGO_URI)
    docs = list(client[MONGO_DB][coleccion].find({}, {"_id": 0}))
    client.close()
    return pd.DataFrame(docs)


# ----------------------------------------------------------------------------
# Acceso con contraseña (se configura en st.secrets["APP_PASSWORD"] o variable de entorno)
# ----------------------------------------------------------------------------
def _check_password() -> bool:
    clave = _secret("APP_PASSWORD")
    if not clave:
        st.error("El dashboard no tiene contraseña configurada (APP_PASSWORD).")
        st.stop()
    if st.session_state.get("auth_ok"):
        return True

    def _validar():
        st.session_state["auth_ok"] = st.session_state.get("pwd_input") == clave

    st.markdown("#### Acceso al dashboard")
    st.text_input("Contraseña", type="password", key="pwd_input", on_change=_validar)
    if st.session_state.get("auth_ok") is False:
        st.error("Contraseña incorrecta.")
    return bool(st.session_state.get("auth_ok"))


if not _check_password():
    st.stop()

if not MONGO_URI:
    st.error("Falta configurar MONGO_URI (en st.secrets o variable de entorno).")
    st.stop()

# Auto-recarga: el ETL actualiza MongoDB; refrescamos la vista cada hora para que
# el dashboard cargue la data nueva sin reinicio manual (combinado con el TTL del cache).
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=3600 * 1000, key="auto_recarga")
except Exception:
    pass

ventas = cargar(COL_VENTAS)
stock = cargar(COL_STOCK)

st.markdown(
    f"<div style='color:{ACCENT};font-weight:600;font-size:0.8rem;"
    f"letter-spacing:0.12em;text-transform:uppercase;'>Adolfo Domínguez</div>",
    unsafe_allow_html=True,
)
tcol, bcol = st.columns([6, 1])
tcol.title("Ventas · Stock · Sell-through · Low Rotation")
if bcol.button("Actualizar datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if ventas.empty and stock.empty:
    st.warning("No hay datos en MongoDB todavia. Corre el ETL primero.")
    st.stop()

# Fecha desde Dia/Mes/Anio (serie diaria de ventas)
if {"Anio", "Mes", "Dia"}.issubset(ventas.columns):
    ventas["Fecha"] = pd.to_datetime(
        dict(year=ventas["Anio"], month=ventas["Mes"], day=ventas["Dia"]),
        errors="coerce")
else:
    ventas["Fecha"] = pd.NaT

ATTRS = [c for c in ["u_categoria", "u_genero", "u_familia", "u_descrip_color"]
         if c in ventas.columns or c in stock.columns]


def opciones(col):
    partes = [d[col] for d in (ventas, stock) if col in d.columns]
    if not partes:
        return []
    return sorted(pd.concat(partes).dropna().astype(str).unique())


# --- Filtros ARRIBA (Bodega/atributos son filtros; el analisis se agrupa por estilo) ---
fmin = ventas["Fecha"].min()
fmax = ventas["Fecha"].max()
hay_fechas = pd.notna(fmin) and pd.notna(fmax)
fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([1, 1, 1, 1, 1, 1])
bodegas = fc1.multiselect("Bodega", opciones("Bodega"))
estilos = fc2.multiselect("Estilo", opciones("u_estilo"))
generos = fc3.multiselect("Género", opciones("u_genero"))
familias = fc4.multiselect("Familia", opciones("u_familia"))
if hay_fechas:
    f_ini = fc5.date_input("Fecha inicio", value=fmin.date(),
                           min_value=fmin.date(), max_value=fmax.date())
    f_fin = fc6.date_input("Fecha fin", value=fmax.date(),
                           min_value=fmin.date(), max_value=fmax.date())
else:
    f_ini = f_fin = None
solo_low = st.checkbox("Solo Low Rotation")

# Aplicar filtros: atributos a ventas Y stock; la fecha solo a ventas
v, s = ventas.copy(), stock.copy()
for col, sel in [("Bodega", bodegas), ("u_estilo", estilos),
                 ("u_genero", generos), ("u_familia", familias)]:
    if sel:
        if col in v.columns: v = v[v[col].astype(str).isin(sel)]
        if col in s.columns: s = s[s[col].astype(str).isin(sel)]

if f_ini is not None and f_fin is not None and v["Fecha"].notna().any():
    ini, fin = pd.Timestamp(f_ini), pd.Timestamp(f_fin)
    if ini > fin:
        st.warning("La fecha de inicio es posterior a la fecha fin; revisa el rango.")
        ini, fin = fin, ini
    v = v[(v["Fecha"] >= ini) & (v["Fecha"] <= fin)]
    st.caption(f"Periodo: {ini:%d/%m/%Y} a {fin:%d/%m/%Y}")

# --- CRUCE ventas <-> stock por ESTILO (el join se hace aqui, en Streamlit) ---
def attrs_de(d):
    return [c for c in ATTRS if c in d.columns]


attr_src = (pd.concat([v[["u_estilo"] + attrs_de(v)], s[["u_estilo"] + attrs_de(s)]],
                      ignore_index=True).drop_duplicates("u_estilo"))
v_agg = v.groupby("u_estilo", as_index=False, dropna=False).agg(
    Ventas_Cantidad=("Ventas_Cantidad", "sum"), Ventas_USD=("Ventas_USD", "sum"))
s_agg = s.groupby("u_estilo", as_index=False, dropna=False).agg(Stock=("Stock", "sum"))
e = (v_agg.merge(s_agg, on="u_estilo", how="outer")
          .merge(attr_src, on="u_estilo", how="left"))
for c in ["Ventas_Cantidad", "Ventas_USD", "Stock"]:
    e[c] = pd.to_numeric(e[c], errors="coerce").fillna(0.0)

den = e["Ventas_Cantidad"] + e["Stock"]
e["SellThrough"] = (e["Ventas_Cantidad"] / den.where(den != 0)).fillna(0)
e["Low_Rotation"] = (e["Stock"] > 0) & (e["SellThrough"] < 0.20)

# --- Severidad de la alerta de baja rotacion ---
# Critico: stock vivo y CERO ventas | Alto: sell-through < 10% | Medio: < 20%
def _severidad(row):
    if row["Stock"] <= 0 or row["SellThrough"] >= 0.20:
        return ""
    if row["Ventas_Cantidad"] == 0:
        return "Crítico"
    if row["SellThrough"] < 0.10:
        return "Alto"
    return "Medio"

e["Severidad"] = e.apply(_severidad, axis=1)
# Orden de severidad para ordenar tabla (Critico primero)
_SEV_ORDEN = {"Crítico": 0, "Alto": 1, "Medio": 2, "": 3}
SEV_COLOR = {"Crítico": "#A8443B", "Alto": "#C2A878", "Medio": "#8A9BB5"}

# USD en riesgo (ESTIMADO): el stock no trae precio, usamos el precio promedio
# de venta (USD vendidos / unidades vendidas) x unidades de stock inmovilizado.
_und_vend = e["Ventas_Cantidad"].sum()
_precio_medio = (e["Ventas_USD"].sum() / _und_vend) if _und_vend else 0.0
e["USD_Riesgo"] = e["Stock"] * _precio_medio * e["Low_Rotation"]

if solo_low:
    e = e[e["Low_Rotation"]]

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ventas USD", f"${e['Ventas_USD'].sum():,.0f}")
c2.metric("Unidades vendidas", f"{e['Ventas_Cantidad'].sum():,.0f}")
c3.metric("Stock total", f"{e['Stock'].sum():,.0f}")
st_glob = e["Ventas_Cantidad"].sum() / max(e["Ventas_Cantidad"].sum() + e["Stock"].sum(), 1)
c4.metric("Sell-through", f"{st_glob:.1%}")

st.divider()
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Ventas USD por estilo - top 15")
    g = e.sort_values("Ventas_USD", ascending=False).head(15).copy()
    g["u_estilo"] = g["u_estilo"].astype(str)
    fig = px.bar(g, x="Ventas_USD", y="u_estilo", orientation="h",
                 text=g["Ventas_USD"].map("${:,.0f}".format))
    fig.update_traces(marker_color=ACCENT, textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=None, yaxis_title=None,
                      yaxis=dict(categoryorder="total ascending", type="category"))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Sell-through por estilo - top 15")
    # Solo estilos con stock vivo y con ventas: ahi el sell-through es accionable
    g = e[(e["Stock"] > 0) & (e["Ventas_Cantidad"] > 0)].copy()
    g = g.sort_values("SellThrough", ascending=False).head(15)
    g["u_estilo"] = g["u_estilo"].astype(str)   # codigo -> categoria, no eje numerico
    fig = px.bar(g, x="SellThrough", y="u_estilo", orientation="h",
                 text=g["SellThrough"].map("{:.0%}".format))
    fig.update_traces(marker_color="#3D6098", textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=None, yaxis_title=None, xaxis_tickformat=".0%",
                      yaxis=dict(categoryorder="total ascending", type="category"))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Stock vs Ventas por categoría")
if "u_categoria" in e.columns:
    g = e.groupby("u_categoria", as_index=False).agg(Stock=("Stock", "sum"),
                                                     Ventas=("Ventas_Cantidad", "sum"))
    g = g.melt(id_vars="u_categoria", value_vars=["Stock", "Ventas"],
               var_name="Métrica", value_name="Unidades")
    fig = px.bar(g, x="u_categoria", y="Unidades", color="Métrica", barmode="group",
                 color_discrete_map={"Stock": "#8A9BB5", "Ventas": ACCENT})
    fig.update_layout(xaxis_title=None, yaxis_title=None, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Alertas de baja rotación")
st.caption("Estilos con stock vivo y sell-through bajo. "
           "Crítico: sin ventas · Alto: < 10% · Medio: < 20%")

nivel_alerta = st.multiselect(
    "Filtrar por Alerta", ["Crítico", "Alto", "Medio"],
    help="Muestra solo los estilos de la(s) severidad(es) elegida(s). Vacío = todas.")

low = e[e["Low_Rotation"]].copy()
if nivel_alerta:
    low = low[low["Severidad"].isin(nivel_alerta)]
low["_ord"] = low["Severidad"].map(_SEV_ORDEN).fillna(3)
low = low.sort_values(["_ord", "Stock"], ascending=[True, False]).drop(columns="_ord")

n_total = int(e["Low_Rotation"].sum())
n_crit = int((e["Severidad"] == "Crítico").sum())
n_alto = int((e["Severidad"] == "Alto").sum())
n_medio = int((e["Severidad"] == "Medio").sum())
und_inmov = float(low["Stock"].sum())
usd_riesgo = float(low["USD_Riesgo"].sum())
pct_stock = und_inmov / max(e["Stock"].sum(), 1)

if n_total == 0:
    st.markdown(
        f"<div style='border:1px solid {LINE};border-left:4px solid #4B8B6F;"
        f"border-radius:10px;padding:14px 18px;background:#FBFDFC;color:{INK};'>"
        f"Sin estilos en baja rotación con los filtros actuales.</div>",
        unsafe_allow_html=True,
    )
else:
    # --- Tarjetas de severidad (alineadas con la estetica de los KPIs) ---
    def _tarjeta(label, valor, color, detalle):
        return (
            f"<div style='flex:1;border:1px solid {LINE};border-left:4px solid {color};"
            f"border-radius:12px;padding:16px 18px;background:#FFFFFF;"
            f"box-shadow:0 1px 2px rgba(16,24,40,0.04);'>"
            f"<div style='color:{MUTED};font-size:0.72rem;font-weight:600;"
            f"text-transform:uppercase;letter-spacing:0.05em;'>{label}</div>"
            f"<div style='color:{color};font-size:1.7rem;font-weight:700;"
            f"line-height:1.2;margin-top:4px;'>{valor}</div>"
            f"<div style='color:{MUTED};font-size:0.78rem;margin-top:2px;'>{detalle}</div>"
            f"</div>"
        )

    tarjetas = [
        _tarjeta("Crítico", f"{n_crit}", SEV_COLOR["Crítico"], "stock sin ventas"),
        _tarjeta("Alto", f"{n_alto}", SEV_COLOR["Alto"], "sell-through < 10%"),
        _tarjeta("Medio", f"{n_medio}", SEV_COLOR["Medio"], "sell-through < 20%"),
        _tarjeta("USD en riesgo (est.)", f"${usd_riesgo:,.0f}", ACCENT,
                 f"{und_inmov:,.0f} uds · {pct_stock:.0%} del stock"),
    ]
    st.markdown(
        "<div style='display:flex;gap:14px;margin:6px 0 18px;'>"
        + "".join(tarjetas) + "</div>",
        unsafe_allow_html=True,
    )

    cols_low = [c for c in ["Severidad", "u_estilo", "u_categoria", "Stock",
                            "Ventas_Cantidad", "SellThrough", "USD_Riesgo"]
                if c in low.columns]
    low_disp = low[cols_low].copy()
    low_disp["u_estilo"] = low_disp["u_estilo"].astype(str)

    def _resalta_sev(val):
        color = SEV_COLOR.get(val, MUTED)
        return f"color:{color};font-weight:600;"

    styler = low_disp.style.map(_resalta_sev, subset=["Severidad"])
    st.dataframe(
        styler, use_container_width=True, height=400, hide_index=True,
        column_config={
            "Severidad": "Alerta",
            "u_estilo": "Estilo",
            "u_categoria": "Categoría",
            "Stock": st.column_config.NumberColumn("Stock", format="%d"),
            "Ventas_Cantidad": st.column_config.NumberColumn("Unidades", format="%d"),
            "SellThrough": st.column_config.NumberColumn("Sell-through", format="percent"),
            "USD_Riesgo": st.column_config.NumberColumn("USD en riesgo (est.)", format="$%d"),
        },
    )

st.divider()
st.subheader("Detalle por estilo")
cols_det = [c for c in ["u_estilo"] + ATTRS +
            ["Stock", "Ventas_Cantidad", "Ventas_USD", "SellThrough"] if c in e.columns]
det_disp = e[cols_det].sort_values("Ventas_USD", ascending=False).copy()
det_disp["u_estilo"] = det_disp["u_estilo"].astype(str)
st.dataframe(
    det_disp, use_container_width=True, hide_index=True,
    column_config={
        "u_estilo": "Estilo",
        "u_categoria": "Categoría", "u_genero": "Género",
        "u_familia": "Familia", "u_descrip_color": "Color",
        "Stock": st.column_config.NumberColumn("Stock", format="%d"),
        "Ventas_Cantidad": st.column_config.NumberColumn("Unidades", format="%d"),
        "Ventas_USD": st.column_config.NumberColumn("Ventas USD", format="$%d"),
        "SellThrough": st.column_config.NumberColumn("Sell-through", format="percent"),
    },
)
