
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from db import get_conn, ensure

st.set_page_config(page_title="Cerditos - Gestión Porcina", layout="wide")
import os
import streamlit as st

def check_password():
    expected = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    # Si no hay secreto configurado, no bloqueamos (útil en local)
    if not expected:
        st.warning("APP_PASSWORD no está configurada en Secrets. Acceso libre (modo demo).")
        return True

    if "auth_ok" not in st.session_state:
        st.session_state["auth_ok"] = False

    if st.session_state["auth_ok"]:
        return True

    with st.sidebar:
        st.subheader("Acceso")
        pwd = st.text_input("Contraseña", type="password", placeholder="Ingresa la clave")
        if st.button("Entrar", use_container_width=True):
            if pwd == expected:
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    return False

# Bloquea la app si no pasa la autenticación
if not check_password():
    st.stop()

# (Opcional) botón de salir
with st.sidebar:
    if st.button("Salir"):
        st.session_state["auth_ok"] = False
        st.rerun()

ensure()
conn = get_conn()

def fetch_df(q, params=()):
    return pd.read_sql_query(q, conn, params=params)

def kpi(label, value, help=None):
    st.metric(label, value)
    if help: st.caption(help)

st.sidebar.title("Cerditos 🐷")
page = st.sidebar.selectbox(
    "Navegación",
    ["Dashboard","Animales","Reproducción","Partos","Ventas","Gastos","Alimentos","Reportes","Finanzas (TIR/Payback)"]
)

if page == "Dashboard":
    st.title("Dashboard de Producción y Finanzas")

    inv = fetch_df("SELECT categoria, COUNT(*) n FROM animals WHERE IFNULL(estado,'Activo')='Activo' GROUP BY categoria")
    totals = inv.set_index('categoria')['n'].to_dict() if not inv.empty else {}
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("Animales totales", sum(totals.values()) if totals else 0)
    with c2: kpi("Marranas", totals.get('Marrana',0))
    with c3: kpi("Sementales", totals.get('Semental',0))
    with c4: kpi("Lechones/Engorde", totals.get('Lechon',0)+totals.get('Engorde',0))

    start = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    ingresos = fetch_df("SELECT COALESCE(SUM(precio_total),0) v FROM ventas WHERE fecha>=?", (start,)).iloc[0]['v']
    egresos = fetch_df("SELECT COALESCE(SUM(monto),0) v FROM gastos WHERE fecha>=?", (start,)).iloc[0]['v']
    u = ingresos-egresos
    a,b,c = st.columns(3)
    with a: kpi("Ingresos 90d", f"${ingresos:,.0f}")
    with b: kpi("Gastos 90d", f"${egresos:,.0f}")
    with c: kpi("Utilidad 90d", f"${u:,.0f}")

    st.subheader("Partos esperados (30 días)")
    prox = fetch_df("""
      SELECT a.arete marrana, r.fecha_parto_esperado
      FROM reproducciones r JOIN animals a ON a.id=r.marrana_id
      WHERE DATE(r.fecha_parto_esperado) BETWEEN DATE('now') AND DATE('now','+30 day')
      ORDER BY r.fecha_parto_esperado
    """)
    st.dataframe(prox if not prox.empty else pd.DataFrame(columns=["marrana","fecha_parto_esperado"]), use_container_width=True)

elif page == "Animales":
    st.title("Inventario de Animales")
    with st.expander("➕ Agregar animal", expanded=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            arete = st.text_input("Arete/ID")
            categoria = st.selectbox("Categoría", ["Marrana","Semental","Lechon","Engorde"])
            sexo = st.selectbox("Sexo", ["Hembra","Macho"])
        with c2:
            raza = st.text_input("Raza", value="")
            fecha_nac = st.date_input("Fecha de nacimiento", format="YYYY-MM-DD")
        with c3:
            estado = st.selectbox("Estado", ["Activo","Vendido","Fallecido","Retirado"], index=0)
            notas = st.text_area("Notas", height=80)
        if st.button("Guardar animal"):
            conn.execute("""INSERT OR REPLACE INTO animals(arete,categoria,sexo,raza,fecha_nacimiento,estado,notas)
                            VALUES (?,?,?,?,?,?,?)""",
                         (arete,categoria,sexo,raza,fecha_nac.strftime("%Y-%m-%d"),estado,notas))
            conn.commit()
            st.success("Animal guardado.")

    df = fetch_df("SELECT id,arete,categoria,sexo,raza,fecha_nacimiento,estado FROM animals ORDER BY id DESC")
    st.dataframe(df, use_container_width=True)

elif page == "Reproducción":
    st.title("Gestión Reproductiva")
    marranas = fetch_df("SELECT id, arete FROM animals WHERE categoria='Marrana' AND IFNULL(estado,'Activo')='Activo' ORDER BY arete")
    machos = fetch_df("SELECT id, arete FROM animals WHERE categoria='Semental' AND IFNULL(estado,'Activo')='Activo' ORDER BY arete")

    with st.expander("➕ Registrar monta", expanded=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            marrana_id = st.selectbox("Marrana", marranas['id'].tolist(), format_func=lambda x: marranas.set_index('id').loc[x,'arete'] if not marranas.empty else "")
            macho_id = st.selectbox("Macho (opcional)", [None]+machos['id'].tolist(), format_func=lambda x: "—" if x is None else machos.set_index('id').loc[x,'arete'])
        with c2:
            f_monta = st.date_input("Fecha de monta", format="YYYY-MM-DD")
            tipo = st.selectbox("Tipo", ["Natural","IA"])
        with c3:
            f_parto_esp = f_monta + timedelta(days=114)
            st.write(f"**Parto esperado:** {f_parto_esp.strftime('%Y-%m-%d')}")
            notas = st.text_area("Notas", height=80)

        if st.button("Guardar reproducción"):
            conn.execute("""INSERT INTO reproducciones(marrana_id,macho_id,fecha_monta,tipo,fecha_parto_esperado,notas)
                            VALUES (?,?,?,?,?,?)""",
                         (marrana_id, None if macho_id is None else macho_id, f_monta.strftime("%Y-%m-%d"), tipo, f_parto_esp.strftime("%Y-%m-%d"), notas))
            conn.commit()
            st.success("Reproducción registrada.")

    repro = fetch_df("""
      SELECT r.id, a.arete marrana, r.fecha_monta, r.tipo, r.fecha_parto_esperado
      FROM reproducciones r JOIN animals a ON a.id=r.marrana_id ORDER BY r.id DESC
    """)
    st.dataframe(repro, use_container_width=True)

elif page == "Partos":
    st.title("Partos y Destetes")
    repros = fetch_df("""SELECT r.id, a.arete marrana, r.fecha_parto_esperado FROM reproducciones r
                         JOIN animals a ON a.id=r.marrana_id ORDER BY r.id DESC""")
    with st.expander("➕ Registrar parto/destete", expanded=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            rid = st.selectbox("Reproducción", repros['id'].tolist(), format_func=lambda x: f"{repros.set_index('id').loc[x,'marrana']} (ESP {repros.set_index('id').loc[x,'fecha_parto_esperado']})" if not repros.empty else "")
            f_parto = st.date_input("Fecha de parto", format="YYYY-MM-DD")
        with c2:
            vivos = st.number_input("Nacidos vivos", min_value=0, step=1)
            muertos = st.number_input("Nacidos muertos", min_value=0, step=1)
        with c3:
            dest = st.number_input("Destetados", min_value=0, step=1)
            f_dest = st.date_input("Fecha de destete", format="YYYY-MM-DD")
        notas = st.text_area("Notas", height=80)
        if st.button("Guardar parto/destete"):
            conn.execute("""INSERT INTO partos(reproduccion_id,fecha_parto,nacidos_vivos,nacidos_muertos,destetados,fecha_destete,notas)
                            VALUES (?,?,?,?,?,?,?)""",
                         (rid, f_parto.strftime("%Y-%m-%d"), int(vivos), int(muertos), int(dest), f_dest.strftime("%Y-%m-%d"), notas))
            conn.commit()
            st.success("Parto/destete registrado.")
    partos = fetch_df("""
      SELECT p.id, a.arete marrana, p.fecha_parto, p.nacidos_vivos, p.nacidos_muertos, p.destetados, p.fecha_destete
      FROM partos p JOIN reproducciones r ON r.id=p.reproduccion_id
      JOIN animals a ON a.id=r.marrana_id ORDER BY p.id DESC
    """)
    st.dataframe(partos, use_container_width=True)

elif page == "Ventas":
    st.title("Ventas")
    with st.expander("➕ Registrar venta", expanded=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            f = st.date_input("Fecha", format="YYYY-MM-DD")
            tipo = st.selectbox("Tipo", ["Lechon","Engorde","Reproductor","Carne"])
        with c2:
            cant = st.number_input("Cantidad", min_value=1, step=1)
            peso = st.number_input("Peso total (kg)", min_value=0.0, step=1.0)
        with c3:
            precio = st.number_input("Precio total", min_value=0.0, step=10000.0)
            comprador = st.text_input("Comprador")
        notas = st.text_area("Notas", height=80)
        if st.button("Guardar venta"):
            conn.execute("""INSERT INTO ventas(fecha,tipo,cantidad,peso_total_kg,precio_total,comprador,notas)
                            VALUES (?,?,?,?,?,?,?)""",
                         (f.strftime("%Y-%m-%d"), tipo, int(cant), float(peso), float(precio), comprador, notas))
            conn.commit()
            st.success("Venta registrada.")
    v = fetch_df("SELECT id,fecha,tipo,cantidad,peso_total_kg,precio_total,comprador FROM ventas ORDER BY fecha DESC")
    st.dataframe(v, use_container_width=True)

elif page == "Gastos":
    st.title("Gastos")
    with st.expander("➕ Registrar gasto", expanded=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            f = st.date_input("Fecha", format="YYYY-MM-DD")
            cat = st.selectbox("Categoría", ["Alimento","Veterinaria","Mano de obra","Infraestructura","Otros"])
        with c2:
            desc = st.text_input("Descripción")
        with c3:
            monto = st.number_input("Monto", min_value=0.0, step=1000.0)
        if st.button("Guardar gasto"):
            conn.execute("""INSERT INTO gastos(fecha,categoria,descripcion,monto) VALUES (?,?,?,?)""",
                         (f.strftime("%Y-%m-%d"), cat, desc, float(monto)))
            conn.commit()
            st.success("Gasto registrado.")
    g = fetch_df("SELECT id,fecha,categoria,descripcion,monto FROM gastos ORDER BY fecha DESC")
    st.dataframe(g, use_container_width=True)

elif page == "Alimentos":
    st.title("Consumo de Alimentos")
    with st.expander("➕ Registrar alimento", expanded=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            f = st.date_input("Fecha", format="YYYY-MM-DD")
            etapa = st.selectbox("Etapa", ["Reproductoras","Gestación","Lactancia","Engorde","Lechones"])
        with c2:
            kg = st.number_input("Kg consumidos", min_value=0.0, step=1.0)
        with c3:
            costo = st.number_input("Costo ($)", min_value=0.0, step=1000.0)
        notas = st.text_area("Notas", height=80)
        if st.button("Guardar consumo"):
            conn.execute("""INSERT INTO alimentos(fecha,etapa,kg,costo,notas) VALUES (?,?,?,?,?)""",
                         (f.strftime("%Y-%m-%d"), etapa, float(kg), float(costo), notas))
            conn.commit()
            st.success("Consumo registrado.")
    a = fetch_df("SELECT id,fecha,etapa,kg,costo FROM alimentos ORDER BY fecha DESC")
    st.dataframe(a, use_container_width=True)

elif page == "Reportes":
    st.title("Reportes")
    c1,c2 = st.columns(2)
    with c1: fi = st.date_input("Fecha inicio", value=datetime(datetime.today().year,1,1), format="YYYY-MM-DD")
    with c2: ff = st.date_input("Fecha fin", value=datetime.today(), format="YYYY-MM-DD")
    fi_s, ff_s = fi.strftime("%Y-%m-%d"), ff.strftime("%Y-%m-%d")
    ingresos = fetch_df("SELECT COALESCE(SUM(precio_total),0) v FROM ventas WHERE fecha BETWEEN ? AND ?", (fi_s, ff_s)).iloc[0]['v']
    egresos = fetch_df("SELECT COALESCE(SUM(monto),0) v FROM gastos WHERE fecha BETWEEN ? AND ?", (fi_s, ff_s)).iloc[0]['v']
    u = ingresos-egresos
    x,y,z = st.columns(3)
    with x: kpi("Ingresos", f"${ingresos:,.0f}")
    with y: kpi("Gastos", f"${egresos:,.0f}")
    with z: kpi("Utilidad", f"${u:,.0f}")

    st.subheader("PSY (destetados por marrana/año) – aprox.")
    marranas = fetch_df("SELECT COUNT(*) n FROM animals WHERE categoria='Marrana' AND IFNULL(estado,'Activo')='Activo'").iloc[0]['n']
    dest = fetch_df("SELECT COALESCE(SUM(destetados),0) d FROM partos WHERE fecha_parto BETWEEN ? AND ?", (fi_s, ff_s)).iloc[0]['d']
    days = max(1,(ff - fi).days)
    psy = (dest / marranas) * (365 / days) if marranas>0 else 0
    st.write(f"**PSY estimado:** {psy:.1f}")

    st.subheader("Detalle")
    v = fetch_df("SELECT * FROM ventas WHERE fecha BETWEEN ? AND ? ORDER BY fecha",(fi_s, ff_s))
    g = fetch_df("SELECT * FROM gastos WHERE fecha BETWEEN ? AND ? ORDER BY fecha",(fi_s, ff_s))
    st.write("**Ventas**"); st.dataframe(v, use_container_width=True)
    st.download_button("Descargar ventas (CSV)", v.to_csv(index=False).encode("utf-8"), file_name="ventas.csv")
    st.write("**Gastos**"); st.dataframe(g, use_container_width=True)
    st.download_button("Descargar gastos (CSV)", g.to_csv(index=False).encode("utf-8"), file_name="gastos.csv")

elif page == "Finanzas (TIR/Payback)":
    st.title("Finanzas: TIR y Payback por periodo")
    st.caption("Calcula TIR y Payback a partir de tu histórico de ventas y gastos más una inversión inicial.")

    c1,c2,c3 = st.columns(3)
    with c1:
        fi = st.date_input("Fecha inicio", value=datetime(datetime.today().year,1,1), format="YYYY-MM-DD")
    with c2:
        ff = st.date_input("Fecha fin", value=datetime.today(), format="YYYY-MM-DD")
    with c3:
        inv_inicial = st.number_input("Inversión inicial (CAPEX + compra animales)", min_value=0.0, value=0.0, step=100000.0)

    fi_s, ff_s = fi.strftime("%Y-%m-%d"), ff.strftime("%Y-%m-%d")
    ventas = fetch_df("SELECT fecha, precio_total FROM ventas WHERE fecha BETWEEN ? AND ?", (fi_s, ff_s))
    gastos = fetch_df("SELECT fecha, monto FROM gastos WHERE fecha BETWEEN ? AND ?", (fi_s, ff_s))

    if ventas.empty and gastos.empty and inv_inicial==0:
        st.info("Ingresa registros de ventas/gastos o una inversión inicial para calcular.")
    else:
        def month_key(d): return datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m")
        months = sorted(set([month_key(x) for x in ventas['fecha'].tolist()] + [month_key(x) for x in gastos['fecha'].tolist()] + [fi.strftime("%Y-%m"), ff.strftime("%Y-%m")]))
        start = datetime.strptime(months[0], "%Y-%m")
        end = datetime.strptime(months[-1], "%Y-%m")
        cur = start; timeline = []
        while cur <= end:
            timeline.append(cur.strftime("%Y-%m"))
            y = cur.year + (cur.month // 12)
            m = (cur.month % 12) + 1
            cur = datetime(y, m, 1)

        v_m = ventas.groupby(ventas['fecha'].apply(lambda s: s[:7]))['precio_total'].sum().reindex(timeline, fill_value=0.0)
        g_m = gastos.groupby(gastos['fecha'].apply(lambda s: s[:7]))['monto'].sum().reindex(timeline, fill_value=0.0)

        cash = [-inv_inicial] + (v_m - g_m).tolist()
        try:
            irr_m = np.irr(cash)
        except Exception:
            irr_m = None

        cum = np.cumsum(cash)
        payback_idx = next((i for i,x in enumerate(cum) if x>=0), None)

        st.subheader("Resultados")
        c1,c2 = st.columns(2)
        if irr_m is not None and not np.isnan(irr_m):
            with c1: kpi("TIR mensual", f"{irr_m*100:.2f}%")
            with c2: kpi("TIR anualizada (aprox.)", f"{((1+irr_m)**12-1)*100:.2f}%")
        else:
            st.warning("No se pudo calcular la TIR con los flujos actuales.")
        if payback_idx is not None:
            meses = payback_idx
            st.metric("Payback", f"{meses} meses")
        else:
            st.info("El payback no se alcanza en el periodo seleccionado.")

        st.subheader("Flujo de caja mensual")
        df = pd.DataFrame({"Mes": ["t0 (inversión)"] + timeline, "Flujo": cash})
        st.dataframe(df, use_container_width=True)
        st.download_button("Descargar cashflow (CSV)", df.to_csv(index=False).encode("utf-8"), file_name="cashflow.csv")
