import pandas as pd
import streamlit as st
import duckdb
import os
import time
import plotly.express as px
import io
import unicodedata
import re

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

streamlit_dir = os.path.join(os.path.expanduser("~"), ".streamlit")
config_path = os.path.join(streamlit_dir, "config.toml")

if not os.path.exists(config_path):
  os.makedirs(streamlit_dir, exist_ok=True)
  with open(config_path, "w", encoding="utf-8") as f:
    f.write("[server]\nport = 8501\n")

st.set_page_config(
    page_title="Painel Censo Escolar (2007-2025)",
    page_icon="🏫",
    layout="wide"
)

# =============================================================================
# CSS CUSTOMIZADO
# =============================================================================

st.markdown("""
<style>
    .stCheckbox {
        margin-bottom: -10px;
    }

    div[data-testid="stDataFrame"] {
        margin-top: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CAMINHOS E CARREGAMENTO DO DICIONÁRIO EXTERNO (ABA 4)
# =============================================================================

CAMINHO_DICIONARIO_PARQUET = "dicionario_super_tabelas.parquet"

@st.cache_data(show_spinner="A carregar dicionário de dados...")
def carregar_dicionario_dados(caminho_parquet):
    if os.path.exists(caminho_parquet):
        df = pd.read_parquet(caminho_parquet)
        return df
    else:
        st.warning(f"Ficheiro de dicionário não encontrado em: {caminho_parquet}")
        return pd.DataFrame(columns=["Coluna Original", "Descrição / Nome Amigável"])

# =============================================================================
# MAPEAMENTOS DAS COLUNAS DE QUANTIDADE E TURMAS
# =============================================================================

MAP_DEPENDENCIA = {
    "1": "1 - Federal",
    "2": "2 - Estadual",
    "3": "3 - Municipal",
    "4": "4 - Privado"
}

MAP_LOCALIZACAO = {
    "1": "1 - Urbano",
    "2": "2 - Rural"
}

OPCOES_ETAPAS = {
    "QT_MAT_BAS": "Educação Básica Geral (QT_MAT_BAS)",
    "QT_MAT_INF": "Educação Infantil Total (QT_MAT_INF)",
    "QT_MAT_INF_CRE": "Infantil - Creche (QT_MAT_INF_CRE)",
    "QT_MAT_INF_PRE": "Infantil - Pré-Escola (QT_MAT_INF_PRE)",
    "QT_MAT_FUND": "Ensino Fundamental Total (QT_MAT_FUND)",
    "QT_MAT_FUND_AI": "Fundamental - Anos Iniciais (QT_MAT_FUND_AI)",
    "QT_MAT_FUND_AF": "Fundamental - Anos Finais (QT_MAT_FUND_AF)",
    "QT_MAT_MED": "Ensino Médio Total (QT_MAT_MED)",
    "QT_MAT_PROF": "Educação Profissional Total (QT_MAT_PROF)",
    "QT_MAT_PROF_TEC": "Profissional Técnico (QT_MAT_PROF_TEC)",
    "QT_MAT_EJA": "EJA Total (QT_MAT_EJA)",
    "QT_MAT_EJA_FUND": "EJA - Fundamental (QT_MAT_EJA_FUND)",
    "QT_MAT_EJA_MED": "EJA - Médio (QT_MAT_EJA_MED)",
    "QT_MAT_ESP": "Educação Especial Total (QT_MAT_ESP)",
    "QT_MAT_ESP_CC": "Especial - Classes Comuns/Inclusão (QT_MAT_ESP_CC)",
    "QT_MAT_ESP_CE": "Especial - Classes Exclusivas (QT_MAT_ESP_CE)"
}

OPCOES_SEXO = {
    "QT_MAT_BAS_FEM": "Feminino (QT_MAT_BAS_FEM)",
    "QT_MAT_BAS_MASC": "Masculino (QT_MAT_BAS_MASC)"
}

OPCOES_RACA = {
    "QT_MAT_BAS_BRANCA": "Branca (QT_MAT_BAS_BRANCA)",
    "QT_MAT_BAS_PRETA": "Preta (QT_MAT_BAS_PRETA)",
    "QT_MAT_BAS_PARDA": "Parda (QT_MAT_BAS_PARDA)",
    "QT_MAT_BAS_AMARELA": "Amarela (QT_MAT_BAS_AMARELA)",
    "QT_MAT_BAS_INDIGENA": "Indígena (QT_MAT_BAS_INDIGENA)",
    "QT_MAT_BAS_ND": "Não Declarado (QT_MAT_BAS_ND)"
}

OPCOES_IDADE = {
    "QT_MAT_BAS_0_3": "0 a 3 anos (QT_MAT_BAS_0_3)",
    "QT_MAT_BAS_4_5": "4 a 5 anos (QT_MAT_BAS_4_5)",
    "QT_MAT_BAS_6_10": "6 a 10 anos (QT_MAT_BAS_6_10)",
    "QT_MAT_BAS_11_14": "11 a 14 anos (QT_MAT_BAS_11_14)",
    "QT_MAT_BAS_15_17": "15 a 17 anos (QT_MAT_BAS_15_17)",
    "QT_MAT_BAS_18_MAIS": "18 anos ou mais (QT_MAT_BAS_18_MAIS)"
}

OPCOES_TURNO = {
    "QT_MAT_BAS_D": "Diurno (QT_MAT_BAS_D)",
    "QT_MAT_BAS_N": "Noturno (QT_MAT_BAS_N)",
    "QT_MAT_BAS_EAD": "Educação a Distância — turno não aplicável (QT_MAT_BAS_EAD)",
    "QT_MAT_INF_INT": "Infantil - Integral (QT_MAT_INF_INT)",
    "QT_MAT_INF_CRE_INT": "Creche - Integral (QT_MAT_INF_CRE_INT)",
    "QT_MAT_INF_PRE_INT": "Pré-Escola - Integral (QT_MAT_INF_PRE_INT)",
    "QT_MAT_FUND_INT": "Fundamental - Integral (QT_MAT_FUND_INT)",
    "QT_MAT_FUND_AI_INT": "Fund. Iniciais - Integral (QT_MAT_FUND_AI_INT)",
    "QT_MAT_FUND_AF_INT": "Fund. Finais - Integral (QT_MAT_FUND_AF_INT)",
    "QT_MAT_MED_INT": "Médio - Integral (QT_MAT_MED_INT)"
}

OPCOES_CURSOS_QTD = {
    "QT_CURSO_TEC": "Total de Cursos (QT_CURSO_TEC)",
    "QT_CURSO_TEC_CT": "Concomitante / Integrado (QT_CURSO_TEC_CT)",
    "QT_CURSO_TEC_NM": "Normal / Magistério (QT_CURSO_TEC_NM)",
    "QT_CURSO_TEC_CONC": "Concluinte (QT_CURSO_TEC_CONC)",
    "QT_CURSO_TEC_SUBS": "Subsequente (QT_CURSO_TEC_SUBS)",
    "QT_CURSO_TEC_EJA": "EJA Técnico (QT_CURSO_TEC_EJA)",
    "QT_CURSO_TEC_IFTP": "Itinerário de Formação Técnica (QT_CURSO_TEC_IFTP)",
    "QT_CURSO_TEC_IFTP_MT": "IFTP Médio-Técnico (QT_CURSO_TEC_IFTP_MT)",
    "QT_CURSO_TEC_IFTP_OTME": "IFTP Outras Modalidades (QT_CURSO_TEC_IFTP_OTME)",
    "QT_CURSO_TEC_IFTP_OE": "IFTP Outros Eixos (QT_CURSO_TEC_IFTP_OE)",
    "QT_CURSO_TEC_IFTP_CT": "IFTP Concomitante (QT_CURSO_TEC_IFTP_CT)"
}

OPCOES_CURSOS_MAT = {
    "QT_MAT_CURSO_TEC": "Matrículas em Cursos Técnicos (QT_MAT_CURSO_TEC)",
    "QT_MAT_CURSO_TEC_CT": "Matrículas Concomitante / Integrado (QT_MAT_CURSO_TEC_CT)",
    "QT_MAT_CURSO_TEC_NM": "Matrículas Normal / Magistério (QT_MAT_CURSO_TEC_NM)",
    "QT_MAT_CURSO_TEC_CONC": "Matrículas Concluinte (QT_MAT_CURSO_TEC_CONC)",
    "QT_MAT_TEC_SUBS": "Matrículas Subsequentes (QT_MAT_TEC_SUBS)",
    "QT_MAT_TEC_EJA": "Matrículas EJA Técnico (QT_MAT_TEC_EJA)",
    "QT_MAT_CURSO_TEC_IFTP": "Matrículas IFTP (QT_MAT_CURSO_TEC_IFTP)",
    "QT_MAT_CURSO_TEC_IFTP_MT": "Matrículas IFTP Médio-Técnico (QT_MAT_CURSO_TEC_IFTP_MT)",
    "QT_MAT_CURSO_TEC_IFTP_OTME": "Matrículas IFTP Outras Modalidades (QT_MAT_CURSO_TEC_IFTP_OTME)",
    "QT_MAT_CURSO_TEC_IFTP_OE": "Matrículas IFTP Outros Eixos (QT_MAT_CURSO_TEC_IFTP_OE)",
    "QT_MAT_CURSO_TEC_SUBS": "Matrículas Cursos Subs. Alternativos (QT_MAT_CURSO_TEC_SUBS)",
    "QT_MAT_CURSO_TEC_IFTP_CT": "Matrículas IFTP Concomitante (QT_MAT_CURSO_TEC_IFTP_CT)",
    "QT_MAT_CURSO_TEC_EJA": "Matrículas Cursos EJA (QT_MAT_CURSO_TEC_EJA)"
}

# =============================================================================
# MÉTRICAS DINÂMICAS DA SUPER TABELA
# =============================================================================

GRUPOS_METRICAS_QT = [
    "Etapa Comum",
    "Etapas: Profissional, EJA e Especial",
    "Sexo",
    "Raça/Cor",
    "Faixa Etária",
    "Turno",
    "Integral",
]

CHAVES_GRUPOS_METRICAS_QT = {
    "Etapa Comum": "etapa",
    "Etapas: Profissional, EJA e Especial": "modalidade",
    "Sexo": "sexo",
    "Raça/Cor": "raca_cor",
    "Faixa Etária": "faixa_etaria",
    "Turno": "turno",
    "Integral": "integral",
}

def categorias_metrica_qt(sufixo):
    s = str(sufixo).strip().upper()
    if s in {"BAS_FEM", "BAS_MASC"}: return "Sexo"
    if s in {"BAS_BRANCA", "BAS_PRETA", "BAS_PARDA", "BAS_AMARELA", "BAS_INDIGENA", "BAS_ND"}: return "Raça/Cor"
    if re.search(r"(^|_)INT($|_)", s): return "Integral"
    if re.search(r"_(D|N|DM|DV)$", s): return "Turno"
    if re.search(r"(^|_)(0_3|4_5|6_10|11_14|15_17|18_MAIS)(_|$)", s): return "Faixa Etária"
    if s in {"PROF", "EJA", "ESP"} or s.startswith(("PROF_", "EJA_", "ESP_", "MED_IFTP_")) or s == "MED_IFTP":
        return "Etapas: Profissional, EJA e Especial"
    return "Etapa Comum"

def descricao_sufixo_qt(sufixo):
    s_upper = str(sufixo).strip().upper()
    coluna_mat = f"QT_MAT_{s_upper}"
    for mapa in [OPCOES_ETAPAS, OPCOES_SEXO, OPCOES_RACA, OPCOES_IDADE, OPCOES_TURNO]:
        if coluna_mat in mapa: return mapa[coluna_mat].split(" (")[0]
    tokens = {
        "BAS": "Educação Básica", "INF": "Educação Infantil", "CRE": "Creche",
        "PRE": "Pré-escola", "FUND": "Ensino Fundamental", "AI": "Anos Iniciais",
        "AF": "Anos Finais", "MED": "Ensino Médio", "PROF": "Educação Profissional",
        "TEC": "Técnico", "EJA": "EJA", "ESP": "Educação Especial",
        "CC": "Classes Comuns", "CE": "Classes Exclusivas", "FEM": "Feminino",
        "MASC": "Masculino", "BRANCA": "Branca", "PRETA": "Preta",
        "PARDA": "Parda", "AMARELA": "Amarela", "INDIGENA": "Indígena",
        "ND": "Não declarado", "INT": "Integral", "D": "Diurno",
        "N": "Noturno", "EAD": "Educação a distância", "DM": "Manhã", "DV": "Tarde"
    }
    partes = [tokens.get(parte, parte.replace("-", " ").title()) for parte in s_upper.split("_")]
    return " · ".join(partes) or s_upper

def construir_opcoes_metricas_qt(colunas_df):
    colunas = {str(c).strip().upper() for c in colunas_df}
    sufixos = {col[len("QT_MAT_"):] for col in colunas if col.startswith("QT_MAT_")} | {col[len("QT_TUR_"):] for col in colunas if col.startswith("QT_TUR_")}
    grupos = {nome: {} for nome in GRUPOS_METRICAS_QT}
    for sufixo in sorted(sufixos):
        col_mat, col_tur = f"QT_MAT_{sufixo}", f"QT_TUR_{sufixo}"
        tem_mat, tem_tur = col_mat in colunas, col_tur in colunas
        categoria, descricao = categorias_metrica_qt(sufixo), descricao_sufixo_qt(sufixo)
        codigos = [c for c, t in [(col_mat, tem_mat), (col_tur, tem_tur)] if t]
        grupos[categoria][sufixo] = f"{descricao} ({' | '.join(codigos)})"
    return grupos, []

def _sincronizar_selecao_metricas(state_key, todos_key, item_data, widget_key, rotulo):
    selecionados = set(st.session_state.get(state_key, []))
    if st.session_state.get(widget_key, False): selecionados.add(rotulo)
    else: selecionados.discard(rotulo)
    st.session_state[state_key] = [r for _wk, r in item_data if r in selecionados]
    st.session_state[todos_key] = len(st.session_state[state_key]) == len(item_data)

def _alternar_todas_metricas(state_key, todos_key, item_data):
    marcar = bool(st.session_state.get(todos_key, False))
    for widget_key, rotulo in item_data: st.session_state[widget_key] = marcar
    st.session_state[state_key] = [rotulo for _widget_key, rotulo in item_data] if marcar else []

def criar_seletor_metricas(titulo, opcoes, chave):
    opcoes = opcoes or {}
    pares = list(opcoes.items())
    if not pares: return []
    item_data = [(f"{chave}__item__{sufixo}", rotulo) for sufixo, rotulo in pares]
    rotulos_validos = [rotulo for _wk, rotulo in item_data]
    state_key, todos_key, busca_key = f"{chave}__popover_selecionados", f"{chave}__popover_todos", f"{chave}__busca_input"

    if state_key not in st.session_state:
        st.session_state[state_key] = [x for x in st.session_state.get(f"{chave}__multi_v4", []) if x in rotulos_validos]

    selecionados_salvos = set(st.session_state.get(state_key, []))
    for widget_key, rotulo in item_data:
        if widget_key not in st.session_state: st.session_state[widget_key] = rotulo in selecionados_salvos
    st.session_state[todos_key] = bool(item_data) and len(selecionados_salvos) == len(item_data)

    with st.popover(titulo):
        termo_busca = st.text_input("🔎 Pesquisar termo ou código:", key=busca_key, placeholder="Ex: creche, diurno...").strip().lower()
        st.checkbox("Todos", key=todos_key, on_change=_alternar_todas_metricas, args=(state_key, todos_key, item_data))
        st.markdown("---")
        for widget_key, rotulo in item_data:
            if not termo_busca or termo_busca in str(rotulo).lower():
                st.checkbox(str(rotulo), key=widget_key, on_change=_sincronizar_selecao_metricas, args=(state_key, todos_key, item_data, widget_key, rotulo))
    return list(st.session_state.get(state_key, []))

ANOS_ESCOLAS_DIC = {str(a): str(a) for a in range(2007, 2026)}
ANOS_TECNICOS_DIC = {str(a): str(a) for a in range(2023, 2026)}

def fmt_num(valor):
    if valor is None or pd.isna(valor): return "0"
    return f"{int(valor):,}".replace(",", ".")

def formatar_anos(lista_anos):
    if not lista_anos: return "Todos"
    anos_ordenados = sorted([int(a) for a in lista_anos])
    if len(anos_ordenados) == 1: return str(anos_ordenados[0])
    elif len(anos_ordenados) == 2: return f"{anos_ordenados[0]} e {anos_ordenados[1]}"
    else: return f"{anos_ordenados[0]} a {anos_ordenados[-1]}"

def formatar_legenda_filtros(ano_inicio, ano_fim, municipio_sel, nre_sel, dep_sel, loc_sel, itens_metricas):
    texto_base = f"Evolução de {ano_inicio} a {ano_fim}"
    partes_filtros = []
    if nre_sel and nre_sel not in ["Todos", "Todas"]: partes_filtros.append(f"NRE: {nre_sel}")
    if municipio_sel and municipio_sel not in ["Todas", "Todos"]: partes_filtros.append(f"Município: {municipio_sel}")
    if dep_sel: partes_filtros.append(f"Rede: {', '.join(dep_sel) if isinstance(dep_sel, list) else dep_sel}")
    if loc_sel and loc_sel not in ["Todas", "Todos"]: partes_filtros.append(f"Localização: {loc_sel}")
    if itens_metricas:
        lista_limpa = [str(m).split(" (")[0] for m in itens_metricas]
        if len(lista_limpa) == 1: partes_filtros.append(lista_limpa[0])
        elif len(lista_limpa) == 2: partes_filtros.append(f"{lista_limpa[0]} e {lista_limpa[1]}")
        else: partes_filtros.append(f"{lista_limpa[0]}, {lista_limpa[1]} e outros")
    return f"{texto_base} - {' | '.join(partes_filtros)}" if partes_filtros else texto_base

def criar_filtro_checkboxes(titulo, opcoes, chave, valor_padrao=None):
    if not opcoes: return []
    opcoes_lista = list(opcoes.values()) if isinstance(opcoes, dict) else list(opcoes)
    opcoes_lista = list(dict.fromkeys(opcoes_lista))
    estado_chave, todos_chave = f"{chave}__estado", f"{chave}__todos"
    inicial = valor_padrao if valor_padrao is not None else []
    if estado_chave not in st.session_state: st.session_state[estado_chave] = [x for x in list(inicial) if x in opcoes_lista]
    selecionados = [x for x in st.session_state[estado_chave] if x in opcoes_lista]
    todos_atual = (len(selecionados) == len(opcoes_lista) and len(opcoes_lista) > 0)

    with st.popover(titulo):
        todos_novo = st.checkbox("Todos", value=todos_atual, key=todos_chave)
        if todos_novo != todos_atual:
            selecionados = opcoes_lista.copy() if todos_novo else []
            st.session_state[estado_chave] = selecionados
            for i in range(len(opcoes_lista)): st.session_state[f"{chave}__item_{i}"] = todos_novo
        st.markdown("---")
        novos_selecionados = []
        for i, opcao in enumerate(opcoes_lista):
            item_key = f"{chave}__item_{i}"
            if item_key not in st.session_state: st.session_state[item_key] = opcao in selecionados
            if st.checkbox(str(opcao), key=item_key): novos_selecionados.append(opcao)
        st.session_state[estado_chave] = novos_selecionados
    return st.session_state[estado_chave]

def criar_filtro_selectbox(titulo, opcoes, key, valor_padrao="Todas"):
    opcoes = list(opcoes)
    if not opcoes: opcoes = [valor_padrao]
    valor_atual = st.session_state.get(key, valor_padrao)
    if valor_atual not in opcoes:
        valor_atual = valor_padrao if valor_padrao in opcoes else opcoes[0]
        st.session_state[key] = valor_atual
    return st.selectbox(titulo, options=opcoes, index=opcoes.index(valor_atual), key=key)

def get_opcoes_cruzadas_completas(df_in, nre_sel=None, mun_sel=None, dep_sel=None, loc_sel=None, cod_sel=None, nome_sel=None, regular_sel=None):
    nre_ativo = nre_sel if nre_sel not in [None, "", "Todas", "Todos"] else None
    dep_sel = list(dep_sel or [])
    loc_ativo = loc_sel if loc_sel not in [None, "", "Todas", "Todos"] else None
    mun_ativo = mun_sel if mun_sel not in [None, "", "Todas", "Todos"] else None
    cod_ativo = str(cod_sel).split(".")[0].strip() if cod_sel not in [None, "", "Todos"] else None
    nome_ativo = str(nome_sel).strip() if nome_sel not in [None, "", "Todas", "Todos"] else None
    regular_ativo = str(regular_sel).strip() if regular_sel not in [None, "", "Todas", "Todos"] else None

    def aplicar_filtros(exceto=None):
        df = df_in
        if exceto != "nre" and nre_ativo is not None and "NO_NRE" in df.columns:
            df = df[df["NO_NRE"].astype(str).str.strip() == nre_ativo]
        if exceto != "mun" and mun_ativo is not None and "NO_MUNICIPIO" in df.columns:
            df = df[df["NO_MUNICIPIO"].astype(str).str.strip() == mun_ativo]
        if exceto != "dep" and dep_sel and "TP_DEPENDENCIA" in df.columns:
            deps_ids = [str(d).split(" - ")[0].strip() for d in dep_sel]
            df = df[df["TP_DEPENDENCIA"].astype(str).str.split(".").str[0].str.strip().isin(deps_ids)]
        if exceto != "loc" and loc_ativo is not None and "TP_LOCALIZACAO" in df.columns:
            loc_id = str(loc_ativo).split(" - ")[0].strip()
            df = df[df["TP_LOCALIZACAO"].astype(str).str.split(".").str[0].str.strip() == loc_id]
        if exceto != "cod" and cod_ativo is not None and "CO_ENTIDADE" in df.columns:
            df = df[df["CO_ENTIDADE"].astype(str).str.split(".").str[0].str.strip() == cod_ativo]
        if exceto != "nome" and nome_ativo is not None and "NO_ENTIDADE" in df.columns:
            df = df[df["NO_ENTIDADE"].astype(str).str.strip() == nome_ativo]
        if exceto != "regular" and regular_ativo is not None and "IN_PODER_PUBLICO_PARCERIA" in df.columns:
            reg_id = regular_ativo.split(" - ")[0].strip()
            df = df[df["IN_PODER_PUBLICO_PARCERIA"].astype(str).str.split(".").str[0].str.strip() == reg_id]
        return df

    df_nre = aplicar_filtros("nre")
    op_nre = sorted(df_nre["NO_NRE"].dropna().astype(str).str.strip().unique()) if "NO_NRE" in df_nre.columns else []
    df_mun = aplicar_filtros("mun")
    op_mun = sorted(df_mun["NO_MUNICIPIO"].dropna().astype(str).str.strip().unique()) if "NO_MUNICIPIO" in df_mun.columns else []
    df_dep = aplicar_filtros("dep")
    op_dep = sorted(df_dep["TP_DEPENDENCIA"].dropna().astype(str).str.split(".").str[0].str.strip().unique()) if "TP_DEPENDENCIA" in df_dep.columns else []
    df_loc = aplicar_filtros("loc")
    op_loc = sorted(df_loc["TP_LOCALIZACAO"].dropna().astype(str).str.split(".").str[0].str.strip().unique()) if "TP_LOCALIZACAO" in df_loc.columns else []
    df_cod = aplicar_filtros("cod")
    op_cod = sorted(df_cod["CO_ENTIDADE"].dropna().astype(str).str.split(".").str[0].str.strip().unique()) if "CO_ENTIDADE" in df_cod.columns else []
    df_nome = aplicar_filtros("nome")
    op_nome = sorted(df_nome["NO_ENTIDADE"].dropna().astype(str).str.strip().unique()) if "NO_ENTIDADE" in df_nome.columns else []

    dic_dep = {k: v for k, v in MAP_DEPENDENCIA.items() if k in op_dep}
    dic_loc = {k: v for k, v in MAP_LOCALIZACAO.items() if k in op_loc}
    return ["Todas"] + op_nre, ["Todas"] + op_mun, dic_dep, ["Todas"] + list(dic_loc.values()), ["Todos"] + op_cod, ["Todas"] + op_nome, ["Todas"] + ["1 - Sim", "0 - Não"]

def sql_int_safe(coluna):
    return f"TRY_CAST(SPLIT_PART(TRIM(CAST({coluna} AS VARCHAR)), '.', 1) AS INTEGER)"

def extrair_chaves_por_rotulos(rotulos, dic):
    if not rotulos: return []
    inv_map = {v: k for k, v in dic.items()}
    return [inv_map.get(r) for r in rotulos if r in inv_map]

def quebrar_anos_em_lotes(anos, tamanho=3):
    anos_limpos = sorted({int(a) for a in (anos or [])})
    for inicio in range(0, len(anos_limpos), tamanho):
        yield anos_limpos[inicio:inicio + tamanho]

def identificador_sql(nome_coluna):
    return '"' + str(nome_coluna).replace('"', '""') + '"'

def obter_colunas_parquet(caminho_parquet):
    con = duckdb.connect()
    try:
        return [str(linha[0]).strip().upper() for linha in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{caminho_parquet}')").fetchall()]
    finally:
        con.close()

def montar_where_escolas(where_base="", anos=None, nre=None, municipio=None, dependencias=None, localizacao=None, codigo=None, nome=None, poder_publico=None):
    condicoes = []
    if where_base: condicoes.append(f"({where_base})")
    if anos: condicoes.append(f"{sql_int_safe('NU_ANO_CENSO')} IN ({', '.join(str(int(a)) for a in anos)})")
    if nre and nre not in ["Todas", "Todos"]: condicoes.append(f"TRIM(CAST(NO_NRE AS VARCHAR)) = '{str(nre).replace('\'', '\'\'')}'")
    if municipio and municipio not in ["Todas", "Todos"]: condicoes.append(f"TRIM(CAST(NO_MUNICIPIO AS VARCHAR)) = '{str(municipio).replace('\'', '\'\'')}'")
    if dependencias: condicoes.append(f"{sql_int_safe('TP_DEPENDENCIA')} IN ({', '.join(map(str, [int(d.split(' - ')[0]) for d in dependencias]))})")
    if localizacao and localizacao not in ["Todas", "Todos"]: condicoes.append(f"{sql_int_safe('TP_LOCALIZACAO')} = {int(localizacao.split(' - ')[0])}")
    if codigo and codigo not in ["Todos", "Todas"]: condicoes.append(f"TRIM(SPLIT_PART(CAST(CO_ENTIDADE AS VARCHAR), '.', 1)) = '{str(codigo).split('.')[0].strip().replace('\'', '\'\'')}'")
    if nome and nome not in ["Todas", "Todos"]: condicoes.append(f"TRIM(CAST(NO_ENTIDADE AS VARCHAR)) = '{str(nome).replace('\'', '\'\'')}'")
    if poder_publico and poder_publico not in ["Todas", "Todos"]: condicoes.append(f"{sql_int_safe('IN_PODER_PUBLICO_PARCERIA')} = {int(poder_publico.split(' - ')[0])}")
    return " AND ".join(condicoes)

def consultar_contagens_escolas(caminho_parquet, where_clause):
    con = duckdb.connect()
    try:
        sql = f"SELECT COUNT(DISTINCT CO_ENTIDADE) AS ESCOLAS, COUNT(*) AS REGISTROS FROM read_parquet('{caminho_parquet}')"
        if where_clause: sql += f" WHERE {where_clause}"
        escolas, registros = con.execute(sql).fetchone()
        return int(escolas or 0), int(registros or 0)
    finally:
        con.close()

def consultar_somas_metricas_parquet(caminho_parquet, where_clause, colunas):
    colunas = list(dict.fromkeys(colunas or []))
    if not colunas: return {}
    expressoes = [f"COALESCE(SUM(TRY_CAST({identificador_sql(col)} AS DOUBLE)), 0) AS {identificador_sql(col)}" for col in colunas]
    sql = f"SELECT {', '.join(expressoes)} FROM read_parquet('{caminho_parquet}')"
    if where_clause: sql += f" WHERE {where_clause}"
    con = duckdb.connect()
    try:
        linha = con.execute(sql).fetchone()
        return {col: (linha[i] or 0) for i, col in enumerate(colunas)}
    finally:
        con.close()

def consultar_evolucao_metricas_lotes(caminho_parquet, where_base, anos, colunas_mat, colunas_tur, tamanho_lote=3):
    colunas_soma = list(dict.fromkeys((colunas_mat or []) + (colunas_tur or [])))
    if not anos or not colunas_soma: return pd.DataFrame(columns=["ANO", "Matrículas", "Turmas"])
    expressoes = [f"COALESCE(SUM(TRY_CAST({identificador_sql(col)} AS DOUBLE)), 0) AS {identificador_sql(col)}" for col in colunas_soma]
    registros = []
    con = duckdb.connect()
    try:
        for lote_anos in quebrar_anos_em_lotes(anos, tamanho_lote):
            where_lote = montar_where_escolas(where_base, anos=lote_anos)
            sql = f"SELECT {sql_int_safe('NU_ANO_CENSO')} AS ANO, {', '.join(expressoes)} FROM read_parquet('{caminho_parquet}') WHERE {where_lote} GROUP BY ANO ORDER BY ANO"
            resultado_lote = con.execute(sql).df()
            for _, linha in resultado_lote.iterrows():
                row_data = {"ANO": int(linha["ANO"])}
                for c in colunas_mat: row_data[c] = float(linha.get(c, 0) or 0)
                for c in colunas_tur: row_data[c] = float(linha.get(c, 0) or 0)
                registros.append(row_data)
    finally:
        con.close()
    return pd.DataFrame(registros)

def consultar_escolas_preview(caminho_parquet, where_clause, colunas, limite=1000):
    if not colunas: return pd.DataFrame()
    sql = f"SELECT {', '.join(identificador_sql(c) for c in colunas)} FROM read_parquet('{caminho_parquet}')"
    if where_clause: sql += f" WHERE {where_clause}"
    sql += f" LIMIT {int(limite)}"
    con = duckdb.connect()
    try:
        df = con.execute(sql).df()
        df.columns = df.columns.str.strip().str.upper()
        return df
    finally:
        con.close()

def exportar_escolas_excel_lotes(caminho_parquet, where_base, anos, colunas, tamanho_lote=3):
    from openpyxl import Workbook
    saida = io.BytesIO()
    workbook = Workbook(write_only=True)
    planilha, linhas_na_planilha, planilha_numero = workbook.create_sheet(title="Relatorio_1"), 0, 1
    planilha.append(list(colunas))
    con = duckdb.connect()
    try:
        lotes = list(quebrar_anos_em_lotes(anos, tamanho_lote)) if anos else [None]
        for lote_anos in lotes:
            where_lote = montar_where_escolas(where_base, anos=lote_anos)
            sql = f"SELECT {', '.join(identificador_sql(c) for c in colunas)} FROM read_parquet('{caminho_parquet}')"
            if where_lote: sql += f" WHERE {where_lote}"
            with con.sql(sql).to_arrow_reader(batch_size=50_000) as leitor:
                for lote_arrow in leitor:
                    for registro in lote_arrow.to_pylist():
                        if linhas_na_planilha >= 1_048_575:
                            planilha_numero += 1
                            planilha = workbook.create_sheet(title=f"Relatorio_{planilha_numero}")
                            planilha.append(list(colunas))
                            linhas_na_planilha = 0
                        planilha.append([registro.get(c) for c in colunas])
                        linhas_na_planilha += 1
    finally:
        con.close()
    workbook.save(saida)
    return saida.getvalue()

def converter_df_para_excel(df):
    df_limpo = df.copy()
    for col in df_limpo.select_dtypes(include=['object', 'string']).columns:
        df_limpo[col] = df_limpo[col].fillna('').astype(str)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_limpo.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

CAMINHO_ESCOLAS_PARQUET = "v1_super_tabela_escolas.parquet"
CAMINHO_TECNICOS_PARQUET = "v2_super_tabela_cursos_tecnicos.parquet"

@st.cache_data(show_spinner="A carregar metadados de escolas para os filtros...")
def carregar_tabela_escolas(caminho, _mod):
    df = pd.read_parquet(caminho, engine="pyarrow")
    df.columns = df.columns.str.strip().str.upper()
    return df

@st.cache_data(show_spinner="A carregar a Tabela de Cursos Técnicos...")
def carregar_tabela_tecnicos(caminho, _mod):
    df = pd.read_parquet(caminho, engine="pyarrow")
    df.columns = df.columns.str.strip().str.upper()
    return df

if not os.path.exists(CAMINHO_ESCOLAS_PARQUET) or not os.path.exists(CAMINHO_TECNICOS_PARQUET):
  st.error("ERRO: Os ficheiros Parquet não foram encontrados.")
  st.stop()

df_escolas_raw = carregar_tabela_escolas(CAMINHO_ESCOLAS_PARQUET, os.path.getmtime(CAMINHO_ESCOLAS_PARQUET))
df_tecnicos_raw = carregar_tabela_tecnicos(CAMINHO_TECNICOS_PARQUET, os.path.getmtime(CAMINHO_TECNICOS_PARQUET))

st.title("🏫 Sistema de Consulta - Microdados do Censo Escolar")
st.markdown("---")

aba_escolas, aba_tecnicos, aba_obs, aba_dic = st.tabs([
    "🏛️ Super Tabela Escolas",
    "🎓 Cursos Técnicos",
    "⚠️ Observações e Limitações",
    "📖 Dicionário de Dados"
])

# =============================================================================
# ABA 1 - SUPER TABELA ESCOLAS
# =============================================================================

with aba_escolas:
    with st.expander("📶 **Painel de Filtros - Escolas**", expanded=True):
        if st.button("🧹 Limpar Todos os Filtros", key="btn_limpar_a1"):
            for chave in ["ano_esc_a1", "nre_esc_a1", "mun_esc_sel_a1", "dep_esc_a1", "loc_esc_a1", "nre_t_v1", "mun_t_v1", "dep_t_v1", "loc_t_v1", "cod_t_busca_v1", "nome_t_busca_v1", "reg_t_v1", "poder_g_v1", "nre_g1", "mun_g1", "dep_g1", "loc_g1", "cod_esc_busca_g1", "nome_esc_busca_g1", "ms_esc_confirmado"]:
                st.session_state.pop(chave, None)
            st.rerun()

        anos_estado_key_a1 = "ano_esc_a1__estado"
        if anos_estado_key_a1 not in st.session_state: st.session_state[anos_estado_key_a1] = ["2025"]
        ano_esc_val_temp = st.session_state.get(anos_estado_key_a1, ["2025"])

        df_esc_ano = df_escolas_raw[df_escolas_raw["NU_ANO_CENSO"].astype(str).str.split('.').str[0].str.strip().isin(ano_esc_val_temp)] if "NU_ANO_CENSO" in df_escolas_raw.columns and ano_esc_val_temp else df_escolas_raw

        cur_nre_p1, cur_mun_p1, cur_dep_p1, cur_loc_p1 = st.session_state.get("nre_esc_a1", "Todas"), st.session_state.get("mun_esc_sel_a1", "Todas"), st.session_state.get("dep_esc_a1", []), st.session_state.get("loc_esc_a1", "Todas")
        if "last_nre_esc_a1" not in st.session_state: st.session_state["last_nre_esc_a1"] = cur_nre_p1
        elif st.session_state["last_nre_esc_a1"] != cur_nre_p1:
            st.session_state["mun_esc_sel_a1"] = "Todas"
            st.session_state["last_nre_esc_a1"] = cur_nre_p1
            st.rerun()

        op_nre_p1, op_mun_p1, op_dep_p1, op_loc_p1, _, _, _ = get_opcoes_cruzadas_completas(df_esc_ano, nre_sel=cur_nre_p1, mun_sel=cur_mun_p1, dep_sel=cur_dep_p1, loc_sel=cur_loc_p1)

        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.5, 2])
        with c1: nre_esc = criar_filtro_selectbox("Núcleo Regional", op_nre_p1, "nre_esc_a1", "Todas")
        with c2: mun_esc = criar_filtro_selectbox("Município", op_mun_p1, "mun_esc_sel_a1", "Todas")
        with c3: loc_esc = criar_filtro_selectbox("Localização", op_loc_p1, "loc_esc_a1", "Todas")
        with c4: ano_esc = criar_filtro_checkboxes("Ano(s) do Censo", ANOS_ESCOLAS_DIC, "ano_esc_a1", valor_padrao=["2025"])
        with c5: dep_esc = criar_filtro_checkboxes("Rede", op_dep_p1, "dep_esc_a1")

    where_esc = []
    if nre_esc and nre_esc not in ["Todas", "Todos"]: where_esc.append(f"TRIM(CAST(NO_NRE AS VARCHAR)) = '{str(nre_esc).replace('\'', '\'\'')}'")
    if mun_esc and mun_esc != "Todas": where_esc.append(f"TRIM(CAST(NO_MUNICIPIO AS VARCHAR)) = '{str(mun_esc).replace('\'', '\'\'')}'")
    if dep_esc: where_esc.append(f"{sql_int_safe('TP_DEPENDENCIA')} IN ({', '.join(map(str, [int(d.split(' - ')[0]) for d in dep_esc]))})")
    if loc_esc and loc_esc not in ["Todas", "Todos"]: where_esc.append(f"{sql_int_safe('TP_LOCALIZACAO')} = {int(loc_esc.split(' - ')[0])}")

    where_clause_filtros_escolas = " AND ".join(where_esc)
    where_clause_escolas = montar_where_escolas(where_clause_filtros_escolas, anos=ano_esc)

    try:
        colunas_escolas = obter_colunas_parquet(CAMINHO_ESCOLAS_PARQUET)
        df_escolas_meta = df_escolas_raw
        if ano_esc and "NU_ANO_CENSO" in df_escolas_meta.columns:
            df_escolas_meta = df_escolas_meta.loc[df_escolas_meta["NU_ANO_CENSO"].astype(str).str.split('.').str[0].str.strip().isin([str(a) for a in ano_esc])]

        qtd_escolas_unicas, qtd_registros_escolas = consultar_contagens_escolas(CAMINHO_ESCOLAS_PARQUET, where_clause_escolas)
        m1, m2 = st.columns(2)
        m1.metric("Escolas Encontradas", fmt_num(qtd_escolas_unicas))
        m2.metric("Ano(s) do Censo", formatar_anos(ano_esc))

        # TABELAS DE TOTAIS
        with st.expander("🔎 **Seleção de Visualização Instantânea dos Totais de Matrículas e Turmas**", expanded=False):
            @st.fragment
            def mostrar_tabelas_por_ano_fragmento():
                cur_nre_t1, cur_mun_t1, cur_dep_t1, cur_loc_t1, cur_cod_t1, cur_nome_t1, cur_reg_t1 = st.session_state.get("nre_t_v1", "Todas"), st.session_state.get("mun_t_v1", "Todas"), st.session_state.get("dep_t_v1", []), st.session_state.get("loc_t_v1", "Todas"), st.session_state.get("cod_t_busca_v1", "Todos"), st.session_state.get("nome_t_busca_v1", "Todas"), st.session_state.get("reg_t_v1", "Todas")
                op_nre_t1, op_mun_t1, op_dep_t1, op_loc_t1, op_cod_t1, op_nome_t1, op_reg_t1 = get_opcoes_cruzadas_completas(df_escolas_meta, nre_sel=cur_nre_t1, mun_sel=cur_mun_t1, dep_sel=cur_dep_t1, loc_sel=cur_loc_t1, cod_sel=cur_cod_t1, nome_sel=cur_nome_t1, regular_sel=cur_reg_t1)

                t_fc1, t_fc2, t_fc3, t_fc4, t_fc5, t_fc6, t_fc7 = st.columns(7)
                with t_fc1: nre_t_sel = criar_filtro_selectbox("Núcleo Regional", op_nre_t1, "nre_t_v1", "Todas")
                with t_fc2: mun_t_sel = criar_filtro_selectbox("Município", op_mun_t1, "mun_t_v1", "Todas")
                with t_fc3: loc_t_sel = criar_filtro_selectbox("Localização", op_loc_t1, "loc_t_v1", "Todas")
                with t_fc4: cod_t_sel = criar_filtro_selectbox("Código INEP", op_cod_t1, "cod_t_busca_v1", "Todos")
                with t_fc5: nome_t_sel = criar_filtro_selectbox("Nome da Escola", op_nome_t1, "nome_t_busca_v1", "Todas")
                with t_fc6: reg_t_sel = criar_filtro_selectbox("Escolas Parceiras", op_reg_t1, "reg_t_v1", "Todas")
                with t_fc7: dep_t_sel = criar_filtro_checkboxes("Rede", op_dep_t1, "dep_t_v1")

                ano_totais_visualizacao = st.selectbox("Visualizar Ano:", options=list(ano_esc), key="ano_totais_visualizacao_a1") if len(ano_esc) > 1 else (ano_esc[0] if ano_esc else None)

                st.markdown("---")
                grupos_opcoes_t, _ = construir_opcoes_metricas_qt(colunas_escolas)
                selecoes_metricas_t = {ng: criar_seletor_metricas(ng, grupos_opcoes_t[ng], f"sel_{CHAVES_GRUPOS_METRICAS_QT[ng]}_t1") for ng in GRUPOS_METRICAS_QT}
                grupos_metricas_a1 = {ng: (sel, grupos_opcoes_t[ng]) for ng, sel in selecoes_metricas_t.items() if sel}

                if grupos_metricas_a1:
                    where_tabela = montar_where_escolas(where_clause_filtros_escolas, anos=[ano_totais_visualizacao] if ano_totais_visualizacao else ano_esc, nre=nre_t_sel, municipio=mun_t_sel, dependencias=dep_t_sel, localizacao=loc_t_sel, codigo=cod_t_sel, nome=nome_t_sel, poder_publico=reg_t_sel)
                    colunas_para_somar = []
                    for _t, (sel, op) in grupos_metricas_a1.items():
                        inverso = {rot: suf for suf, rot in op.items()}
                        for rot in sel:
                            suf = inverso.get(rot)
                            if suf:
                                for c in (f"QT_MAT_{suf}", f"QT_TUR_{suf}"):
                                    if c in colunas_escolas: colunas_para_somar.append(c)

                    totais_metricas = consultar_somas_metricas_parquet(CAMINHO_ESCOLAS_PARQUET, where_tabela, colunas_para_somar)
                    for tg, (sel_g, op_g) in grupos_metricas_a1.items():
                        linhas, tot_m, tot_t = [], 0, 0
                        inv_map = {v: k for k, v in op_g.items()}
                        for rot in sel_g:
                            suf = inv_map.get(rot)
                            if not suf: continue
                            cm, ct = f"QT_MAT_{suf}", f"QT_TUR_{suf}"
                            vm, vt = totais_metricas.get(cm, 0) if cm in colunas_escolas else 0, totais_metricas.get(ct, 0) if ct in colunas_escolas else 0
                            tot_m, tot_t = tot_m + vm, tot_t + vt
                            linhas.append({"Seleção": rot, "Matrículas": fmt_num(vm) if cm in colunas_escolas else "—", "Turmas": fmt_num(vt) if ct in colunas_escolas else "—"})
                        if linhas:
                            linhas.append({"Seleção": "TOTAL DO GRUPO", "Matrículas": fmt_num(tot_m), "Turmas": fmt_num(tot_t)})
                            df_resumo = pd.DataFrame([{"Ano": str(ano_totais_visualizacao), **l} for l in linhas])
                            with st.container(border=True):
                                st.markdown(f"#### {tg}")
                                st.dataframe(df_resumo, use_container_width=True, hide_index=True)
                                st.download_button(f"📥 Baixar {tg} Excel", data=converter_df_para_excel(df_resumo), file_name=f"tabela_{CHAVES_GRUPOS_METRICAS_QT[tg]}.xlsx", key=f"dl_exp_{tg}")
            mostrar_tabelas_por_ano_fragmento()

        # GRÁFICOS DA ABA 1 (Exatamente idênticos ao app.py local)
        with st.expander("🔎 **Seleção de Visualização Instantânea dos Gráficos de Matrículas e Turmas**", expanded=False):
            @st.fragment
            def mostrar_graficos_escolas_fragmento():
                st.markdown("### 📈 Evolução Histórica (Escolas)")
                anos_disp = sorted([int(a) for a in ano_esc]) if ano_esc else list(range(2007, 2026))
                anos_sel = st.slider("Selecione o Período Histórico", min_value=min(anos_disp), max_value=max(anos_disp), value=(min(anos_disp), max(anos_disp)), key="slider_a2") if min(anos_disp) != max(anos_disp) else (min(anos_disp), min(anos_disp))

                cur_nre_g1, cur_mun_g1, cur_dep_g1, cur_loc_g1, cur_cod_g1, cur_nome_g1, cur_reg_g1 = st.session_state.get("nre_g1", "Todas"), st.session_state.get("mun_g1", "Todas"), st.session_state.get("dep_g1", []), st.session_state.get("loc_g1", "Todas"), st.session_state.get("cod_esc_sel_g1", "Todos"), st.session_state.get("nome_esc_sel_g1", "Todas"), st.session_state.get("poder_g_v1", "Todas")
                op_nre_g1, op_mun_g1, op_dep_g1, op_loc_g1, op_cod_g1, op_nome_g1, op_reg_g1 = get_opcoes_cruzadas_completas(df_escolas_meta, nre_sel=cur_nre_g1, mun_sel=cur_mun_g1, dep_sel=cur_dep_g1, loc_sel=cur_loc_g1, cod_sel=cur_cod_g1, nome_sel=cur_nome_g1, regular_sel=cur_reg_g1)

                g_c1, g_c2, g_c3, g_c4, g_c5, g_c6, g_c7 = st.columns(7)
                with g_c1: nre_esc_graf = criar_filtro_selectbox("Núcleo Regional", op_nre_g1, "nre_g1", "Todas")
                with g_c2: mun_esc_graf = criar_filtro_selectbox("Município", op_mun_g1, "mun_g1", "Todas")
                with g_c3: loc_esc_graf = criar_filtro_selectbox("Localização", op_loc_g1, "loc_g1", "Todas")
                with g_c4: cod_esc_sel_g = criar_filtro_selectbox("Código INEP", op_cod_g1, "cod_esc_sel_g1", "Todos")
                with g_c5: nome_esc_sel_g = criar_filtro_selectbox("Nome da Escola", op_nome_g1, "nome_esc_sel_g1", "Todas")
                with g_c6: reg_g_sel = criar_filtro_selectbox("Escolas Parceiras", op_reg_g1, "poder_g_v1", "Todas")
                with g_c7: dep_esc_graf = criar_filtro_checkboxes("Rede", op_dep_g1, "dep_g1")

                st.markdown("##### Métrica Específica para os Gráficos")
                grupos_opcoes_g, _ = construir_opcoes_metricas_qt(colunas_escolas)
                selecoes_metricas_g = {ng: criar_seletor_metricas(ng, grupos_opcoes_g[ng], f"sel_{CHAVES_GRUPOS_METRICAS_QT[ng]}_a2") for ng in GRUPOS_METRICAS_QT}
                grupos_metricas_a2 = {ng: (sel, grupos_opcoes_g[ng]) for ng, sel in selecoes_metricas_g.items() if sel}

                if grupos_metricas_a2:
                    anos_grafico = [str(a) for a in (ano_esc or anos_disp) if anos_sel[0] <= int(a) <= anos_sel[1]]
                    where_grafico = montar_where_escolas(where_clause_filtros_escolas, nre=nre_esc_graf, municipio=mun_esc_graf, dependencias=dep_esc_graf, localizacao=loc_esc_graf, codigo=cod_esc_sel_g, nome=nome_esc_sel_g, poder_publico=reg_g_sel)

                    for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_a2.items():
                        sufixos_grupo = extrair_chaves_por_rotulos(selecionados_grupo, opcoes_grupo)
                        if not sufixos_grupo: continue
                        colunas_mat_grupo = [f"QT_MAT_{s}" for s in sufixos_grupo if f"QT_MAT_{s}" in colunas_escolas]
                        colunas_turma_grupo = [f"QT_TUR_{s}" for s in sufixos_grupo if f"QT_TUR_{s}" in colunas_escolas]
                        if not (colunas_mat_grupo or colunas_turma_grupo) or not anos_grafico: continue

                        df_agrupado = consultar_evolucao_metricas_lotes(CAMINHO_ESCOLAS_PARQUET, where_grafico, anos_grafico, colunas_mat_grupo, colunas_turma_grupo, tamanho_lote=3)
                        if df_agrupado.empty: continue

                        st.markdown(f"### {titulo_grupo}")
                        st.caption(formatar_legenda_filtros(anos_sel[0], anos_sel[1], mun_esc_graf, nre_esc_graf, dep_esc_graf, loc_esc_graf, selecionados_grupo))

                        mapa_nomes = {f"QT_MAT_{s}": rot.split(" (")[0] for s, rot in opcoes_grupo.items()}
                        mapa_nomes.update({f"QT_TUR_{s}": f"{rot.split(' (')[0]} (Turmas)" for s, rot in opcoes_grupo.items()})

                        cols_mat = [c for c in colunas_mat_grupo if c in df_agrupado.columns]
                        cols_tur = [c for c in colunas_turma_grupo if c in df_agrupado.columns]
                        fig_mat, fig_tur = None, None

                        if cols_mat:
                            df_m = df_agrupado.melt(id_vars=['ANO'], value_vars=cols_mat, var_name='Metrica', value_name='Valor')
                            df_m['Metrica_Nome'] = df_m['Metrica'].map(mapa_nomes).fillna(df_m['Metrica'])
                            df_m['Valor_Fmt'] = df_m['Valor'].apply(lambda x: f"{int(x):,}".replace(",", "."))
                            fig_mat = px.line(df_m, x='ANO', y='Valor', color='Metrica_Nome', markers=True, custom_data=['Valor_Fmt'])
                            fig_mat.update_traces(hovertemplate="<b>Ano:</b> %{x}<br><b>Valor:</b> %{customdata[0]}<extra></extra>")
                            fig_mat.update_layout(separators=',.', hovermode="closest", title="Matrículas", xaxis_title="Ano do Censo", yaxis_title="Total de Matrículas")
                            fig_mat.update_xaxes(type='category', fixedrange=True)
                            fig_mat.update_yaxes(tickformat=',.0f', fixedrange=True)

                        if cols_tur:
                            df_t = df_agrupado.melt(id_vars=['ANO'], value_vars=cols_tur, var_name='Metrica', value_name='Valor')
                            df_t['Metrica_Nome'] = df_t['Metrica'].map(mapa_nomes).fillna(df_t['Metrica'])
                            df_t['Valor_Fmt'] = df_t['Valor'].apply(lambda x: f"{int(x):,}".replace(",", "."))
                            fig_tur = px.line(df_t, x='ANO', y='Valor', color='Metrica_Nome', markers=True, custom_data=['Valor_Fmt'])
                            fig_tur.update_traces(hovertemplate="<b>Ano:</b> %{x}<br><b>Valor:</b> %{customdata[0]}<extra></extra>")
                            fig_tur.update_layout(separators=',.', hovermode="closest", title="Turmas", xaxis_title="Ano do Censo", yaxis_title="Total de Turmas")
                            fig_tur.update_xaxes(type='category', fixedrange=True)
                            fig_tur.update_yaxes(tickformat=',.0f', fixedrange=True)

                        safe_key = CHAVES_GRUPOS_METRICAS_QT.get(titulo_grupo, "g")
                        if fig_mat and fig_tur:
                            g1, g2 = st.columns(2)
                            with g1: st.plotly_chart(fig_mat, use_container_width=True, config={'displayModeBar': False}, key=f"mat_{safe_key}")
                            with g2: st.plotly_chart(fig_tur, use_container_width=True, config={'displayModeBar': False}, key=f"tur_{safe_key}")
                        elif fig_mat: st.plotly_chart(fig_mat, use_container_width=True, config={'displayModeBar': False}, key=f"mat_{safe_key}")
                        elif fig_tur: st.plotly_chart(fig_tur, use_container_width=True, config={'displayModeBar': False}, key=f"tur_{safe_key}")
                        st.markdown("---")
            mostrar_graficos_escolas_fragmento()

        # PREVIEW E EXPORTAÇÃO
        @st.fragment
        def fragmento_tabela_escolas():
            with st.expander("⚙️ **Personalizar Colunas Adicionais do Relatório**", expanded=False):
                cols_obrigatorias = ['NU_ANO_CENSO', 'NO_REGIAO', 'SG_UF', 'CO_NRE', 'NO_NRE', 'CO_MUNICIPIO', 'NO_MUNICIPIO', 'CO_ENTIDADE', 'NO_ENTIDADE', 'TP_DEPENDENCIA', 'TP_LOCALIZACAO', 'TP_SITUACAO_FUNCIONAMENTO', 'IN_PODER_PUBLICO_PARCERIA', 'QT_MAT_BAS', 'QT_TUR_BAS']
                with st.form("form_cols_esc"):
                    cols_extras = st.multiselect("Marque colunas extras:", options=[c for c in colunas_escolas if c not in cols_obrigatorias], default=st.session_state.get("ms_esc_confirmado", []))
                    if st.form_submit_button("✔️ Inserir Colunas"): st.session_state["ms_esc_confirmado"] = cols_extras

            cols_finais = [c for c in list(dict.fromkeys(cols_obrigatorias + st.session_state.get("ms_esc_confirmado", []))) if c in colunas_escolas]
            df_exibir = consultar_escolas_preview(CAMINHO_ESCOLAS_PARQUET, montar_where_escolas(where_clause_filtros_escolas, anos=ano_esc), cols_finais, limite=1000)
            if not df_exibir.empty:
                st.info(f"💡 Apresenta as primeiras 1000 escolas. Total: {fmt_num(qtd_registros_escolas)} registros.")
                st.dataframe(df_exibir, use_container_width=True, height=500)
                if st.button("📄 Preparar Excel", key="btn_prep_exc_esc"):
                    with st.spinner("Preparando Excel..."):
                        st.session_state["_excel_escolas_bytes"] = exportar_escolas_excel_lotes(CAMINHO_ESCOLAS_PARQUET, where_clause_filtros_escolas, ano_esc, cols_finais, tamanho_lote=3)
                if st.session_state.get("_excel_escolas_bytes") is not None:
                    st.download_button("📥 Baixar Excel (.xlsx)", data=st.session_state["_excel_escolas_bytes"], file_name="censo_escolas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        fragmento_tabela_escolas()
    except Exception as e:
        st.error(f"Erro: {e}")

# =============================================================================
# ABA 2 - CURSOS TÉCNICOS
# =============================================================================

with aba_tecnicos:
    with st.expander("📶 **Painel de Filtros - Cursos Técnicos**", expanded=True):
        if st.button("🧹 Limpar Todos os Filtros", key="btn_limpar_a3"):
            for chave in ["ano_tec", "nre_tec", "mun_tec_sel_a3", "dep_tec", "loc_tec", "cod_tec_sel_a3", "nome_tec_sel_a3", "nre_t_v2", "mun_t_v2", "dep_t_v2", "loc_t_v2", "cod_t_busca_v2", "nome_t_busca_v2", "ms_tec_confirmado"]:
                st.session_state.pop(chave, None)
            st.rerun()

        anos_tec_estado_key = "ano_tec__estado"
        if anos_tec_estado_key not in st.session_state: st.session_state[anos_tec_estado_key] = ["2025"]
        ano_tec_val_temp = st.session_state.get(anos_tec_estado_key, ["2025"])
        df_tec_ano = df_tecnicos_raw[df_tecnicos_raw["NU_ANO_CENSO"].astype(str).str.split('.').str[0].str.strip().isin(ano_tec_val_temp)] if "NU_ANO_CENSO" in df_tecnicos_raw.columns and ano_tec_val_temp else df_tecnicos_raw

        cur_nre_p3, cur_mun_p3, cur_dep_p3, cur_loc_p3 = st.session_state.get("nre_tec", "Todas"), st.session_state.get("mun_tec_sel_a3", "Todas"), st.session_state.get("dep_tec", []), st.session_state.get("loc_tec", "Todas")
        op_nre_p3, op_mun_p3, op_dep_p3, op_loc_p3, _, _, _ = get_opcoes_cruzadas_completas(df_tec_ano, nre_sel=cur_nre_p3, mun_sel=cur_mun_p3, dep_sel=cur_dep_p3, loc_sel=cur_loc_p3)

        t1, t2, t3, t4, t5 = st.columns([2, 2, 2, 1.5, 2])
        with t1: nre_tec = criar_filtro_selectbox("Núcleo Regional", op_nre_p3, "nre_tec", "Todas")
        with t2: mun_tec = criar_filtro_selectbox("Município", op_mun_p3, "mun_tec_sel_a3", "Todas")
        with t3: loc_tec = criar_filtro_selectbox("Localização", op_loc_p3, "loc_tec", "Todas")
        with t4: ano_tec = criar_filtro_checkboxes("Ano(s) do Censo", ANOS_TECNICOS_DIC, "ano_tec", valor_padrao=["2025"])
        with t5: dep_tec = criar_filtro_checkboxes("Rede", op_dep_p3, "dep_tec")

    where_tec = []
    if ano_tec: where_tec.append(f"{sql_int_safe('NU_ANO_CENSO')} IN ({', '.join(ano_tec)})")
    if nre_tec and nre_tec not in ["Todas", "Todos"] and "NO_NRE" in df_tecnicos_raw.columns: where_tec.append(f"TRIM(CAST(NO_NRE AS VARCHAR)) = '{nre_tec.replace('\'', '\'\'')}'")
    if mun_tec and mun_tec not in ["Todas", "Todos"]: where_tec.append(f"TRIM(CAST(NO_MUNICIPIO AS VARCHAR)) = '{mun_tec.replace('\'', '\'\'')}'")
    if dep_tec: where_tec.append(f"{sql_int_safe('TP_DEPENDENCIA')} IN ({', '.join(map(str, [int(d.split(' - ')[0]) for d in dep_tec]))})")
    if loc_tec and loc_tec not in ["Todas", "Todos"]: where_tec.append(f"{sql_int_safe('TP_LOCALIZACAO')} = {int(loc_tec.split(' - ')[0])}")

    try:
        con = duckdb.connect()
        df_tecnicos = con.execute(f"SELECT * FROM df_tecnicos_raw" + (" WHERE " + " AND ".join(where_tec) if where_tec else "")).df()
        con.close()

        k1, k2, k3 = st.columns(3)
        k1.metric("Escolas Retornadas", fmt_num(df_tecnicos["CO_ENTIDADE"].nunique() if "CO_ENTIDADE" in df_tecnicos.columns else 0))
        k2.metric("Cursos Distintos Retornados", fmt_num(df_tecnicos["NO_CURSO_EDUC_PROFISSIONAL"].nunique() if "NO_CURSO_EDUC_PROFISSIONAL" in df_tecnicos.columns else 0))
        k3.metric("Ano(s) Selecionado(s)", formatar_anos(ano_tec))

        # GRÁFICOS DE CURSOS TÉCNICOS (Idênticos ao app.py local)
        with st.expander("🔎 **Seleção de Visualização Instantânea dos Gráficos de Matrículas e Cursos**", expanded=False):
            @st.fragment
            def mostrar_graficos_tecnicos_fragmento():
                st.markdown("### 📈 Evolução Histórica (Cursos Técnicos)")
                anos_tec_disp = sorted([int(a) for a in ano_tec]) if ano_tec else list(range(2023, 2026))
                anos_tec_sel = st.slider("Selecione o Período Histórico", min_value=min(anos_tec_disp), max_value=max(anos_tec_disp), value=(min(anos_tec_disp), max(anos_tec_disp)), key="slider_tec") if min(anos_tec_disp) != max(anos_tec_disp) else (min(anos_tec_disp), min(anos_tec_disp))

                cur_nre_g2, cur_mun_g2, cur_dep_g2, cur_loc_g2, cur_cod_g2, cur_nome_g2 = st.session_state.get("nre_g2", "Todas"), st.session_state.get("mun_g2", "Todas"), st.session_state.get("dep_g2", []), st.session_state.get("loc_g2", "Todas"), st.session_state.get("cod_tec_busca_g2", "Todos"), st.session_state.get("nome_tec_busca_g2", "Todas")
                op_nre_g2, op_mun_g2, op_dep_g2, op_loc_g2, op_cod_g2, op_nome_g2, _ = get_opcoes_cruzadas_completas(df_tecnicos, nre_sel=cur_nre_g2, mun_sel=cur_mun_g2, dep_sel=cur_dep_g2, loc_sel=cur_loc_g2, cod_sel=cur_cod_g2, nome_sel=cur_nome_g2)

                g_t1, g_t2, g_t3, g_t4, g_t5, g_t6 = st.columns(6)
                with g_t1: nre_tec_graf = criar_filtro_selectbox("Núcleo Regional", op_nre_g2, "nre_g2", "Todas")
                with g_t2: mun_tec_graf = criar_filtro_selectbox("Município", op_mun_g2, "mun_g2", "Todas")
                with g_t3: loc_tec_graf = criar_filtro_selectbox("Localização", op_loc_g2, "loc_g2", "Todas")
                with g_t4: cod_tec_sel_g = criar_filtro_selectbox("Código INEP", op_cod_g2, "cod_tec_busca_g2", "Todos")
                with g_t5: nome_tec_sel_g = criar_filtro_selectbox("Nome da Escola", op_nome_g2, "nome_tec_busca_g2", "Todas")
                with g_t6: dep_tec_graf = criar_filtro_checkboxes("Rede", op_dep_g2, "dep_g2")

                st.markdown("##### Descrição do Curso")
                gd1, gd2 = st.columns(2)
                op_areas_graf = ["Todas"] + sorted(df_tecnicos["NO_AREA_CURSO_PROFISSIONAL"].dropna().astype(str).str.strip().unique()) if "NO_AREA_CURSO_PROFISSIONAL" in df_tecnicos.columns else ["Todas"]
                op_nomes_graf = ["Todas"] + sorted(df_tecnicos["NO_CURSO_EDUC_PROFISSIONAL"].dropna().astype(str).str.strip().unique()) if "NO_CURSO_EDUC_PROFISSIONAL" in df_tecnicos.columns else ["Todas"]
                with gd1: sel_area_graf = criar_filtro_selectbox("Área do Curso", op_areas_graf, "sel_area_graf", "Todas")
                with gd2: sel_nome_curso_graf = criar_filtro_selectbox("Nome do Curso", op_nomes_graf, "sel_nome_curso_graf", "Todas")

                st.markdown("##### Métrica Específica para o Gráfico")
                gt1, gt2 = st.columns(2)
                with gt1: sel_qtd_tec_graf = criar_seletor_metricas("Quantidade de Cursos", OPCOES_CURSOS_QTD, "sel_qtd_tec_g1")
                with gt2: sel_mat_tec_graf = criar_seletor_metricas("Quantidade de Matrículas", OPCOES_CURSOS_MAT, "sel_mat_tec_g1")

                grupos_metricas_tec_graf = {}
                if sel_qtd_tec_graf: grupos_metricas_tec_graf["Quantidade de Cursos"] = (sel_qtd_tec_graf, OPCOES_CURSOS_QTD)
                if sel_mat_tec_graf: grupos_metricas_tec_graf["Quantidade de Matrículas"] = (sel_mat_tec_graf, OPCOES_CURSOS_MAT)

                if grupos_metricas_tec_graf:
                    df_base = df_tecnicos.copy()
                    if not df_base.empty:
                        df_base['ANO_INT'] = df_base['NU_ANO_CENSO'].astype(str).str.split('.').str[0].astype(int)
                        df_base = df_base[(df_base['ANO_INT'] >= anos_tec_sel[0]) & (df_base['ANO_INT'] <= anos_tec_sel[1])]
                        if nre_tec_graf and nre_tec_graf not in ["Todas", "Todos"] and "NO_NRE" in df_base.columns: df_base = df_base[df_base['NO_NRE'].astype(str).str.strip() == nre_tec_graf]
                        if mun_tec_graf and mun_tec_graf not in ["Todas", "Todos"]: df_base = df_base[df_base['NO_MUNICIPIO'].astype(str).str.strip() == mun_tec_graf]
                        if dep_tec_graf: df_base = df_base[df_base['TP_DEPENDENCIA'].astype(str).str.split('.').str[0].str.strip().isin([str(d.split(' - ')[0]) for d in dep_tec_graf])]
                        if sel_area_graf != "Todas" and "NO_AREA_CURSO_PROFISSIONAL" in df_base.columns: df_base = df_base[df_base['NO_AREA_CURSO_PROFISSIONAL'].astype(str).str.strip() == sel_area_graf]
                        if sel_nome_curso_graf != "Todas" and "NO_CURSO_EDUC_PROFISSIONAL" in df_base.columns: df_base = df_base[df_base['NO_CURSO_EDUC_PROFISSIONAL'].astype(str).str.strip() == sel_nome_curso_graf]

                    for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_tec_graf.items():
                        colunas_grupo = extrair_chaves_por_rotulos(selecionados_grupo, opcoes_grupo)
                        if not colunas_grupo: continue
                        cols_presentes = [c for c in list(dict.fromkeys(["ANO_INT"] + colunas_grupo)) if c in df_base.columns]
                        if df_base.empty or not cols_presentes: continue

                        df_sub = df_base[cols_presentes]
                        registos = []
                        for ano_idx, df_s in df_sub.groupby('ANO_INT'):
                            row_g = {'ANO': ano_idx}
                            for c in colunas_grupo:
                                row_g[c] = float(df_s[c].dropna().astype(str).str.replace(',', '.').astype(float).sum()) if c in df_s.columns else 0.0
                            registos.append(row_g)

                        df_agrupado = pd.DataFrame(registos)
                        if df_agrupado.empty: continue

                        mapa_nomes_tec = {s: rot.split(" (")[0] for s, rot in opcoes_grupo.items()}
                        cols_melt = [c for c in colunas_grupo if c in df_agrupado.columns]
                        if cols_melt:
                            df_melt = df_agrupado.melt(id_vars=['ANO'], value_vars=cols_melt, var_name='Metrica', value_name='Valor')
                            df_melt['Metrica_Nome'] = df_melt['Metrica'].map(mapa_nomes_tec).fillna(df_melt['Metrica'])
                            df_melt['Valor_Fmt'] = df_melt['Valor'].apply(lambda x: f"{int(x):,}".replace(",", "."))

                            st.markdown(f"### {titulo_grupo}")
                            st.caption(formatar_legenda_filtros(anos_tec_sel[0], anos_tec_sel[1], mun_tec_graf, nre_tec_graf, dep_tec_graf, loc_tec_graf, selecionados_grupo))

                            fig_tec = px.line(df_melt, x='ANO', y='Valor', color='Metrica_Nome', markers=True, custom_data=['Valor_Fmt'])
                            fig_tec.update_traces(hovertemplate="<b>Ano:</b> %{x}<br><b>Total:</b> %{customdata[0]}<extra></extra>")
                            fig_tec.update_layout(separators=',.', hovermode="closest", xaxis_title="Ano do Censo", yaxis_title=f"Total de {titulo_grupo}")
                            fig_tec.update_xaxes(type='category', fixedrange=True)
                            fig_tec.update_yaxes(tickformat=',.0f', fixedrange=True)

                            st.plotly_chart(fig_tec, use_container_width=True, config={'displayModeBar': False}, key=f"fig_tec_{titulo_grupo.lower().replace(' ', '_')}")
                            st.markdown("---")
            mostrar_graficos_tecnicos_fragmento()

        # PREVIEW E EXPORTAÇÃO TÉCNICA
        @st.fragment
        def fragmento_tabela_tecnicos():
            cols_obrigatorias_tec = ['NU_ANO_CENSO', 'NO_REGIAO', 'SG_UF', 'CO_NRE', 'NO_NRE', 'CO_MUNICIPIO', 'NO_MUNICIPIO', 'CO_ENTIDADE', 'NO_ENTIDADE', 'TP_DEPENDENCIA', 'TP_LOCALIZACAO', 'CO_CURSO_EDUC_PROFISSIONAL', 'NO_CURSO_EDUC_PROFISSIONAL', 'NO_AREA_CURSO_PROFISSIONAL', 'QT_MAT_CURSO_TEC', 'QT_CURSO_TEC']
            with st.expander("⚙️ **Personalizar Colunas Adicionais do Relatório**", expanded=False):
                with st.form("form_cols_tec"):
                    cols_extras = st.multiselect("Marque colunas extras:", options=[c for c in df_tecnicos.columns if c not in cols_obrigatorias_tec], default=st.session_state.get("ms_tec_confirmado", []))
                    if st.form_submit_button("✔️ Inserir Colunas"): st.session_state["ms_tec_confirmado"] = cols_extras

            cols_finais = [c for c in list(dict.fromkeys(cols_obrigatorias_tec + st.session_state.get("ms_tec_confirmado", []))) if c in df_tecnicos.columns]
            df_exibir = df_tecnicos[cols_finais] if not df_tecnicos.empty and cols_finais else df_tecnicos
            if not df_exibir.empty:
                st.info(f"💡 Apresenta os primeiros 1000 cursos. Total: {fmt_num(len(df_exibir))} registros.")
                st.dataframe(df_exibir.head(1000), use_container_width=True, height=500)
                st.download_button("📥 Baixar Cursos Excel (.xlsx)", data=converter_df_para_excel(df_exibir), file_name="cursos_tecnicos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        fragmento_tabela_tecnicos()
    except Exception as e:
        st.error(f"Erro: {e}")

# =============================================================================
# ABA 3 E 4
# =============================================================================
with aba_obs:
    st.markdown("## 🔎 Observações e Limitações Metodológicas")
    st.caption("Orientações para uso e interpretação dos dados extraídos do Censo Escolar (INEP)")
    st.markdown("---")
    with st.container(border=True):
        st.markdown("### 1. Ausência de Cruzamento Multidimensional Agregado")
        st.write("Os microdados refletem agregações por instituição. Não é possível realizar cruzamentos multidimensionais diretos entre variáveis categóricas distintas.")

with aba_dic:
    st.markdown("## 📖 Dicionário de Dados — Super Tabelas")
    st.caption("Consulta detalhada dos códigos originais das colunas e interpretações amigáveis.")
    st.markdown("---")
    df_dicionario = carregar_dicionario_dados(CAMINHO_DICIONARIO_PARQUET)
    if not df_dicionario.empty:
        st.dataframe(df_dicionario, use_container_width=True, hide_index=True, height=600)
        st.download_button("📥 Baixar Dicionário Completo (.xlsx)", data=converter_df_para_excel(df_dicionario), file_name="dicionario_super_tabelas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
