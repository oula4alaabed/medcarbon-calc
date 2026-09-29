"""
MedCarbon-Calc — Mediterranean low-carbon wall assembly calculator.

Run with:
    pip install streamlit pandas
    streamlit run app.py

NOTE: All emission factors below are ILLUSTRATIVE, rounded values for
early-stage design comparison. Replace them with project-specific EPDs or a
database such as ICE / Ecoinvent before using results in any formal report.
"""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page setup & styling
# ---------------------------------------------------------------------------
st.set_page_config(page_title="MedCarbon-Calc", page_icon="🏛️", layout="wide")

TERRACOTTA = "#B5573A"
OCHRE = "#D9A441"
OLIVE = "#6B7A4F"
SEA = "#2F6F8F"
SLATE = "#5B5B5B"

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; max-width: 1200px; }
    h1, h2, h3 { letter-spacing: -0.02em; font-weight: 600; }
    [data-testid="stMetric"] {
        background: #F7F3EC; border: 1px solid #E6DECF;
        border-radius: 6px; padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] { color: #6b6255; text-transform: uppercase;
        font-size: 0.72rem; letter-spacing: 0.08em; }
    [data-testid="stSidebar"] { background: #F1ECE2; }
    .tagline { color: #6b6255; font-size: 1.05rem; margin-top: -0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Assembly:
    name: str
    ef_material: float   # kg CO2e per m3 of wall (production stage, A1–A3)
    biogenic: float      # kg CO2e per m3 (negative = carbon stored in bio-based material)
    density: float       # kg per m3 (used for transport emissions)
    local_share: float   # 0–1 typical share of material value/mass sourced regionally
    note: str


ASSEMBLIES = {
    "Local Stone": Assembly(
        "Local Stone", 70.0, 0.0, 2200.0, 0.95,
        "Quarried within the region, lime mortar. Very high mass, minimal processing.",
    ),
    "Rammed Earth": Assembly(
        "Rammed Earth", 90.0, 0.0, 1900.0, 0.90,
        "Site or nearby soil with ~6% cement stabilisation. Cement is the main carbon source.",
    ),
    "Hempcrete": Assembly(
        "Hempcrete", 60.0, -110.0, 350.0, 0.60,
        "Hemp shiv + lime binder on a timber frame. Stores biogenic carbon; binder often imported.",
    ),
    "Baseline Reinforced Concrete": Assembly(
        "Baseline Reinforced Concrete", 380.0, 0.0, 2400.0, 0.35,
        "Ready-mix concrete with rebar. Cement, aggregates and steel are largely sourced off-region.",
    ),
}
BASELINE_KEY = "Baseline Reinforced Concrete"
TRANSPORT_EF = 0.10  # kg CO2e per tonne-km (road freight, illustrative)


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
def wall_volume(floor_area, storeys, height, glazing, thickness):
    """Estimate wall volume from a square footprint."""
    footprint = floor_area / storeys
    perimeter = 4 * footprint ** 0.5
    gross_wall_area = perimeter * height * storeys
    net_wall_area = gross_wall_area * (1 - glazing)
    return net_wall_area, net_wall_area * thickness


def carbon(asm, volume, distance_km, include_biogenic):
    materials = volume * asm.ef_material
    transport = volume * asm.density / 1000 * distance_km * TRANSPORT_EF
    biogenic = volume * asm.biogenic if include_biogenic else 0.0
    return {
        "Materials": materials,
        "Transport": transport,
        "Biogenic storage": biogenic,
        "Total": materials + transport + biogenic,
    }


def sourcing_score(asm, distance_km):
    """0–100 score: regional share of materials, penalised for long haul distances."""
    proximity = 1 - 0.5 * min(distance_km, 300) / 300
    return round(100 * asm.local_share * proximity, 1)


# ---------------------------------------------------------------------------
# Sidebar inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Project inputs")
    floor_area = st.number_input("Floor area (m²)", 20.0, 10000.0, 250.0, step=10.0)
    thickness = st.slider("Wall thickness (m)", 0.10, 0.80, 0.40, step=0.01)
    choice = st.selectbox("Primary wall assembly", list(ASSEMBLIES.keys()), index=1)

    with st.expander("Advanced assumptions"):
        storeys = st.number_input("Storeys", 1, 10, 2)
        height = st.number_input("Floor-to-floor height (m)", 2.4, 5.0, 3.0, step=0.1)
        glazing = st.slider("Glazing ratio", 0.0, 0.6, 0.20, step=0.05)
        distance = st.slider("Average supplier distance (km)", 5, 500, 40, step=5)
        concrete_thickness = st.slider(
            "Concrete baseline thickness (m)", 0.10, 0.50, 0.25, step=0.01,
            help="Concrete walls are usually thinner than earth or stone walls for the same structural role.",
        )
        include_biogenic = st.toggle("Count biogenic carbon storage", value=True)

    st.caption("Emission factors are illustrative early-design values, not EPD data.")

# ---------------------------------------------------------------------------
# Compute results
# ---------------------------------------------------------------------------
chosen = ASSEMBLIES[choice]
base = ASSEMBLIES[BASELINE_KEY]

wall_area, vol_chosen = wall_volume(floor_area, storeys, height, glazing, thickness)
_, vol_base = wall_volume(floor_area, storeys, height, glazing, concrete_thickness)

res_chosen = carbon(chosen, vol_chosen, distance, include_biogenic)
res_base = carbon(base, vol_base, distance, include_biogenic)

total = res_chosen["Total"]
per_m2 = total / floor_area
base_total = res_base["Total"]
base_per_m2 = base_total / floor_area
score = sourcing_score(chosen, distance)
base_score = sourcing_score(base, distance)

# ---------------------------------------------------------------------------
# Header & metrics
# ---------------------------------------------------------------------------
st.title("MedCarbon-Calc")
st.markdown(
    '<p class="tagline">Embodied carbon and local sourcing for Mediterranean wall assemblies.</p>',
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
delta_pct = (total - base_total) / base_total * 100 if base_total else 0
m1.metric(
    "Total embodied carbon",
    f"{total:,.0f} kg CO₂e",
    delta=None if choice == BASELINE_KEY else f"{delta_pct:+.0f}% vs concrete",
    delta_color="inverse",
)
m2.metric(
    "Carbon intensity",
    f"{per_m2:,.1f} kg CO₂e/m²",
    delta=None if choice == BASELINE_KEY else f"{per_m2 - base_per_m2:+,.1f} vs concrete",
    delta_color="inverse",
)
m3.metric(
    "Local sourcing score",
    f"{score:.0f}%",
    delta=None if choice == BASELINE_KEY else f"{score - base_score:+.0f} pts vs concrete",
)
m4.metric("Wall volume", f"{vol_chosen:,.1f} m³", help=f"Net wall area ≈ {wall_area:,.0f} m²")

st.caption(chosen.note)
st.divider()

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Chosen vs concrete", "All assemblies", "Thickness sensitivity", "Assumptions"]
)

with tab1:
    if choice == BASELINE_KEY:
        st.info("Concrete is the baseline. Pick another assembly in the sidebar to compare.")
    labels = [base.name, chosen.name] if choice != BASELINE_KEY else [base.name]
    results = [res_base, res_chosen] if choice != BASELINE_KEY else [res_base]

    left, right = st.columns(2)
    with left:
        st.subheader("Carbon breakdown (kg CO₂e)")
        breakdown = pd.DataFrame(
            {k: [r[k] for r in results] for k in ["Materials", "Transport", "Biogenic storage"]},
            index=labels,
        )
        st.bar_chart(breakdown, color=[TERRACOTTA, OCHRE, OLIVE], horizontal=True)
    with right:
        st.subheader("Carbon intensity (kg CO₂e/m² floor)")
        intensity = pd.DataFrame(
            {"kg CO₂e/m²": [r["Total"] / floor_area for r in results]}, index=labels
        )
        st.bar_chart(intensity, color=SEA, horizontal=True)

    st.subheader("Local sourcing score (%)")
    scores = [base_score, score] if choice != BASELINE_KEY else [base_score]
    st.bar_chart(pd.DataFrame({"Score": scores}, index=labels), color=OLIVE, horizontal=True)

with tab2:
    rows = []
    for key, asm in ASSEMBLIES.items():
        t = thickness if key != BASELINE_KEY else concrete_thickness
        _, v = wall_volume(floor_area, storeys, height, glazing, t)
        r = carbon(asm, v, distance, include_biogenic)
        rows.append(
            {
                "Assembly": key,
                "Thickness (m)": t,
                "Total (kg CO₂e)": round(r["Total"]),
                "kg CO₂e/m²": round(r["Total"] / floor_area, 1),
                "Local score (%)": sourcing_score(asm, distance),
            }
        )
    table = pd.DataFrame(rows).set_index("Assembly")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Carbon intensity")
        st.bar_chart(table[["kg CO₂e/m²"]], color=TERRACOTTA)
    with c2:
        st.subheader("Local sourcing")
        st.bar_chart(table[["Local score (%)"]], color=OLIVE)
    st.dataframe(table, use_container_width=True)

with tab3:
    st.subheader(f"{chosen.name}: carbon vs wall thickness")
    thicknesses = [round(0.10 + 0.05 * i, 2) for i in range(15)]  # 0.10 – 0.80 m
    sens = pd.DataFrame(
        {
            chosen.name: [
                carbon(chosen, wall_volume(floor_area, storeys, height, glazing, t)[1],
                       distance, include_biogenic)["Total"] / floor_area
                for t in thicknesses
            ],
            f"Concrete @ {concrete_thickness:.2f} m": [base_per_m2] * len(thicknesses),
        },
        index=pd.Index(thicknesses, name="Wall thickness (m)"),
    )
    st.line_chart(sens, color=[TERRACOTTA, SLATE])
    st.caption("kg CO₂e per m² of floor area. Where the lines cross, the thicker low-carbon wall loses its advantage.")

with tab4:
    st.subheader("Method")
    st.markdown(
        f"""
- **Geometry:** square footprint of `floor area ÷ storeys`; net wall area = perimeter × height × storeys × (1 − glazing).
- **Embodied carbon:** wall volume × material factor + transport (`mass × distance × {TRANSPORT_EF} kg CO₂e/t·km`) + biogenic storage (optional).
- **Sourcing score:** typical regional share of the assembly, reduced by up to 50% as supplier distance grows toward 300 km.
- **Scope:** wall assembly only, production and transport stages (A1–A4). Foundations, floors, roof, finishes and operational energy are excluded.
        """
    )
    factors = pd.DataFrame(
        [
            {
                "Assembly": a.name,
                "Material (kg CO₂e/m³)": a.ef_material,
                "Biogenic (kg CO₂e/m³)": a.biogenic,
                "Density (kg/m³)": a.density,
                "Regional share": a.local_share,
            }
            for a in ASSEMBLIES.values()
        ]
    ).set_index("Assembly")
    st.dataframe(factors, use_container_width=True)
