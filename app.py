import streamlit as st
from dataclasses import dataclass
from typing import Optional, Dict, Any

# =========================
# 1) Utilidades de periodos
# =========================

def n_periods_per_year(period: str, base_days: int = 360, custom_days: Optional[int] = None) -> float:
    period = period.upper()
    table = {"A": 1, "S": 2, "T": 4, "M": 12, "Q": 24, "D": base_days}
    if period in table:
        return float(table[period])
    if period == "CUSTOM":
        if not custom_days or custom_days <= 0:
            raise ValueError("Si eliges 'X días', debes poner X > 0.")
        return float(base_days) / float(custom_days)
    raise ValueError(f"Periodo no soportado: {period}")

@dataclass
class RateSpec:
    value: float              # decimal (0.016)
    kind: str                 # 'E' efectiva o 'N' nominal
    form: str                 # 'V' vencida o 'A' anticipada
    period: str               # 'A','S','T','M','Q','D','CUSTOM'
    base_days: int = 360
    custom_days: Optional[int] = None

    def n(self) -> float:
        return n_periods_per_year(self.period, self.base_days, self.custom_days)

# =========================
# 2) Fórmulas del esquema
# =========================

def nominal_to_periodic(j: float, n: float) -> float:
    return j / n

def periodic_to_nominal(i_p: float, n: float) -> float:
    return i_p * n

def anticipada_to_vencida(d: float) -> float:
    if d >= 1:
        raise ValueError("Una tasa anticipada periódica no puede ser >= 100%.")
    return d / (1 - d)

def vencida_to_anticipada(i: float) -> float:
    return i / (1 + i)

def periodic_to_EA(i_p_v: float, n: float) -> float:
    return (1 + i_p_v) ** n - 1

def EA_to_periodic(EA: float, n: float) -> float:
    return (1 + EA) ** (1 / n) - 1

def to_EA_from_any(rate: RateSpec) -> Dict[str, Any]:
    """
    Devuelve EA + el paso a paso intermedio para mostrar en la UI.
    """
    n1 = rate.n()

    # Nominal/Efectiva -> periódica (misma forma)
    if rate.kind == "N":
        ip = nominal_to_periodic(rate.value, n1)
        step1 = f"Periódica: i_p = j/n = {rate.value:.8f}/{n1:.8f} = {ip:.8f}"
    else:
        ip = rate.value
        step1 = f"Periódica: i_p = {ip:.8f} (ya era efectiva periódica)"

    # Anticipada -> vencida (si aplica)
    if rate.form == "A":
        ipv = anticipada_to_vencida(ip)
        step2 = f"Anticipada→Vencida: i = d/(1-d) = {ip:.8f}/(1-{ip:.8f}) = {ipv:.8f}"
    else:
        ipv = ip
        step2 = f"Forma: ya era vencida, i = {ipv:.8f}"

    # Periódica vencida -> EA
    EA = periodic_to_EA(ipv, n1)
    step3 = f"EA: (1+i)^n - 1 = (1+{ipv:.8f})^{n1:.8f} - 1 = {EA:.8f}"

    return {"EA": EA, "n1": n1, "ip": ip, "ipv": ipv, "steps": [step1, step2, step3]}

def from_EA_to_any(EA: float, target: RateSpec) -> Dict[str, Any]:
    """
    EA -> tasa objetivo + paso a paso.
    """
    n2 = target.n()

    # EA -> periódica vencida
    ipv2 = EA_to_periodic(EA, n2)
    step1 = f"Periódica vencida destino: i = (1+EA)^(1/n) - 1 = (1+{EA:.8f})^(1/{n2:.8f}) - 1 = {ipv2:.8f}"

    # vencida -> anticipada (si aplica)
    if target.form == "A":
        ip2 = vencida_to_anticipada(ipv2)
        step2 = f"Vencida→Anticipada: d = i/(1+i) = {ipv2:.8f}/(1+{ipv2:.8f}) = {ip2:.8f}"
    else:
        ip2 = ipv2
        step2 = f"Forma: ya era vencida, i = {ip2:.8f}"

    # periódica -> nominal si lo piden
    if target.kind == "N":
        out = periodic_to_nominal(ip2, n2)
        step3 = f"Nominal: j = i_p·n = {ip2:.8f}·{n2:.8f} = {out:.8f}"
    else:
        out = ip2
        step3 = f"Efectiva destino: tasa = {out:.8f}"

    return {"out": out, "n2": n2, "ipv2": ipv2, "ip2": ip2, "steps": [step1, step2, step3]}

def label_rate(kind: str, form: str, period: str, custom_days: Optional[int]) -> str:
    k = "Efectiva" if kind == "E" else "Nominal"
    f = "Vencida" if form == "V" else "Anticipada"
    if period == "CUSTOM":
        p = f"{custom_days} días"
    else:
        pmap = {"A":"Anual", "S":"Semestral", "T":"Trimestral", "M":"Mensual", "Q":"Quincenal", "D":"Diaria"}
        p = pmap.get(period, period)
    return f"{k} • {f} • {p}"

# =========================
# 3) UI (más agradable)
# =========================

st.set_page_config(page_title="Conversor de tasas - Ing. Económica", layout="centered")

st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 920px; }
h1 { margin-bottom: 0.25rem; }
.small-muted { color: #9aa0a6; font-size: 0.95rem; }
.card { border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.03); }
hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.title("Conversor de tasas (Ingeniería Económica)")
st.markdown('<div class="small-muted">Basado en el esquema: Nominal/Efectiva → Periódica → (A↔V) → EA → Periódica → (A↔V) → Nominal/Efectiva</div>', unsafe_allow_html=True)

base_days = st.selectbox("Base de días", [360, 365, 366], index=0)

period_labels = {
    "Anual (A)": "A",
    "Semestral (S)": "S",
    "Trimestral (T)": "T",
    "Mensual (M)": "M",
    "Quincenal (Q)": "Q",
    "Diaria (D)": "D",
    "X días (custom)": "CUSTOM",
}

st.markdown("### Parámetros")
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Tasa de partida")
    in_value_pct = st.number_input("Valor (%)", value=1.6, step=0.01, format="%.6f")
    in_kind = st.selectbox("Tipo", ["Efectiva (E)", "Nominal (N)"], index=0)
    in_form = st.selectbox("Forma", ["Vencida (V)", "Anticipada (A)"], index=0)
    in_period_label = st.selectbox("Periodo", list(period_labels.keys()), index=3)

    in_custom_days = None
    if period_labels[in_period_label] == "CUSTOM":
        in_custom_days = st.number_input("¿Cuántos días por periodo? (X)", min_value=1, value=20, step=1)

    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Tasa destino")
    out_kind = st.selectbox("Tipo destino", ["Efectiva (E)", "Nominal (N)"], index=0)
    out_form = st.selectbox("Forma destino", ["Vencida (V)", "Anticipada (A)"], index=0)
    out_period_label = st.selectbox("Periodo destino", list(period_labels.keys()), index=2)

    out_custom_days = None
    if period_labels[out_period_label] == "CUSTOM":
        out_custom_days = st.number_input("¿Cuántos días por periodo destino? (X)", min_value=1, value=20, step=1)

    st.markdown('</div>', unsafe_allow_html=True)

show_steps = st.toggle("Mostrar paso a paso", value=False)

st.markdown("---")

if st.button("Convertir", type="primary"):
    try:
        src = RateSpec(
            value=in_value_pct / 100.0,
            kind="E" if in_kind.startswith("Efectiva") else "N",
            form="V" if in_form.startswith("Vencida") else "A",
            period=period_labels[in_period_label],
            base_days=int(base_days),
            custom_days=int(in_custom_days) if in_custom_days is not None else None,
        )

        tgt = RateSpec(
            value=0.0,
            kind="E" if out_kind.startswith("Efectiva") else "N",
            form="V" if out_form.startswith("Vencida") else "A",
            period=period_labels[out_period_label],
            base_days=int(base_days),
            custom_days=int(out_custom_days) if out_custom_days is not None else None,
        )

        # Conversiones según el esquema
        a = to_EA_from_any(src)
        b = from_EA_to_any(a["EA"], tgt)

        st.markdown("### Resultados")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**Partida:**", label_rate(src.kind, src.form, src.period, src.custom_days))
        st.write("**Destino:**", label_rate(tgt.kind, tgt.form, tgt.period, tgt.custom_days))
        st.write(f"**Base de días:** {base_days}")
        st.markdown("<hr/>", unsafe_allow_html=True)

        r1, r2 = st.columns(2)
        with r1:
            st.metric("EA equivalente", f"{a['EA']*100:.6f}%")
        with r2:
            st.metric("Tasa convertida", f"{b['out']*100:.6f}%")

        st.caption(f"n1 = {a['n1']:.6g} periodos/año • n2 = {b['n2']:.6g} periodos/año")
        st.markdown('</div>', unsafe_allow_html=True)

        if show_steps:
            st.markdown("### Paso a paso (según el cuadro)")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("**Hacia EA**")
            for s in a["steps"]:
                st.write("•", s)
            st.write("")
            st.write("**Desde EA a destino**")
            for s in b["steps"]:
                st.write("•", s)
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---")
st.markdown('<div class="small-muted">Tip: Si tu profe usa base 360 en “D”, selecciona 360. Para “X días”, usa “X días (custom)”.</div>', unsafe_allow_html=True)