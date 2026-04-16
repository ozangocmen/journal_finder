import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from backend.semantic_analyzer import ManuscriptFingerprint
from backend.risk_assessor import RiskAssessment

def render_fingerprint(fp: ManuscriptFingerprint):
    st.markdown("### 🧬 Manuscript Semantic Fingerprint")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Primary Domain(s):** " + (", ".join(fp.primary_domain) if fp.primary_domain else "Unspecified"))
        st.markdown("**Primary Targets:** " + (", ".join(fp.primary_targets) if fp.primary_targets else "None identified"))
        st.markdown("**Secondary Targets:** " + (", ".join(fp.secondary_targets) if fp.secondary_targets else "None identified"))
        st.markdown("**Methodologies:** " + (", ".join(fp.methodologies) if fp.methodologies else "Unspecified"))
    
    with col2:
        st.markdown(f"**Study Type:** {fp.study_type if fp.study_type else 'Unspecified'}")
        st.markdown(f"**Translational Stage:** {fp.translational_stage if fp.translational_stage else 'Unspecified'}")
        st.markdown(f"**Clinical Relevance Score:** {fp.clinical_relevance_score}/10")
        
    st.markdown("**Hypothesis:** " + (fp.hypothesis if fp.hypothesis else "None provided"))
    st.markdown("**Novelty:** " + (fp.novelty if fp.novelty else "None identified"))
    
    st.markdown("**Keyword Taxonomy:**")
    st.markdown(f"- **Core:** {', '.join(fp.keywords.core) if fp.keywords.core else 'None'}")
    st.markdown(f"- **Supporting:** {', '.join(fp.keywords.supporting) if fp.keywords.supporting else 'None'}")
    st.markdown(f"- **Peripheral:** {', '.join(fp.keywords.peripheral) if fp.keywords.peripheral else 'None'}")

def render_cas_radar(dim_a, dim_b, dim_c, dim_d, key_suffix=""):
    categories = ['Topical (35%)', 'Methodological (25%)', 'Translational Fit (20%)', 'Audience Fit (20%)']
    values = [dim_a, dim_b, dim_c, dim_d]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='CAS Dimensions',
        marker=dict(color='#3182ce')
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=False,
        margin=dict(t=20, b=20, l=20, r=20),
        height=250
    )
    return fig

def render_journal_card(rank: int, row: pd.Series, risk: RiskAssessment, pub_color: str):
    tier_colors = {1: "#38a169", 2: "#d69e2e", 3: "#e53e3e"}
    tier_labels = {1: "PRIORITY TARGET", 2: "STRONG ALTERNATIVE", 3: "CONTINGency OPTION"}
    
    tier = risk.tier if risk else "N/A"
    t_color = tier_colors.get(tier, "#718096")
    t_label = tier_labels.get(tier, "UNKNOWN TIER")
    
    st.markdown(f"""
    <div style="border: 2px solid {pub_color}; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1rem;">
            <h3 style="margin: 0; color: #2d3748;">#{rank} — {row.get('journal_title', 'Unknown')}</h3>
            <span style="background: {t_color}; color: white; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem;">TIER {tier}: {t_label}</span>
        </div>
    """, unsafe_allow_html=True)
    
    col_scores, col_radar = st.columns([3, 2])
    
    with col_scores:
        st.markdown(f"**Publisher:** {row.get('publisher', 'Unknown')}")
        st.markdown(f"**Composite Alignment Score (CAS):** <span style='font-size: 1.2rem; font-weight: 700; color: #3182ce;'>{row.get('cas', 0):.1f}%</span>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**Relevance Justification:**")
        st.write(row.get('relevance_justification', 'No justification provided.'))
        if risk:
            st.markdown(f"**Scope Edge Classification:** {risk.scope_edge_risk} — *{risk.scope_edge_rationale}*")
        
    with col_radar:
        fig = render_cas_radar(row.get('dim_a', 0), row.get('dim_b', 0), row.get('dim_c', 0), row.get('dim_d', 0), key_suffix=f"radar_{rank}")
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
    st.markdown("---")
    
    # Bottom Grid: Bibliometrics, Speed, Risk
    bg1, bg2, bg3 = st.columns(3)
    with bg1:
        st.markdown("#### 📊 Bibliometric Profile")
        st.markdown(f"- **Impact Factor:** {row.get('impact_factor', 'N/A')}")
        st.markdown(f"- **Quartile:** {row.get('sjr_quartile', 'N/A')}")
        st.markdown(f"- **OA Status:** {row.get('oa_status', 'N/A')}")
        st.markdown(f"- **Indexing:** {row.get('indexing', 'N/A')}")
        
    with bg2:
        st.markdown("#### ⚡ Publication Speed")
        st.markdown(f"- **Time to First Decision:** {row.get('time_to_first_decision', 'Not reported')}")
        st.markdown(f"- **Total Turnaround:** {row.get('total_turnaround', 'Not reported')}")
        st.markdown(f"- **Acceptance Rate:** {row.get('acceptance_rate', 'Not reported')}")
        
    with bg3:
        st.markdown("#### ⚠️ Strategic Risk")
        if risk:
            st.markdown(f"- **Prestige/Speed:** {risk.prestige_vs_speed}")
            st.markdown(f"- **Special Issues:** {risk.special_issues}")
            st.markdown(f"- **Competing Subms:** {risk.competing_submissions}")
        else:
            st.markdown("Risk assessment unavailable.")
            
    st.markdown("---")
    if risk:
        st.markdown(f"**Recommendation:** {risk.recommendation}")
        
    with st.expander("📖 Aims & Scope Text"):
        st.markdown(f"**Source URL:** [{row.get('scope_url', 'N/A')}]({row.get('scope_url', '#')})  | **Status:** {row.get('scope_retrieval_status', 'UNKNOWN')}")
        st.write(row.get('scope_text', 'No scope text available.'))
        
    st.markdown("</div>", unsafe_allow_html=True)

def render_borderline_list(df: pd.DataFrame):
    if df.empty:
        return
    with st.expander(f"⚠️ Borderline Matches ({len(df)} journals with CAS 45-59%)"):
        for _, row in df.iterrows():
            st.markdown(f"- **{row.get('journal_title', 'Unknown')}** (CAS: {row.get('cas', 0):.1f}%) | {row.get('publisher', '')}")
