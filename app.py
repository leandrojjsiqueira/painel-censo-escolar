import pandas as pd
import streamlit as st
import duckdb
import os
import urllib.request
import time
import plotly.express as px
import io

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

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
    "QT_MAT_BAS_EAD": "Educação a Distância (QT_MAT_BAS_EAD)",
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

MAP_MAT_PARA_TUR = {
    "QT_MAT_BAS": "QT_TUR_BAS",
    "QT_MAT_INF": "QT_TUR_INF",
    "QT_MAT_INF_CRE": "QT_TUR_INF_CRE",
    "QT_MAT_INF_PRE": "QT_TUR_INF_PRE",
    "QT_MAT_FUND": "QT_TUR_FUND",
    "QT_MAT_FUND_AI": "QT_TUR_FUND_AI",
    "QT_MAT_FUND_AF": "QT_TUR_FUND_AF",
    "QT_MAT_MED": "QT_TUR_MED",
    "QT_MAT_PROF": "QT_TUR_PROF",
    "QT_MAT_PROF_TEC": "QT_TUR_PROF_TEC",
    "QT_MAT_EJA": "QT_TUR_EJA",
    "QT_MAT_EJA_FUND": "QT_TUR_EJA_FUND",
    "QT_MAT_EJA_MED": "QT_TUR_EJA_MED",
    "QT_MAT_ESP": "QT_TUR_ESP",
    "QT_MAT_ESP_CC": "Especial - Classes Comuns/Inclusão (QT_MAT_ESP_CC)",
    "QT_MAT_ESP_CE": "Especial - Classes Exclusivas (QT_MAT_ESP_CE)",
    "QT_MAT_BAS_D": "QT_TUR_BAS_D",
    "QT_MAT_BAS_N": "QT_TUR_BAS_N",
    "QT_MAT_BAS_EAD": "QT_TUR_BAS_EAD",
    "QT_MAT_INF_INT": "Infantil - Integral (QT_MAT_INF_INT)",
    "QT_MAT_INF_CRE_INT": "Creche - Integral (QT_MAT_INF_CRE_INT)",
    "QT_MAT_INF_PRE_INT": "Pré-Escola - Integral (QT_MAT_INF_PRE_INT)",
    "QT_MAT_FUND_INT": "Fundamental - Integral (QT_MAT_FUND_INT)",
    "QT_MAT_FUND_AI_INT": "Fund. Iniciais - Integral (QT_MAT_FUND_AI_INT)",
    "QT_MAT_FUND_AF_INT": "Fund. Finais - Integral (QT_MAT_FUND_AF_INT)",
    "QT_MAT_MED_INT": "Médio - Integral (QT_MAT_MED_INT)"
}

ANOS_ESCOLAS_DIC = {str(a): str(a) for a in range(2007, 2026)}
ANOS_TECNICOS_DIC = {str(a): str(a) for a in range(2023, 2026)}

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def fmt_num(valor):
    if valor is None or pd.isna(valor): return "0"
    return f"{int(valor):,}".replace(",", ".")

def formatar_anos(lista_anos):
    if not lista_anos:
        return "Todos"
    anos_ordenados = sorted([int(a) for a in lista_anos])
    qtd = len(anos_ordenados)
    if qtd == 1:
        return str(anos_ordenados[0])
    elif qtd == 2:
        return f"{anos_ordenados[0]} e {anos_ordenados[1]}"
    else:
        return f"{anos_ordenados[0]} a {anos_ordenados[-1]}"

def formatar_legenda_filtros(ano_inicio, ano_fim, municipio_sel, nre_sel, dep_sel, loc_sel, itens_metricas):
    texto_base = f"Evolução de {ano_inicio} a {ano_fim}"
    
    partes_filtros = []
    if nre_sel and nre_sel not in ["Todos", "Todas"]:
        partes_filtros.append(f"NRE: {nre_sel}")
    if municipio_sel and municipio_sel not in ["Todas", "Todos"]:
        partes_filtros.append(f"Município: {municipio_sel}")
    if dep_sel:
        partes_filtros.append(f"Rede: {', '.join(dep_sel) if isinstance(dep_sel, list) else dep_sel}")
    if loc_sel and loc_sel not in ["Todas", "Todos"]:
        partes_filtros.append(f"Localização: {loc_sel}")
        
    if itens_metricas:
        if len(itens_metricas) == 1:
            partes_filtros.append(itens_metricas[0])
        elif len(itens_metricas) == 2:
            partes_filtros.append(f"{itens_metricas[0]} e {itens_metricas[1]}")
        else:
            partes_filtros.append(f"{itens_metricas[0]}, {itens_metricas[1]} e outros")
            
    if partes_filtros:
        return f"{texto_base} - {' | '.join(partes_filtros)}"
    return texto_base

def criar_filtro_checkboxes(titulo, opcoes, chave, default=None, valor_padrao=None):
    if not opcoes:
        return []

    if isinstance(opcoes, dict):
        opcoes_lista = list(opcoes.values())
    else:
        opcoes_lista = list(opcoes)

    opcoes_lista = list(dict.fromkeys(opcoes_lista))

    estado_chave = f"{chave}__estado"
    todos_chave = f"{chave}__todos"

    if valor_padrao is not None:
        inicial = valor_padrao
    elif default is not None:
        inicial = default
    else:
        inicial = []

    if estado_chave not in st.session_state:
        st.session_state[estado_chave] = [
            x for x in list(inicial) if x in opcoes_lista
        ]

    selecionados = [
        x for x in st.session_state[estado_chave]
        if x in opcoes_lista
    ]

    todos_atual = (
        len(selecionados) == len(opcoes_lista)
        and len(opcoes_lista) > 0
    )

    with st.popover(titulo):
        todos_novo = st.checkbox(
            "Todos",
            value=todos_atual,
            key=todos_chave
        )

        if todos_novo != todos_atual:
            selecionados = opcoes_lista.copy() if todos_novo else []
            st.session_state[estado_chave] = selecionados

            for i in range(len(opcoes_lista)):
                st.session_state[f"{chave}__item_{i}"] = todos_novo

        st.markdown("---")

        novos_selecionados = []

        for i, opcao in enumerate(opcoes_lista):
            item_key = f"{chave}__item_{i}"

            if item_key not in st.session_state:
                st.session_state[item_key] = opcao in selecionados

            marcado = st.checkbox(
                str(opcao),
                key=item_key
            )

            if marcado:
                novos_selecionados.append(opcao)

        st.session_state[estado_chave] = novos_selecionados

    return st.session_state[estado_chave]

def criar_filtro_selectbox(titulo, opcoes, key, valor_padrao="Todas"):
    opcoes = list(opcoes)

    if not opcoes:
        opcoes = [valor_padrao]

    valor_atual = st.session_state.get(key, valor_padrao)

    if valor_atual not in opcoes:
        valor_atual = valor_padrao if valor_padrao in opcoes else opcoes[0]
        st.session_state[key] = valor_atual

    return st.selectbox(
        titulo,
        options=opcoes,
        index=opcoes.index(valor_atual),
        key=key,
        help=f"Selecione uma opção ou '{valor_padrao}' para incluir todos"
    )

def get_opcoes_cruzadas_completas(
    df_in,
    nre_sel=None,
    mun_sel=None,
    dep_sel=None,
    loc_sel=None,
    cod_sel=None,
    nome_sel=None
):
    nre_ativo = (
        nre_sel
        if nre_sel not in [None, "", "Todas", "Todos"]
        else None
    )
    dep_sel = list(dep_sel or [])
    
    loc_ativo = (
        loc_sel
        if loc_sel not in [None, "", "Todas", "Todos"]
        else None
    )

    mun_ativo = (
        mun_sel
        if mun_sel not in [None, "", "Todas", "Todos"]
        else None
    )

    cod_ativo = (
        str(cod_sel).split(".")[0].strip()
        if cod_sel not in [None, "", "Todos"]
        else None
    )

    nome_ativo = (
        str(nome_sel).strip()
        if nome_sel not in [None, "", "Todas", "Todos"]
        else None
    )

    def aplicar_filtros(exceto=None):
        df = df_in

        if exceto != "nre" and nre_ativo is not None and "NO_NRE" in df.columns:
            df = df[
                df["NO_NRE"].astype(str).str.strip() == nre_ativo
            ]

        if exceto != "mun" and mun_ativo is not None and "NO_MUNICIPIO" in df.columns:
            df = df[
                df["NO_MUNICIPIO"].astype(str).str.strip() == mun_ativo
            ]

        if exceto != "dep" and dep_sel and "TP_DEPENDENCIA" in df.columns:
            deps_ids = [
                str(d).split(" - ")[0].strip()
                for d in dep_sel
            ]
            df = df[
                df["TP_DEPENDENCIA"]
                .astype(str)
                .str.split(".")
                .str[0]
                .str.strip()
                .isin(deps_ids)
            ]

        if exceto != "loc" and loc_ativo is not None and "TP_LOCALIZACAO" in df.columns:
            loc_id = str(loc_ativo).split(" - ")[0].strip()
            df = df[
                df["TP_LOCALIZACAO"]
                .astype(str)
                .str.split(".")
                .str[0]
                .str.strip() == loc_id
            ]

        if exceto != "cod" and cod_ativo is not None and "CO_ENTIDADE" in df.columns:
            df = df[
                df["CO_ENTIDADE"]
                .astype(str)
                .str.split(".")
                .str[0]
                .str.strip() == cod_ativo
            ]

        if exceto != "nome" and nome_ativo is not None and "NO_ENTIDADE" in df.columns:
            df = df[
                df["NO_ENTIDADE"]
                .astype(str)
                .str.strip() == nome_ativo
            ]

        return df

    # NRE
    df_nre = aplicar_filtros("nre")
    op_nre = (
        sorted(
            df_nre["NO_NRE"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )
        if "NO_NRE" in df_nre.columns
        else []
    )

    # Município
    df_mun = aplicar_filtros("mun")
    op_mun = (
        sorted(
            df_mun["NO_MUNICIPIO"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )
        if "NO_MUNICIPIO" in df_mun.columns
        else []
    )

    # Rede
    df_dep = aplicar_filtros("dep")
    op_dep = (
        sorted(
            df_dep["TP_DEPENDENCIA"]
            .dropna()
            .astype(str)
            .str.split(".")
            .str[0]
            .str.strip()
            .unique()
        )
        if "TP_DEPENDENCIA" in df_dep.columns
        else []
    )

    # Localização
    df_loc = aplicar_filtros("loc")
    op_loc = (
        sorted(
            df_loc["TP_LOCALIZACAO"]
            .dropna()
            .astype(str)
            .str.split(".")
            .str[0]
            .str.strip()
            .unique()
        )
        if "TP_LOCALIZACAO" in df_loc.columns
        else []
    )

    # Código INEP
    df_cod = aplicar_filtros("cod")
    op_cod = (
        sorted(
            df_cod["CO_ENTIDADE"]
            .dropna()
            .astype(str)
            .str.split(".")
            .str[0]
            .str.strip()
            .unique()
        )
        if "CO_ENTIDADE" in df_cod.columns
        else []
    )

    # Nome da Escola
    df_nome = aplicar_filtros("nome")
    op_nome = (
        sorted(
            df_nome["NO_ENTIDADE"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )
        if "NO_ENTIDADE" in df_nome.columns
        else []
    )

    dic_dep = {
        k: v for k, v in MAP_DEPENDENCIA.items()
        if k in op_dep
    }

    dic_loc = {
        k: v for k, v in MAP_LOCALIZACAO.items()
        if k in op_loc
    }

    return (
        ["Todas"] + op_nre,
        ["Todas"] + op_mun,
        dic_dep,
        ["Todas"] + list(dic_loc.values()),
        ["Todos"] + op_cod,
        ["Todas"] + op_nome
    )

def sql_int_safe(coluna):
    return f"TRY_CAST(SPLIT_PART(TRIM(CAST({coluna} AS VARCHAR)), '.', 1) AS INTEGER)"

def extrair_chaves_por_rotulos(rotulos, dic):
    if not rotulos: return []
    inv_map = {v: k for k, v in dic.items()}
    return [inv_map.get(r) for r in rotulos if r in inv_map]

def calcular_soma_segura(df, coluna_principal, colunas_fallback=None):
    if df.empty: return 0
    col_upper = coluna_principal.upper()
    if col_upper in df.columns:
        serie = pd.to_numeric(df[col_upper].astype(str).str.replace(',', '.').str.extract(r'(\d+\.?\d*)')[0], errors='coerce').fillna(0)
        total = serie.sum()
        if total > 0: return total
    if colunas_fallback:
        total_fallback = 0
        encontrou_coluna = False
        for col in colunas_fallback:
            c_upper = col.upper()
            if c_upper in df.columns:
                s = pd.to_numeric(df[c_upper].astype(str).str.replace(',', '.').str.extract(r'(\d+\.?\d*)')[0], errors='coerce').fillna(0)
                soma_col = s.sum()
                if soma_col > 0:
                    total_fallback += soma_col
                    encontrou_coluna = True
        if encontrou_coluna and total_fallback > 0:
            return total_fallback
    return 0

def limpar_dataframe_para_excel(df):
    df_limpo = df.copy()
    for col in df_limpo.select_dtypes(include=['object', 'string']).columns:
        df_limpo[col] = df_limpo[col].fillna('').astype(str)
    return df_limpo

def converter_df_para_excel(df):
    df_tratado = limpar_dataframe_para_excel(df)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_tratado.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

# =============================================================================
# CAMINHOS E DOWNLOAD AUTOMÁTICO (Local vs Nuvem)
# =============================================================================

URL_ESCOLAS = "https://github.com/leandrojjsiqueira/painel-censo-escolar/releases/download/v1.0.0/v1_super_tabela_escolas.parquet"
URL_TECNICOS = "https://github.com/leandrojjsiqueira/painel-censo-escolar/releases/download/v1.0.0/v2_super_tabela_cursos_tecnicos.parquet"

if os.path.exists(r"C:\Ferramenta_Censo\v1_super_tabela_escolas.parquet"):
    # Caminhos no seu Computador (Local)
    CAMINHO_ESCOLAS_PARQUET = r"C:\Ferramenta_Censo\v1_super_tabela_escolas.parquet"
    CAMINHO_TECNICOS = r"M:\DPGE\04 - DPR\CIGD\0-2026\5 - ESTUDOS\45 - Microdados Censo Escolar 2007 a 2025\v2_super_tabela_cursos_tecnicos.csv"
else:
    # Caminhos na Nuvem (Streamlit Cloud)
    CAMINHO_ESCOLAS_PARQUET = "v1_super_tabela_escolas.parquet"
    CAMINHO_TECNICOS = "v2_super_tabela_cursos_tecnicos.parquet"

    # Função que descarrega automaticamente os ficheiros se não existirem no servidor
    @st.cache_resource
    def garantir_ficheiros_nuvem():
        if not os.path.exists(CAMINHO_ESCOLAS_PARQUET):
            with st.spinner("📥 A descarregar a Super Tabela de Escolas para a nuvem..."):
                urllib.request.urlretrieve(URL_ESCOLAS, CAMINHO_ESCOLAS_PARQUET)
                
        if not os.path.exists(CAMINHO_TECNICOS):
            with st.spinner("📥 A descarregar a Tabela de Cursos Técnicos para a nuvem..."):
                urllib.request.urlretrieve(URL_TECNICOS, CAMINHO_TECNICOS)

    garantir_ficheiros_nuvem()

@st.cache_data(show_spinner="A carregar a Super Tabela de Escolas...")
def carregar_tabela_escolas(caminho_parquet, data_modificacao):
    df = pd.read_parquet(caminho_parquet, engine="pyarrow")
    df.columns = df.columns.str.strip().str.upper()
    return df

@st.cache_data(show_spinner="A carregar a Tabela de Cursos Técnicos...")
def carregar_tabela_tecnicos(caminho, data_modificacao):
    con = duckdb.connect()
    try:
        if caminho.endswith('.parquet'):
            df = con.execute(f"SELECT * FROM read_parquet('{caminho}')").df()
        else:
            df = con.execute(f"SELECT * FROM read_csv_auto('{caminho}', delim=';', encoding='latin-1', all_varchar=true, ignore_errors=true)").df()
        df.columns = df.columns.str.strip().str.upper()
    finally:
        con.close()
    return df

@st.cache_data(show_spinner=False)
def consultar_escolas_filtradas_parquet(caminho_parquet, where_clause):
    con = duckdb.connect()
    try:
        sql = f"SELECT * FROM read_parquet('{caminho_parquet}')"
        if where_clause:
            sql += f" WHERE {where_clause}"
        return con.execute(sql).df()
    finally:
        con.close()

if not os.path.exists(CAMINHO_ESCOLAS_PARQUET) or not os.path.exists(CAMINHO_TECNICOS):
    st.error(f"ERRO: Ficheiro não encontrado. Escolas: {CAMINHO_ESCOLAS_PARQUET} | Técnicos: {CAMINHO_TECNICOS}")
    st.stop()

DATA_MOD_ESCOLAS = os.path.getmtime(CAMINHO_ESCOLAS_PARQUET)
DATA_MOD_TECNICOS = os.path.getmtime(CAMINHO_TECNICOS)

try:
    df_escolas_raw = carregar_tabela_escolas(CAMINHO_ESCOLAS_PARQUET, DATA_MOD_ESCOLAS)
    df_tecnicos_raw = carregar_tabela_tecnicos(CAMINHO_TECNICOS, DATA_MOD_TECNICOS)
except Exception as e:
    st.error("Erro ao carregar os dados:")
    st.exception(e)
    st.stop()

# =============================================================================
# TÍTULO E ABAS GLOBAIS
# =============================================================================

st.title("🏫 Sistema de Consulta - Microdados do Censo Escolar")
st.markdown("---")

aba_escolas, aba_tecnicos, aba_obs = st.tabs([
    "🏛️ Super Tabela Escolas",
    "🎓 Cursos Técnicos",
    "⚠️ Observações e Limitações"
])

# =============================================================================
# ABA 1 - SUPER TABELA ESCOLAS
# =============================================================================

with aba_escolas:
    with st.expander("📶 **Painel de Filtros - Escolas**", expanded=True):
        if st.button("🧹 Limpar Todos os Filtros", key="btn_limpar_a1", width="content"):
            for chave in [
                "ano_esc_a1", "nre_esc_a1", "mun_esc_sel_a1", "dep_esc_a1", "loc_esc_a1",
                "nre_t_v1", "mun_t_v1", "dep_t_v1", "loc_t_v1", "cod_t_busca_v1", "nome_t_busca_v1", "sel_etapa_t1", "sel_sexo_t1", "sel_raca_t1", "sel_idade_t1", "sel_turno_t1",
                "nre_g1", "mun_g1", "dep_g1", "loc_g1", "cod_esc_busca_g1", "nome_esc_busca_g1", "sel_etapa_a2", "sel_sexo_a2", "sel_raca_a2", "sel_idade_a2", "sel_turno_a2",
                "ms_esc_confirmado"
            ]:
                st.session_state.pop(chave, None)
                for k in list(st.session_state.keys()):
                    if k.startswith(f"cb_{chave}"):
                        st.session_state.pop(k, None)
            st.rerun()

        default_ano_a1 = ["2025"]
        anos_estado_key_a1 = "ano_esc_a1__estado"
        if anos_estado_key_a1 not in st.session_state:
            st.session_state[anos_estado_key_a1] = default_ano_a1
        ano_esc_val_temp = st.session_state.get(anos_estado_key_a1, default_ano_a1)

        if "NU_ANO_CENSO" in df_escolas_raw.columns and ano_esc_val_temp:
            df_esc_ano = df_escolas_raw[df_escolas_raw["NU_ANO_CENSO"].astype(str).str.split('.').str[0].str.strip().isin(ano_esc_val_temp)]
        else:
            df_esc_ano = df_escolas_raw

        cur_nre_p1 = st.session_state.get("nre_esc_a1", "Todas")
        cur_mun_p1 = st.session_state.get("mun_esc_sel_a1", "Todas")
        cur_dep_p1 = st.session_state.get("dep_esc_a1", [])
        cur_loc_p1 = st.session_state.get("loc_esc_a1", "Todas")

        if "last_nre_esc_a1" not in st.session_state:
            st.session_state["last_nre_esc_a1"] = cur_nre_p1
        elif st.session_state["last_nre_esc_a1"] != cur_nre_p1:
            st.session_state["mun_esc_sel_a1"] = "Todas"
            st.session_state["last_nre_esc_a1"] = cur_nre_p1
            st.rerun()

        op_nre_p1, op_mun_p1, op_dep_p1, op_loc_p1, _, _ = get_opcoes_cruzadas_completas(
            df_esc_ano, nre_sel=cur_nre_p1, mun_sel=cur_mun_p1, dep_sel=cur_dep_p1, loc_sel=cur_loc_p1
        )

        st.markdown("##### Localização e Identificação da Escola")
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.5, 2])
        with c1:
            nre_esc = criar_filtro_selectbox("Núcleo Regional", op_nre_p1, "nre_esc_a1", "Todas")
        with c2:
            mun_esc = criar_filtro_selectbox("Município", op_mun_p1, "mun_esc_sel_a1", "Todas")
        with c3:
            loc_esc = criar_filtro_selectbox("Localização", op_loc_p1, "loc_esc_a1", "Todas")
        with c4:
            ano_esc = criar_filtro_checkboxes("Ano(s) do Censo", ANOS_ESCOLAS_DIC, "ano_esc_a1", valor_padrao=["2025"])
        with c5:
            dep_esc = criar_filtro_checkboxes("Rede", op_dep_p1, "dep_esc_a1")

    where_esc = []
    if ano_esc:
        where_esc.append(f"{sql_int_safe('NU_ANO_CENSO')} IN ({', '.join(ano_esc)})")
    if nre_esc and nre_esc not in ["Todas", "Todos"] and "NO_NRE" in df_escolas_raw.columns:
        where_esc.append(f"TRIM(CAST(NO_NRE AS VARCHAR)) = '{nre_esc.replace('\'', '\'\'')}'")
    if mun_esc and mun_esc != "Todas":
        where_esc.append(f"TRIM(CAST(NO_MUNICIPIO AS VARCHAR)) = '{mun_esc.replace('\'', '\'\'')}'")
    if dep_esc:
        deps = [int(d.split(' - ')[0]) for d in dep_esc]
        where_esc.append(f"{sql_int_safe('TP_DEPENDENCIA')} IN ({', '.join(map(str, deps))})")
    if loc_esc and loc_esc not in ["Todas", "Todos"]:
        loc_id = int(loc_esc.split(' - ')[0])
        where_esc.append(f"{sql_int_safe('TP_LOCALIZACAO')} = {loc_id}")

    where_clause_escolas = " AND ".join(where_esc)

    try:
        df_escolas = consultar_escolas_filtradas_parquet(
            CAMINHO_ESCOLAS_PARQUET,
            where_clause_escolas
        )

        rotulo_ano = formatar_anos(ano_esc)
        qtd_escolas_unicas = df_escolas["CO_ENTIDADE"].nunique() if "CO_ENTIDADE" in df_escolas.columns else len(df_escolas)

        m1, m2 = st.columns(2)
        m1.metric("Escolas Encontradas", fmt_num(qtd_escolas_unicas))
        m2.metric("Ano(s) do Censo", rotulo_ano)

        with st.expander("🔎 **Seleção de Visualização Instantânea das Tabelas**", expanded=False):
            @st.fragment
            def mostrar_tabelas_por_ano_fragmento():
                st.markdown("##### Localização e Identificação da Escola")
                
                cur_nre_t1 = st.session_state.get("nre_t_v1", "Todas")
                cur_mun_t1 = st.session_state.get("mun_t_v1", "Todas")
                cur_dep_t1 = st.session_state.get("dep_t_v1", [])
                cur_loc_t1 = st.session_state.get("loc_t_v1", "Todas")
                cur_cod_t1 = st.session_state.get("cod_t_busca_v1", "Todos")
                cur_nome_t1 = st.session_state.get("nome_t_busca_v1", "Todas")

                op_nre_t1, op_mun_t1, op_dep_t1, op_loc_t1, op_cod_t1, op_nome_t1 = get_opcoes_cruzadas_completas(
                    df_escolas, nre_sel=cur_nre_t1, mun_sel=cur_mun_t1, dep_sel=cur_dep_t1, loc_sel=cur_loc_t1, cod_sel=cur_cod_t1, nome_sel=cur_nome_t1
                )

                t_fc1, t_fc2, t_fc3, t_fc4, t_fc5, t_fc6 = st.columns(6)
                with t_fc1: 
                    nre_t_sel = criar_filtro_selectbox("Núcleo Regional", op_nre_t1, "nre_t_v1", "Todas")
                with t_fc2: 
                    mun_t_sel = criar_filtro_selectbox("Município", op_mun_t1, "mun_t_v1", "Todas")
                with t_fc3: 
                    loc_t_sel = criar_filtro_selectbox("Localização", op_loc_t1, "loc_t_v1", "Todas")
                with t_fc4: 
                    cod_t_sel = criar_filtro_selectbox("Código INEP", op_cod_t1, "cod_t_busca_v1", "Todos")
                with t_fc5: 
                    nome_t_sel = criar_filtro_selectbox("Nome da Escola", op_nome_t1, "nome_t_busca_v1", "Todas")
                with t_fc6: 
                    dep_t_sel = criar_filtro_checkboxes("Rede", op_dep_t1, "dep_t_v1")

                if len(ano_esc) > 1:
                    opcoes_anos_totais = list(ano_esc)
                    if (
                        "ano_totais_visualizacao_a1" not in st.session_state
                        or st.session_state["ano_totais_visualizacao_a1"] not in opcoes_anos_totais
                    ):
                        st.session_state["ano_totais_visualizacao_a1"] = opcoes_anos_totais[0]

                    ano_totais_visualizacao = st.selectbox(
                        "Visualizar Ano:",
                        options=opcoes_anos_totais,
                        key="ano_totais_visualizacao_a1"
                    )
                else:
                    ano_totais_visualizacao = ano_esc[0] if ano_esc else None

                st.markdown("---")
                st.markdown("##### Selecione as métricas que deseja exibir nas tabelas abaixo:")
                
                t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns(5)
                with t_col1: sel_etapa_t = criar_filtro_checkboxes("Etapa / Modalidade", OPCOES_ETAPAS, "sel_etapa_t1")
                with t_col2: sel_sexo_t = criar_filtro_checkboxes("Sexo", OPCOES_SEXO, "sel_sexo_t1")
                with t_col3: sel_raca_t = criar_filtro_checkboxes("Raça / Cor", OPCOES_RACA, "sel_raca_t1")
                with t_col4: sel_idade_t = criar_filtro_checkboxes("Faixa Etária", OPCOES_IDADE, "sel_idade_t1")
                with t_col5: sel_turno_t = criar_filtro_checkboxes("Turno / Integral", OPCOES_TURNO, "sel_turno_t1")

                grupos_metricas_a1 = {}
                if sel_etapa_t: grupos_metricas_a1["Etapa / Modalidade"] = (sel_etapa_t, OPCOES_ETAPAS)
                if sel_sexo_t: grupos_metricas_a1["Sexo"] = (sel_sexo_t, OPCOES_SEXO)
                if sel_raca_t: grupos_metricas_a1["Raça / Cor"] = (sel_raca_t, OPCOES_RACA)
                if sel_idade_t: grupos_metricas_a1["Faixa Etária"] = (sel_idade_t, OPCOES_IDADE)
                if sel_turno_t: grupos_metricas_a1["Turno / Integral"] = (sel_turno_t, OPCOES_TURNO)

                if grupos_metricas_a1:
                    df_vis_dinamica = df_escolas.copy()
                    if nre_t_sel and nre_t_sel not in ["Todas", "Todos"] and "NO_NRE" in df_vis_dinamica.columns:
                        df_vis_dinamica = df_vis_dinamica[df_vis_dinamica["NO_NRE"].astype(str).str.strip() == nre_t_sel]
                    if mun_t_sel and mun_t_sel not in ["Todas", "Todos"]:
                        df_vis_dinamica = df_vis_dinamica[df_vis_dinamica["NO_MUNICIPIO"].astype(str).str.strip() == mun_t_sel]
                    if loc_t_sel and loc_t_sel not in ["Todas", "Todos"]:
                        loc_v_id = str(loc_t_sel).split(' - ')[0].strip()
                        df_vis_dinamica = df_vis_dinamica[df_vis_dinamica["TP_LOCALIZACAO"].astype(str).str.split('.').str[0].str.strip() == loc_v_id]
                    if dep_t_sel:
                        deps_v_ids = [str(d.split(' - ')[0]) for d in dep_t_sel]
                        df_vis_dinamica = df_vis_dinamica[df_vis_dinamica["TP_DEPENDENCIA"].astype(str).str.split('.').str[0].str.strip().isin(deps_v_ids)]
                    if cod_t_sel and cod_t_sel != "Todos":
                        cod_limpo_t1 = str(cod_t_sel).split('.')[0].strip()
                        df_vis_dinamica = df_vis_dinamica[df_vis_dinamica["CO_ENTIDADE"].astype(str).str.split('.').str[0].str.strip() == cod_limpo_t1]
                    if nome_t_sel and nome_t_sel not in ["Todas", "Todos"]:
                        df_vis_dinamica = df_vis_dinamica[df_vis_dinamica["NO_ENTIDADE"].astype(str).str.strip() == nome_t_sel]

                    anos_v_serie = df_vis_dinamica["NU_ANO_CENSO"].astype(str).str.split(".").str[0].str.strip() if not df_vis_dinamica.empty else pd.Series()
                    df_ano_calculo = df_vis_dinamica[anos_v_serie == str(ano_totais_visualizacao)] if ano_totais_visualizacao else df_vis_dinamica

                    dados_ano = {}
                    for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_a1.items():
                        if not selecionados_grupo:
                            continue
                        linhas_totais = []
                        total_matriculas = 0
                        total_turmas = 0
                        inv_map = {v: k for k, v in opcoes_grupo.items()}

                        for rotulo in selecionados_grupo:
                            coluna_mat = inv_map.get(rotulo)
                            if not coluna_mat:
                                continue
                            coluna_tur = MAP_MAT_PARA_TUR.get(coluna_mat)
                            valor_mat = calcular_soma_segura(df_ano_calculo, coluna_mat)
                            valor_tur = calcular_soma_segura(df_ano_calculo, coluna_tur) if coluna_tur else 0

                            total_matriculas += valor_mat
                            total_turmas += valor_tur

                            linhas_totais.append({
                                "Seleção": rotulo,
                                "Matrículas": fmt_num(valor_mat),
                                "Turmas": "-" if valor_tur == 0 else fmt_num(valor_tur)
                            })

                        if linhas_totais:
                            linhas_totais.append({
                                "Seleção": "TOTAL DO GRUPO",
                                "Matrículas": fmt_num(total_matriculas),
                                "Turmas": "-" if total_turmas == 0 else fmt_num(total_turmas)
                            })

                        dados_ano[titulo_grupo] = linhas_totais

                    chaves_ativas_grupos = list(grupos_metricas_a1.keys())
                    for inicio in range(0, len(chaves_ativas_grupos), 2):
                        grupos_linha = chaves_ativas_grupos[inicio:inicio + 2]
                        colunas_totais = st.columns(2)

                        for posicao, titulo_grupo in enumerate(grupos_linha):
                            with colunas_totais[posicao]:
                                linhas_grupo = dados_ano.get(titulo_grupo, [])
                                if linhas_grupo:
                                    linhas_com_ano = []
                                    for linha in linhas_grupo:
                                        linhas_com_ano.append({
                                            "Ano": str(ano_totais_visualizacao),
                                            "Seleção": linha["Seleção"],
                                            "Matrículas": linha["Matrículas"],
                                            "Turmas": linha["Turmas"]
                                        })

                                    df_resumo_grupo = pd.DataFrame(linhas_com_ano)

                                    with st.container(border=True):
                                        st.markdown(f"#### {titulo_grupo}")
                                        st.dataframe(
                                            df_resumo_grupo,
                                            use_container_width=True,
                                            hide_index=True,
                                            height=min(120 + len(df_resumo_grupo) * 38, 430)
                                        )
                                        
                                        excel_bytes_grupo = converter_df_para_excel(df_resumo_grupo)
                                        safe_file_name = titulo_grupo.lower().replace(" / ", "_").replace(" ", "_")
                                        st.download_button(
                                            f"📥 Baixar {titulo_grupo} Excel (.xlsx)",
                                            data=excel_bytes_grupo,
                                            file_name=f"tabela_{safe_file_name}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key=f"dl_exp_{safe_file_name}"
                                        )
                else:
                    st.info("ℹ️ Selecione ao menos uma opção acima em um dos grupos para visualizar as tabelas de totais.")

            mostrar_tabelas_por_ano_fragmento()

        with st.expander("🔎 **Seleção de Visualização Instantânea dos Gráficos**", expanded=False):
            @st.fragment
            def mostrar_graficos_escolas_fragmento():
                st.markdown("### 📈 Evolução Histórica (Escolas)")
                
                st.markdown("##### Período e Filtros Históricos")
                anos_disponiveis = sorted([int(a) for a in ano_esc]) if ano_esc else list(range(2007, 2026))
                min_ano_sld = min(anos_disponiveis)
                max_ano_sld = max(anos_disponiveis)

                if min_ano_sld == max_ano_sld:
                    anos_selecionados = (min_ano_sld, max_ano_sld)
                    st.info(f"ℹ️ Período fixado em **{min_ano_sld}** conforme selecionado no filtro principal.")
                else:
                    anos_selecionados = st.slider(
                        "Selecione o Período Histórico",
                        min_value=min_ano_sld,
                        max_value=max_ano_sld,
                        value=(min_ano_sld, max_ano_sld),
                        key="slider_a2"
                    )

                cur_nre_g1 = st.session_state.get("nre_g1", "Todas")
                cur_mun_g1 = st.session_state.get("mun_g1", "Todas")
                cur_dep_g1 = st.session_state.get("dep_g1", [])
                cur_loc_g1 = st.session_state.get("loc_g1", "Todas")
                cur_cod_g1 = st.session_state.get("cod_esc_sel_g1", "Todos")
                cur_nome_g1 = st.session_state.get("nome_esc_sel_g1", "Todas")

                op_nre_g1, op_mun_g1, op_dep_g1, op_loc_g1, op_cod_g1, op_nome_g1 = get_opcoes_cruzadas_completas(
                    df_escolas, nre_sel=cur_nre_g1, mun_sel=cur_mun_g1, dep_sel=cur_dep_g1, loc_sel=cur_loc_g1, cod_sel=cur_cod_g1, nome_sel=cur_nome_g1
                )

                g_c1, g_c2, g_c3, g_c4, g_c5, g_c6 = st.columns(6)
                with g_c1: 
                    nre_esc_graf = criar_filtro_selectbox("Núcleo Regional", op_nre_g1, "nre_g1", "Todas")
                with g_c2: 
                    mun_esc_graf = criar_filtro_selectbox("Município", op_mun_g1, "mun_g1", "Todas")
                with g_c3: 
                    loc_esc_graf = criar_filtro_selectbox("Localização", op_loc_g1, "loc_g1", "Todas")
                with g_c4: 
                    cod_esc_sel_g = criar_filtro_selectbox("Código INEP", op_cod_g1, "cod_esc_sel_g1", "Todos")
                with g_c5: 
                    nome_esc_sel_g = criar_filtro_selectbox("Nome da Escola", op_nome_g1, "nome_esc_sel_g1", "Todas")
                with g_c6: 
                    dep_esc_graf = criar_filtro_checkboxes("Rede", op_dep_g1, "dep_g1")

                st.markdown("##### Métrica Específica para o Gráfico")
                
                gf1, gf2, gf3, gf4, gf5 = st.columns(5)
                with gf1: sel_etapa_graf = criar_filtro_checkboxes("Etapa / Modalidade", OPCOES_ETAPAS, "sel_etapa_a2")
                with gf2: sel_sexo_graf = criar_filtro_checkboxes("Sexo", OPCOES_SEXO, "sel_sexo_a2")
                with gf3: sel_raca_graf = criar_filtro_checkboxes("Raça / Cor", OPCOES_RACA, "sel_raca_a2")
                with gf4: sel_idade_graf = criar_filtro_checkboxes("Faixa Etária", OPCOES_IDADE, "sel_idade_a2")
                with gf5: sel_turno_graf = criar_filtro_checkboxes("Turno / Integral", OPCOES_TURNO, "sel_turno_a2")

                grupos_metricas_a2 = {}
                if sel_etapa_graf: grupos_metricas_a2["Etapa / Modalidade"] = (sel_etapa_graf, OPCOES_ETAPAS)
                if sel_sexo_graf: grupos_metricas_a2["Sexo"] = (sel_sexo_graf, OPCOES_SEXO)
                if sel_raca_graf: grupos_metricas_a2["Raça / Cor"] = (sel_raca_graf, OPCOES_RACA)
                if sel_idade_graf: grupos_metricas_a2["Faixa Etária"] = (sel_idade_graf, OPCOES_IDADE)
                if sel_turno_graf: grupos_metricas_a2["Turno / Integral"] = (sel_turno_graf, OPCOES_TURNO)

                if grupos_metricas_a2:
                    df_graf_base = df_escolas.copy()
                    if not df_graf_base.empty:
                        df_graf_base['ANO_INT'] = df_graf_base['NU_ANO_CENSO'].astype(str).str.split('.').str[0].astype(int)
                        df_graf_base = df_graf_base[
                            (df_graf_base['ANO_INT'] >= anos_selecionados[0]) & 
                            (df_graf_base['ANO_INT'] <= anos_selecionados[1])
                        ]

                        if nre_esc_graf and nre_esc_graf not in ["Todas", "Todos"] and "NO_NRE" in df_graf_base.columns:
                            df_graf_base = df_graf_base[df_graf_base['NO_NRE'].astype(str).str.strip() == nre_esc_graf]
                        if mun_esc_graf and mun_esc_graf not in ["Todas", "Todos"]:
                            df_graf_base = df_graf_base[df_graf_base['NO_MUNICIPIO'].astype(str).str.strip() == mun_esc_graf]
                        if loc_esc_graf and loc_esc_graf not in ["Todas", "Todos"]:
                            loc_g_id = str(loc_esc_graf).split(' - ')[0].strip()
                            df_graf_base = df_graf_base[df_graf_base['TP_LOCALIZACAO'].astype(str).str.split('.').str[0].str.strip() == loc_g_id]
                        if dep_esc_graf:
                            deps_g_ids = [str(d.split(' - ')[0]) for d in dep_esc_graf]
                            df_graf_base = df_graf_base[df_graf_base['TP_DEPENDENCIA'].astype(str).str.split('.').str[0].str.strip().isin(deps_g_ids)]
                        if cod_esc_sel_g and cod_esc_sel_g != "Todos":
                            cod_limpo_g1 = str(cod_esc_sel_g).split('.')[0].strip()
                            df_graf_base = df_graf_base[df_graf_base['CO_ENTIDADE'].astype(str).str.split('.').str[0].str.strip() == cod_limpo_g1]
                        if nome_esc_sel_g and nome_esc_sel_g not in ["Todas", "Todos"]:
                            df_graf_base = df_graf_base[df_graf_base['NO_ENTIDADE'].astype(str).str.strip() == nome_esc_sel_g]

                    for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_a2.items():
                        colunas_grupo = extrair_chaves_por_rotulos(selecionados_grupo, opcoes_grupo)
                        if not colunas_grupo:
                            continue

                        colunas_turma_grupo = [MAP_MAT_PARA_TUR.get(c) for c in colunas_grupo if MAP_MAT_PARA_TUR.get(c)]
                        cols_necessarias = list(dict.fromkeys(["ANO_INT"] + colunas_grupo + colunas_turma_grupo))
                        cols_presentes = [c for c in cols_necessarias if c in df_graf_base.columns]

                        if df_graf_base.empty or not cols_presentes:
                            continue

                        df_sub_grupo = df_graf_base[cols_presentes]
                        registos_agrupados = []
                        for ano_idx, df_sub in df_sub_grupo.groupby('ANO_INT'):
                            registos_agrupados.append({
                                'ANO': ano_idx,
                                'Matrículas': sum(calcular_soma_segura(df_sub, c) for c in colunas_grupo if c in df_sub.columns),
                                'Turmas': sum(calcular_soma_segura(df_sub, c) for c in colunas_turma_grupo if c and c in df_sub.columns)
                            })

                        df_agrupado = pd.DataFrame(registos_agrupados)
                        if df_agrupado.empty:
                            continue

                        df_agrupado['Matrículas_Fmt'] = df_agrupado['Matrículas'].apply(lambda x: f"{int(x):,}".replace(",", "."))
                        df_agrupado['Turmas_Fmt'] = df_agrupado['Turmas'].apply(lambda x: f"{int(x):,}".replace(",", "."))

                        st.markdown(f"### {titulo_grupo}")
                        
                        subtitulo_dinamico = formatar_legenda_filtros(
                            anos_selecionados[0], 
                            anos_selecionados[1], 
                            mun_esc_graf, 
                            nre_esc_graf,
                            dep_esc_graf, 
                            loc_esc_graf, 
                            selecionados_grupo
                        )
                        st.caption(subtitulo_dinamico)

                        fig_mat = px.line(df_agrupado, x='ANO', y='Matrículas', markers=True, custom_data=['Matrículas_Fmt'])
                        fig_mat.update_traces(hovertemplate="<b>Ano:</b> %{x}<br><b>Matrículas:</b> %{customdata[0]}<extra></extra>")
                        fig_mat.update_layout(separators=',.', hovermode="closest", title="Matrículas", xaxis_title="Ano do Censo", yaxis_title="Total de Matrículas")
                        fig_mat.update_xaxes(type='category', fixedrange=True)
                        min_mat, max_mat = df_agrupado['Matrículas'].min(), df_agrupado['Matrículas'].max()
                        fig_mat.update_yaxes(tickformat=',.0f', range=[min_mat * 0.95, max_mat * 1.05] if max_mat > 0 else None, fixedrange=True)

                        fig_tur = px.line(df_agrupado, x='ANO', y='Turmas', markers=True, custom_data=['Turmas_Fmt'])
                        fig_tur.update_traces(hovertemplate="<b>Ano:</b> %{x}<br><b>Turmas:</b> %{customdata[0]}<extra></extra>")
                        fig_tur.update_layout(separators=',.', hovermode="closest", title="Turmas", xaxis_title="Ano do Censo", yaxis_title="Total de Turmas")
                        fig_tur.update_xaxes(type='category', fixedrange=True)
                        min_tur, max_tur = df_agrupado['Turmas'].min(), df_agrupado['Turmas'].max()
                        fig_tur.update_yaxes(tickformat=',.0f', range=[min_tur * 0.95, max_tur * 1.05] if max_tur > 0 else None, fixedrange=True)

                        tem_turmas = df_agrupado['Turmas'].sum() > 0
                        safe_key_suffix = titulo_grupo.lower().replace(" / ", "_").replace(" ", "_")

                        if tem_turmas:
                            g1, g2 = st.columns(2)
                            with g1:
                                st.plotly_chart(fig_mat, use_container_width=True, config={'displayModeBar': False}, key=f"mat_{safe_key_suffix}")
                            with g2:
                                st.plotly_chart(fig_tur, use_container_width=True, config={'displayModeBar': False}, key=f"tur_{safe_key_suffix}")
                        else:
                            st.plotly_chart(fig_mat, use_container_width=True, config={'displayModeBar': False}, key=f"mat_{safe_key_suffix}")

                        st.markdown("---")
                else:
                    st.info("ℹ️ Selecione ao menos uma métrica acima para exibir os gráficos.")

            mostrar_graficos_escolas_fragmento()

        st.markdown("<br>", unsafe_allow_html=True)

        @st.fragment
        def fragmento_tabela_escolas():
            with st.expander("⚙️ **Personalizar Colunas Adicionais do Relatório**", expanded=False):
                st.caption("🔒 As colunas de identificação, localização, NRE, rede e código do município são fixadas automaticamente.")
                todas_cols_esc = list(df_escolas.columns) if not df_escolas.empty else []
                cols_obrigatorias_esc = [
                    'NU_ANO_CENSO', 'NO_REGIAO', 'SG_UF', 'CO_NRE', 'NO_NRE',
                    'CO_MUNICIPIO', 'NO_MUNICIPIO', 'CO_ENTIDADE', 'NO_ENTIDADE',
                    'TP_DEPENDENCIA', 'TP_LOCALIZACAO', 'QT_MAT_BAS', 'QT_TUR_BAS'
                ]
                cols_opcionais_disponiveis = [c for c in todas_cols_esc if c not in cols_obrigatorias_esc]

                with st.form("form_cols_esc"):
                    cols_extras_rascunho = st.multiselect(
                        "Marque colunas extras:", 
                        options=cols_opcionais_disponiveis, 
                        default=st.session_state.get("ms_esc_confirmado", [])
                    )
                    btn_inserir_esc = st.form_submit_button("✔️ Inserir Colunas")
                    if btn_inserir_esc:
                        st.session_state["ms_esc_confirmado"] = cols_extras_rascunho

            cols_extras_sel = st.session_state.get("ms_esc_confirmado", [])
            cols_finais_esc = list(dict.fromkeys(cols_obrigatorias_esc + cols_extras_sel))
            cols_finais_validas = [c for c in cols_finais_esc if c in df_escolas.columns]

            df_escolas_exibir = df_escolas[cols_finais_validas] if not df_escolas.empty and cols_finais_validas else df_escolas
            
            if not df_escolas_exibir.empty:
                excel_escolas_bytes = converter_df_para_excel(df_escolas_exibir)
                st.info(f"💡 A apresentar as primeiras 100 escolas. O botão de download exporta todos os {fmt_num(len(df_escolas_exibir))} registos.")
                st.dataframe(df_escolas_exibir.head(100), use_container_width=True, height=500)
                st.download_button(
                    "📥 Baixar Excel (.xlsx)", 
                    data=excel_escolas_bytes, 
                    file_name="censo_escolas.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Nenhum resultado encontrado.")

        fragmento_tabela_escolas()

    except Exception as e:
        st.error(f"Erro: {e}")

# =============================================================================
# ABA 2 - CURSOS TÉCNICOS
# =============================================================================

with aba_tecnicos:
    with st.expander("📶 **Painel de Filtros - Cursos Técnicos**", expanded=True):
        if st.button("🧹 Limpar Todos os Filtros", key="btn_limpar_a3", width="content"):
            for chave in ["ano_tec", "nre_tec", "mun_tec_sel_a3", "dep_tec", "loc_tec", "cod_tec_sel_a3", "nome_tec_sel_a3", "nre_t_v2", "mun_t_v2", "dep_t_v2", "loc_t_v2", "cod_t_busca_v2", "nome_t_busca_v2", "sel_qtd_tec", "sel_mat_tec", "sel_area_inst", "sel_nome_curso_inst", "nre_g2", "mun_g2", "dep_g2", "loc_g2", "cod_tec_busca_g2", "nome_tec_busca_g2", "sel_qtd_tec_graf", "sel_mat_tec_graf", "sel_area_graf", "sel_nome_curso_graf", "ms_tec_confirmado"]:
                st.session_state.pop(chave, None)
                for k in list(st.session_state.keys()):
                    if k.startswith(f"cb_{chave}"):
                        st.session_state.pop(k, None)
            st.rerun()

        default_ano_tec = ["2025"]
        anos_tec_estado_key = "ano_tec__estado"
        if anos_tec_estado_key not in st.session_state:
            st.session_state[anos_tec_estado_key] = default_ano_tec
        ano_tec_val_temp = st.session_state.get(anos_tec_estado_key, default_ano_tec)

        if "NU_ANO_CENSO" in df_tecnicos_raw.columns and ano_tec_val_temp:
            df_tec_ano = df_tecnicos_raw[df_tecnicos_raw["NU_ANO_CENSO"].astype(str).str.split('.').str[0].str.strip().isin(ano_tec_val_temp)]
        else:
            df_tec_ano = df_tecnicos_raw

        cur_nre_p3 = st.session_state.get("nre_tec", "Todas")
        cur_mun_p3 = st.session_state.get("mun_tec_sel_a3", "Todas")
        cur_dep_p3 = st.session_state.get("dep_tec", [])
        cur_loc_p3 = st.session_state.get("loc_tec", "Todas")

        if "last_nre_tec" not in st.session_state:
            st.session_state["last_nre_tec"] = cur_nre_p3
        elif st.session_state["last_nre_tec"] != cur_nre_p3:
            st.session_state["mun_tec_sel_a3"] = "Todas"
            st.session_state["last_nre_tec"] = cur_nre_p3
            st.rerun()

        op_nre_p3, op_mun_p3, op_dep_p3, op_loc_p3, _, _ = get_opcoes_cruzadas_completas(
            df_tec_ano, nre_sel=cur_nre_p3, mun_sel=cur_mun_p3, dep_sel=cur_dep_p3, loc_sel=cur_loc_p3
        )

        st.markdown("##### Localização e Identificação da Escola")
        t1, t2, t3, t4, t5 = st.columns([2, 2, 2, 1.5, 2])
        with t1:
            nre_tec = criar_filtro_selectbox("Núcleo Regional", op_nre_p3, "nre_tec", "Todas")
        with t2:
            mun_tec = criar_filtro_selectbox("Município", op_mun_p3, "mun_tec_sel_a3", "Todas")
        with t3:
            loc_tec = criar_filtro_selectbox("Localização", op_loc_p3, "loc_tec", "Todas")
        with t4:
            ano_tec = criar_filtro_checkboxes("Ano(s) do Censo", ANOS_TECNICOS_DIC, "ano_tec", valor_padrao=["2025"])
        with t5:
            dep_tec = criar_filtro_checkboxes("Rede", op_dep_p3, "dep_tec")

    where_tec = []
    if ano_tec:
        where_tec.append(f"{sql_int_safe('NU_ANO_CENSO')} IN ({', '.join(ano_tec)})")
    if nre_tec and nre_tec not in ["Todas", "Todos"] and "NO_NRE" in df_tecnicos_raw.columns:
        where_tec.append(f"TRIM(CAST(NO_NRE AS VARCHAR)) = '{nre_tec.replace('\'', '\'\'')}'")
    if mun_tec and mun_tec not in ["Todas", "Todos"]:
        where_tec.append(f"TRIM(CAST(NO_MUNICIPIO AS VARCHAR)) = '{mun_tec.replace('\'', '\'\'')}'")
    if dep_tec:
        deps_t = [int(d.split(' - ')[0]) for d in dep_tec]
        where_tec.append(f"{sql_int_safe('TP_DEPENDENCIA')} IN ({', '.join(map(str, deps_t))})")
    if loc_tec and loc_tec not in ["Todas", "Todos"]:
        loc_id_t = int(loc_tec.split(' - ')[0])
        where_tec.append(f"{sql_int_safe('TP_LOCALIZACAO')} = {loc_id_t}")

    sql_tecnicos = f"SELECT * FROM df_tecnicos_raw" + (" WHERE " + " AND ".join(where_tec) if where_tec else "")

    try:
        con = duckdb.connect()
        df_tecnicos = con.execute(sql_tecnicos).df()
        con.close()

        qtd_escolas_tec = df_tecnicos["CO_ENTIDADE"].nunique() if "CO_ENTIDADE" in df_tecnicos.columns else 0
        qtd_cursos_distintos = df_tecnicos["NO_CURSO_EDUC_PROFISSIONAL"].nunique() if "NO_CURSO_EDUC_PROFISSIONAL" in df_tecnicos.columns else 0
        rotulo_ano_tec = formatar_anos(ano_tec)

        k1, k2, k3 = st.columns(3)
        k1.metric("Escolas Retornadas", fmt_num(qtd_escolas_tec))
        k2.metric("Cursos Distintos Retornados", fmt_num(qtd_cursos_distintos))
        k3.metric("Ano(s) Selecionado(s)", rotulo_ano_tec)

        with st.expander("🔎 **Seleção de Visualização Instantânea das Tabelas**", expanded=False):
            @st.fragment
            def mostrar_tabelas_tecnicos_por_ano_fragmento():
                st.markdown("##### Localização e Identificação da Escola")
                
                cur_nre_tt = st.session_state.get("nre_t_v2", "Todas")
                cur_mun_tt = st.session_state.get("mun_t_v2", "Todas")
                cur_dep_tt = st.session_state.get("dep_t_v2", [])
                cur_loc_tt = st.session_state.get("loc_t_v2", "Todas")
                cur_cod_tt = st.session_state.get("cod_t_busca_v2", "Todos")
                cur_nome_tt = st.session_state.get("nome_t_busca_v2", "Todas")

                op_nre_tt, op_mun_tt, op_dep_tt, op_loc_tt, op_cod_tt, op_nome_tt = get_opcoes_cruzadas_completas(
                    df_tecnicos, nre_sel=cur_nre_tt, mun_sel=cur_mun_tt, dep_sel=cur_dep_tt, loc_sel=cur_loc_tt, cod_sel=cur_cod_tt, nome_sel=cur_nome_tt
                )

                t_tc1, t_tc2, t_tc3, t_tc4, t_tc5, t_tc6 = st.columns(6)
                with t_tc1: 
                    nre_t_sel_tec = criar_filtro_selectbox("Núcleo Regional", op_nre_tt, "nre_t_v2", "Todas")
                with t_tc2: 
                    mun_t_sel_tec = criar_filtro_selectbox("Município", op_mun_tt, "mun_t_v2", "Todas")
                with t_tc3: 
                    loc_t_sel_tec = criar_filtro_selectbox("Localização", op_loc_tt, "loc_t_v2", "Todas")
                with t_tc4: 
                    cod_t_sel_tec = criar_filtro_selectbox("Código INEP", op_cod_tt, "cod_t_busca_v2", "Todos")
                with t_tc5: 
                    nome_t_sel_tec = criar_filtro_selectbox("Nome da Escola", op_nome_tt, "nome_t_busca_v2", "Todas")
                with t_tc6: 
                    dep_t_sel_tec = criar_filtro_checkboxes("Rede", op_dep_tt, "dep_t_v2")

                if len(ano_tec) > 1:
                    opcoes_anos_tec_totais = list(ano_tec)
                    if (
                        "ano_totais_visualizacao_tec" not in st.session_state
                        or st.session_state["ano_totais_visualizacao_tec"] not in opcoes_anos_tec_totais
                    ):
                        st.session_state["ano_totais_visualizacao_tec"] = opcoes_anos_tec_totais[0]

                    ano_totais_tec_vis = st.selectbox(
                        "Visualizar Ano:",
                        options=opcoes_anos_tec_totais,
                        key="ano_totais_visualizacao_tec"
                    )
                else:
                    ano_totais_tec_vis = ano_tec[0] if ano_tec else None

                st.markdown("---")
                st.markdown("##### Descrição do Curso")
                d_col1, d_col2 = st.columns(2)
                
                op_areas_tec = ["Todas"] + sorted(df_tecnicos["NO_AREA_CURSO_PROFISSIONAL"].dropna().astype(str).str.strip().unique()) if "NO_AREA_CURSO_PROFISSIONAL" in df_tecnicos.columns else ["Todas"]
                op_nomes_cursos_tec = ["Todas"] + sorted(df_tecnicos["NO_CURSO_EDUC_PROFISSIONAL"].dropna().astype(str).str.strip().unique()) if "NO_CURSO_EDUC_PROFISSIONAL" in df_tecnicos.columns else ["Todas"]

                with d_col1: 
                    sel_area_inst = criar_filtro_selectbox("Área do Curso (NO_AREA_CURSO_PROFISSIONAL)", op_areas_tec, "sel_area_inst", "Todas")
                with d_col2: 
                    sel_nome_curso_inst = criar_filtro_selectbox("Nome do Curso (NO_CURSO_EDUC_PROFISSIONAL)", op_nomes_cursos_tec, "sel_nome_curso_inst", "Todas")

                st.markdown("---")
                st.markdown("##### Selecione as métricas que deseja exibir nas tabelas abaixo:")
                
                t_col1, t_col2 = st.columns(2)
                with t_col1: sel_qtd_tec = criar_filtro_checkboxes("Quantidade de Cursos", OPCOES_CURSOS_QTD, "sel_qtd_tec")
                with t_col2: sel_mat_tec = criar_filtro_checkboxes("Quantidade de Matrículas", OPCOES_CURSOS_MAT, "sel_mat_tec")

                tem_metricas_gerais = bool(sel_qtd_tec or sel_mat_tec)
                tem_dimensoes_especificas = bool(sel_area_inst != "Todas" or sel_nome_curso_inst != "Todas")

                if tem_metricas_gerais or tem_dimensoes_especificas:
                    df_vis_tec_dinamica = df_tecnicos.copy()
                    if nre_t_sel_tec and nre_t_sel_tec not in ["Todas", "Todos"] and "NO_NRE" in df_vis_tec_dinamica.columns:
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["NO_NRE"].astype(str).str.strip() == nre_t_sel_tec]
                    if mun_t_sel_tec and mun_t_sel_tec not in ["Todas", "Todos"]:
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["NO_MUNICIPIO"].astype(str).str.strip() == mun_t_sel_tec]
                    if loc_t_sel_tec and loc_t_sel_tec not in ["Todas", "Todos"]:
                        loc_vt_id = str(loc_t_sel_tec).split(' - ')[0].strip()
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["TP_LOCALIZACAO"].astype(str).str.split('.').str[0].str.strip() == loc_vt_id]
                    if dep_t_sel_tec:
                        deps_vt_ids = [str(d.split(' - ')[0]) for d in dep_t_sel_tec]
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["TP_DEPENDENCIA"].astype(str).str.split('.').str[0].str.strip().isin(deps_vt_ids)]
                    if cod_t_sel_tec and cod_t_sel_tec != "Todos":
                        cod_limpo_t2 = str(cod_t_sel_tec).split('.')[0].strip()
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["CO_ENTIDADE"].astype(str).str.split('.').str[0].str.strip() == cod_limpo_t2]
                    if nome_t_sel_tec and nome_t_sel_tec not in ["Todas", "Todos"]:
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["NO_ENTIDADE"].astype(str).str.strip() == nome_t_sel_tec]

                    if sel_area_inst != "Todas" and "NO_AREA_CURSO_PROFISSIONAL" in df_vis_tec_dinamica.columns:
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["NO_AREA_CURSO_PROFISSIONAL"].astype(str).str.strip() == sel_area_inst]
                    if sel_nome_curso_inst != "Todas" and "NO_CURSO_EDUC_PROFISSIONAL" in df_vis_tec_dinamica.columns:
                        df_vis_tec_dinamica = df_vis_tec_dinamica[df_vis_tec_dinamica["NO_CURSO_EDUC_PROFISSIONAL"].astype(str).str.strip() == sel_nome_curso_inst]

                    anos_vt_serie = df_vis_tec_dinamica["NU_ANO_CENSO"].astype(str).str.split(".").str[0].str.strip() if not df_vis_tec_dinamica.empty else pd.Series()
                    df_ano_calc_tec = df_vis_tec_dinamica[anos_vt_serie == str(ano_totais_tec_vis)] if ano_totais_tec_vis else df_vis_tec_dinamica

                    grupos_metricas_tec = {}
                    if sel_qtd_tec: grupos_metricas_tec["Quantidade de Cursos"] = (sel_qtd_tec, OPCOES_CURSOS_QTD)
                    if sel_mat_tec: grupos_metricas_tec["Quantidade de Matrículas"] = (sel_mat_tec, OPCOES_CURSOS_MAT)

                    if grupos_metricas_tec:
                        dados_ano_tec = {}
                        for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_tec.items():
                            linhas_totais = []
                            total_geral_grupo = 0
                            inv_map_tec = {v: k for k, v in opcoes_grupo.items()}

                            for rotulo in selecionados_grupo:
                                coluna_metrica = inv_map_tec.get(rotulo)
                                if not coluna_metrica:
                                    continue
                                
                                valor_metrica = calcular_soma_segura(df_ano_calc_tec, coluna_metrica)
                                total_geral_grupo += valor_metrica

                                linhas_totais.append({
                                    "Seleção": rotulo,
                                    "Total": fmt_num(valor_metrica)
                                })

                            if linhas_totais:
                                linhas_totais.append({
                                    "Seleção": "TOTAL DO GRUPO",
                                    "Total": fmt_num(total_geral_grupo)
                                })

                            dados_ano_tec[titulo_grupo] = linhas_totais

                        chaves_ativas_tec = list(grupos_metricas_tec.keys())
                        colunas_totais_tec = st.columns(len(chaves_ativas_tec))

                        for posicao, titulo_grupo in enumerate(chaves_ativas_tec):
                            with colunas_totais_tec[posicao]:
                                linhas_grupo_tec = dados_ano_tec.get(titulo_grupo, [])
                                if linhas_grupo_tec:
                                    linhas_com_ano_tec = [
                                        {
                                            "Ano": str(ano_totais_tec_vis),
                                            "Seleção": l["Seleção"],
                                            "Total": l["Total"]
                                        } for l in linhas_grupo_tec
                                    ]
                                    df_resumo_grupo_tec = pd.DataFrame(linhas_com_ano_tec)

                                    with st.container(border=True):
                                        st.markdown(f"#### {titulo_grupo}")
                                        st.dataframe(
                                            df_resumo_grupo_tec,
                                            use_container_width=True,
                                            hide_index=True,
                                            height=min(120 + len(df_resumo_grupo_tec) * 38, 430)
                                        )
                                        
                                        excel_bytes_g_tec = converter_df_para_excel(df_resumo_grupo_tec)
                                        safe_file_name_tec = titulo_grupo.lower().replace(" / ", "_").replace(" ", "_")
                                        st.download_button(
                                            f"📥 Baixar {titulo_grupo} Excel (.xlsx)",
                                            data=excel_bytes_g_tec,
                                            file_name=f"tabela_{safe_file_name_tec}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key=f"dl_exp_{safe_file_name_tec}"
                                        )

                    dimensoes_para_exibir = []
                    if sel_area_inst != "Todas":
                        dimensoes_para_exibir.append(("Área do Curso (NO_AREA_CURSO_PROFISSIONAL)", "NO_AREA_CURSO_PROFISSIONAL", [sel_area_inst]))
                    if sel_nome_curso_inst != "Todas":
                        dimensoes_para_exibir.append(("Nome do Curso (NO_CURSO_EDUC_PROFISSIONAL)", "NO_CURSO_EDUC_PROFISSIONAL", [sel_nome_curso_inst]))

                    if dimensoes_para_exibir:
                        st.markdown("---")
                        col_dim1, col_dim2 = st.columns(len(dimensoes_para_exibir))

                        for idx_dim, (titulo_dim, col_dim, selecionados_dim) in enumerate(dimensoes_para_exibir):
                            col_alvo = col_dim1 if idx_dim == 0 else col_dim2
                            with col_alvo:
                                linhas_dim = []
                                tot_mat_dim = 0
                                tot_cur_dim = 0

                                for item_sel in selecionados_dim:
                                    if col_dim in df_ano_calc_tec.columns:
                                        df_sub_item = df_ano_calc_tec[df_ano_calc_tec[col_dim].astype(str).str.strip() == item_sel]
                                    else:
                                        df_sub_item = pd.DataFrame()

                                    v_mat = calcular_soma_segura(df_sub_item, "QT_MAT_CURSO_TEC")
                                    v_cur = len(df_sub_item) if not df_sub_item.empty else 0

                                    tot_mat_dim += v_mat
                                    tot_cur_dim += v_cur

                                    linhas_dim.append({
                                        "Ano": str(ano_totais_tec_vis),
                                        "Seleção": item_sel,
                                        "Matrículas (QT_MAT_CURSO_TEC)": fmt_num(v_mat),
                                        "Quantidade de Cursos (QT_CURSO_TEC)": fmt_num(v_cur)
                                    })

                                if linhas_dim:
                                    linhas_dim.append({
                                        "Ano": str(ano_totais_tec_vis),
                                        "Seleção": "TOTAL DO GRUPO",
                                        "Matrículas (QT_MAT_CURSO_TEC)": fmt_num(tot_mat_dim),
                                        "Quantidade de Cursos (QT_CURSO_TEC)": fmt_num(tot_cur_dim)
                                    })

                                    df_resumo_dim = pd.DataFrame(linhas_dim)

                                    with st.container(border=True):
                                        st.markdown(f"#### {titulo_dim}")
                                        st.dataframe(
                                            df_resumo_dim,
                                            use_container_width=True,
                                            hide_index=True,
                                            height=min(120 + len(df_resumo_dim) * 38, 430)
                                        )

                                        excel_bytes_dim = converter_df_para_excel(df_resumo_dim)
                                        safe_file_dim = col_dim.lower()
                                        st.download_button(
                                            f"📥 Baixar Resumo Excel (.xlsx)",
                                            data=excel_bytes_dim,
                                            file_name=f"resumo_{safe_file_dim}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key=f"dl_exp_dim_{safe_file_dim}"
                                        )
                else:
                    st.info("ℹ️ Selecione ao menos uma opção acima em um dos grupos para visualizar as tabelas de totais.")

            mostrar_tabelas_tecnicos_por_ano_fragmento()

        with st.expander("🔎 **Seleção de Visualização Instantânea dos Gráficos**", expanded=False):
            @st.fragment
            def mostrar_graficos_tecnicos_fragmento():
                st.markdown("### 📈 Evolução Histórica (Cursos Técnicos)")
                st.markdown("##### Período e Filtros Históricos")
                anos_tec_disp = sorted([int(a) for a in ano_tec]) if ano_tec else list(range(2023, 2026))
                min_tec_sld = min(anos_tec_disp)
                max_tec_sld = max(anos_tec_disp)

                if min_tec_sld == max_tec_sld:
                    anos_tec_sel = (min_tec_sld, max_tec_sld)
                    st.info(f"ℹ️ Período fixado em **{min_tec_sld}** conforme selecionado no filtro principal.")
                else:
                    anos_tec_sel = st.slider(
                        "Selecione o Período Histórico",
                        min_value=min_tec_sld,
                        max_value=max_tec_sld,
                        value=(min_tec_sld, max_tec_sld),
                        key="slider_tec"
                    )

                cur_nre_g2 = st.session_state.get("nre_g2", "Todas")
                cur_mun_g2 = st.session_state.get("mun_g2", "Todas")
                cur_dep_g2 = st.session_state.get("dep_g2", [])
                cur_loc_g2 = st.session_state.get("loc_g2", "Todas")
                cur_cod_g2 = st.session_state.get("cod_tec_busca_g2", "Todos")
                cur_nome_g2 = st.session_state.get("nome_tec_busca_g2", "Todas")

                op_nre_g2, op_mun_g2, op_dep_g2, op_loc_g2, op_cod_g2, op_nome_g2 = get_opcoes_cruzadas_completas(
                    df_tecnicos, nre_sel=cur_nre_g2, mun_sel=cur_mun_g2, dep_sel=cur_dep_g2, loc_sel=cur_loc_g2, cod_sel=cur_cod_g2, nome_sel=cur_nome_g2
                )

                g_t1, g_t2, g_t3, g_t4, g_t5, g_t6 = st.columns(6)
                with g_t1: 
                    nre_tec_graf = criar_filtro_selectbox("Núcleo Regional", op_nre_g2, "nre_g2", "Todas")
                with g_t2: 
                    mun_tec_graf = criar_filtro_selectbox("Município", op_mun_g2, "mun_g2", "Todas")
                with g_t3: 
                    loc_tec_graf = criar_filtro_selectbox("Localização", op_loc_g2, "loc_g2", "Todas")
                with g_t4: 
                    cod_tec_sel_g = criar_filtro_selectbox("Código INEP", op_cod_g2, "cod_tec_busca_g2", "Todos")
                with g_t5: 
                    nome_tec_sel_g = criar_filtro_selectbox("Nome da Escola", op_nome_g2, "nome_tec_busca_g2", "Todas")
                with g_t6: 
                    dep_tec_graf = criar_filtro_checkboxes("Rede", op_dep_g2, "dep_g2")

                st.markdown("##### Descrição do Curso")
                gd1, gd2 = st.columns(2)
                
                op_areas_graf = ["Todas"] + sorted(df_tecnicos["NO_AREA_CURSO_PROFISSIONAL"].dropna().astype(str).str.strip().unique()) if "NO_AREA_CURSO_PROFISSIONAL" in df_tecnicos.columns else ["Todas"]
                op_nomes_graf = ["Todas"] + sorted(df_tecnicos["NO_CURSO_EDUC_PROFISSIONAL"].dropna().astype(str).str.strip().unique()) if "NO_CURSO_EDUC_PROFISSIONAL" in df_tecnicos.columns else ["Todas"]

                with gd1: 
                    sel_area_graf = criar_filtro_selectbox("Área do Curso (NO_AREA_CURSO_PROFISSIONAL)", op_areas_graf, "sel_area_graf", "Todas")
                with gd2: 
                    sel_nome_curso_graf = criar_filtro_selectbox("Nome do Curso (NO_CURSO_EDUC_PROFISSIONAL)", op_nomes_graf, "sel_nome_curso_graf", "Todas")

                st.markdown("##### Métrica Específica para o Gráfico")
                
                gt1, gt2 = st.columns(2)
                with gt1: sel_qtd_tec_graf = criar_filtro_checkboxes("Quantidade de Cursos", OPCOES_CURSOS_QTD, "sel_qtd_tec_graf")
                with gt2: sel_mat_tec_graf = criar_filtro_checkboxes("Quantidade de Matrículas", OPCOES_CURSOS_MAT, "sel_mat_tec_graf")

                grupos_metricas_tec_graf = {}
                if sel_qtd_tec_graf: grupos_metricas_tec_graf["Quantidade de Cursos"] = (sel_qtd_tec_graf, OPCOES_CURSOS_QTD)
                if sel_mat_tec_graf: grupos_metricas_tec_graf["Quantidade de Matrículas"] = (sel_mat_tec_graf, OPCOES_CURSOS_MAT)

                if grupos_metricas_tec_graf:
                    df_graf_tec_base = df_tecnicos.copy()
                    if not df_graf_tec_base.empty:
                        df_graf_tec_base['ANO_INT'] = df_graf_tec_base['NU_ANO_CENSO'].astype(str).str.split('.').str[0].astype(int)
                        df_graf_tec_base = df_graf_tec_base[
                            (df_graf_tec_base['ANO_INT'] >= anos_tec_sel[0]) & 
                            (df_graf_tec_base['ANO_INT'] <= anos_tec_sel[1])
                        ]

                        if nre_tec_graf and nre_tec_graf not in ["Todas", "Todos"] and "NO_NRE" in df_graf_tec_base.columns:
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['NO_NRE'].astype(str).str.strip() == nre_tec_graf]
                        if mun_tec_graf and mun_tec_graf not in ["Todas", "Todos"]:
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['NO_MUNICIPIO'].astype(str).str.strip() == mun_tec_graf]
                        if loc_tec_graf and loc_tec_graf not in ["Todas", "Todos"]:
                            loc_tg_id = str(loc_tec_graf).split(' - ')[0].strip()
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['TP_LOCALIZACAO'].astype(str).str.split('.').str[0].str.strip() == loc_tg_id]
                        if dep_tec_graf:
                            deps_tg_ids = [str(d.split(' - ')[0]) for d in dep_tec_graf]
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['TP_DEPENDENCIA'].astype(str).str.split('.').str[0].str.strip().isin(deps_tg_ids)]
                        if cod_tec_sel_g and cod_tec_sel_g != "Todos":
                            cod_limpo_g2 = str(cod_tec_sel_g).split('.')[0].strip()
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['CO_ENTIDADE'].astype(str).str.split('.').str[0].str.strip() == cod_limpo_g2]
                        if nome_tec_sel_g and nome_tec_sel_g not in ["Todas", "Todos"]:
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['NO_ENTIDADE'].astype(str).str.strip() == nome_tec_sel_g]

                        if sel_area_graf != "Todas" and "NO_AREA_CURSO_PROFISSIONAL" in df_graf_tec_base.columns:
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['NO_AREA_CURSO_PROFISSIONAL'].astype(str).str.strip() == sel_area_graf]
                        if sel_nome_curso_graf != "Todas" and "NO_CURSO_EDUC_PROFISSIONAL" in df_graf_tec_base.columns:
                            df_graf_tec_base = df_graf_tec_base[df_graf_tec_base['NO_CURSO_EDUC_PROFISSIONAL'].astype(str).str.strip() == sel_nome_curso_graf]

                    for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_tec_graf.items():
                        colunas_grupo = extrair_chaves_por_rotulos(selecionados_grupo, opcoes_grupo)
                        if not colunas_grupo:
                            continue

                        cols_necessarias = list(dict.fromkeys(["ANO_INT"] + colunas_grupo))
                        cols_presentes = [c for c in cols_necessarias if c in df_graf_tec_base.columns]

                        if df_graf_tec_base.empty or not cols_presentes:
                            continue

                        df_sub_grupo = df_graf_tec_base[cols_presentes]
                        registos_agrupados = []
                        for ano_idx, df_sub in df_sub_grupo.groupby('ANO_INT'):
                            registos_agrupados.append({
                                'ANO': ano_idx,
                                'Total': sum(calcular_soma_segura(df_sub, c) for c in colunas_grupo if c in df_sub.columns)
                            })

                        df_agrupado = pd.DataFrame(registos_agrupados)
                        if df_agrupado.empty:
                            continue

                        df_agrupado['Total_Fmt'] = df_agrupado['Total'].apply(lambda x: f"{int(x):,}".replace(",", "."))

                        st.markdown(f"### {titulo_grupo}")
                        
                        subt_tec = formatar_legenda_filtros(
                            anos_tec_sel[0], 
                            anos_tec_sel[1], 
                            mun_tec_graf, 
                            nre_tec_graf,
                            dep_tec_graf, 
                            loc_tec_graf, 
                            selecionados_grupo
                        )
                        st.caption(subt_tec)

                        fig_tec = px.line(
                            df_agrupado,
                            x='ANO',
                            y='Total',
                            markers=True,
                            custom_data=['Total_Fmt']
                        )
                        fig_tec.update_traces(
                            hovertemplate="<b>Ano:</b> %{x}<br><b>Total:</b> %{customdata[0]}<extra></extra>"
                        )
                        fig_tec.update_layout(
                            separators=',.',
                            hovermode="closest",
                            xaxis_title="Ano do Censo",
                            yaxis_title=f"Total de {titulo_grupo}"
                        )
                        fig_tec.update_xaxes(type='category', fixedrange=True)

                        min_t = df_agrupado['Total'].min()
                        max_t = df_agrupado['Total'].max()
                        fig_tec.update_yaxes(
                            tickformat=',.0f',
                            range=[min_t * 0.95, max_t * 1.05] if max_t > 0 else None,
                            fixedrange=True
                        )
                        st.plotly_chart(fig_tec, use_container_width=True, config={'displayModeBar': False}, key=f"fig_tec_{titulo_grupo.lower().replace(' ', '_')}")
                        st.markdown("---")
                else:
                    st.info("ℹ️ Selecione ao menos uma métrica acima para exibir os gráficos.")

            mostrar_graficos_tecnicos_fragmento()

        st.markdown("<br>", unsafe_allow_html=True)

        @st.fragment
        def fragmento_tabela_tecnicos():
            with st.expander("⚙️ **Personalizar Colunas Adicionais do Relatório**", expanded=False):
                st.caption("🔒 As colunas de identificação, localização, NRE, rede e código do município são fixadas automaticamente.")
                todas_cols_tec = list(df_tecnicos.columns) if not df_tecnicos.empty else []
                cols_obrigatorias_tec = [
                    'NU_ANO_CENSO', 'NO_REGIAO', 'SG_UF', 'CO_NRE', 'NO_NRE',
                    'CO_MUNICIPIO', 'NO_MUNICIPIO', 'CO_ENTIDADE', 'NO_ENTIDADE',
                    'TP_DEPENDENCIA', 'TP_LOCALIZACAO', 'CO_CURSO_EDUC_PROFISSIONAL',
                    'NO_CURSO_EDUC_PROFISSIONAL', 'NO_AREA_CURSO_PROFISSIONAL'
                ]
                cols_opcionais_disponiveis_tec = [c for c in todas_cols_tec if c not in cols_obrigatorias_tec]

                with st.form("form_cols_tec"):
                    cols_extras_rascunho_tec = st.multiselect(
                        "Marque colunas extras:", 
                        options=cols_opcionais_disponiveis_tec, 
                        default=st.session_state.get("ms_tec_confirmado", [])
                    )
                    btn_inserir_tec = st.form_submit_button("✔️ Inserir Colunas")
                    if btn_inserir_tec:
                        st.session_state["ms_tec_confirmado"] = cols_extras_rascunho_tec

            cols_extras_sel_tec = st.session_state.get("ms_tec_confirmado", [])
            cols_finais_tec = list(dict.fromkeys(cols_obrigatorias_tec + cols_extras_sel_tec))
            cols_finais_validas_tec = [c for c in cols_finais_tec if c in df_tecnicos.columns]

            df_tecnicos_exibir = df_tecnicos[cols_finais_validas_tec] if not df_tecnicos.empty and cols_finais_validas_tec else df_tecnicos
            
            if not df_tecnicos_exibir.empty:
                excel_tecnicos_bytes = converter_df_para_excel(df_tecnicos_exibir)
                st.info(f"💡 A apresentar os primeiros 100 cursos. O botão de download exporta todos os {fmt_num(len(df_tecnicos_exibir))} registos.")
                st.dataframe(df_tecnicos_exibir.head(100), use_container_width=True, height=500)
                st.download_button(
                    "📥 Baixar Cursos Excel (.xlsx)", 
                    data=excel_tecnicos_bytes, 
                    file_name="cursos_tecnicos.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Nenhum resultado encontrado.")

        fragmento_tabela_tecnicos()

    except Exception as e:
        st.error(f"Erro: {e}")

# =============================================================================
# ABA 3 - OBSERVAÇÕES E LIMITAÇÕES
# =============================================================================

with aba_obs:
    st.markdown("## 🔎 Observações e Limitações Metodológicas")
    st.caption("Orientações para uso e interpretação dos dados extraídos do Censo Escolar (INEP)")
    
    st.markdown("---")
    
    with st.container(border=True):
        st.markdown("### 1. Ausência de Cruzamento Multidimensional Agregado")
        st.write(
            "Os microdados da **Super Tabela de Escolas** disponibilizados pelo INEP refletem agregações por instituição. "
            "Portanto, **não é possível realizar cruzamentos multidimensionais diretos** entre variáveis categóricas distintas."
        )
        st.info(
            "**Exemplo Prático:** É possível visualizar a quantidade total de alunos pretos/pardos na escola e a quantidade total "
            "de alunos no turno noturno. No entanto, **não é possível identificar quantos alunos pretos/pardos estudam especificamente no turno noturno**, "
            "pois tais variáveis são contabilizadas de forma independente na declaração da escola."
        )

    with st.container(border=True):
        st.markdown("### 2. Granularidade do Turno das Turmas")
        st.write(
            "A base agregada disponibiliza o turno dividido de forma macro:"
        )
        st.markdown("""
        * **Diurno (`QT_MAT_BAS_D`):** Agrupa os turnos matutino, vespertino e intermediário.
        * **Noturno (`QT_MAT_BAS_N`):** Contabiliza o atendimento noturno.
        """)

    with st.container(border=True):
        st.markdown("### 3. Histórico e Série Temporal")
        st.markdown("""
        * **Super Tabela Escolas (2007–2025):** Série temporal longa para análise de infraestrutura, turmas e matrículas gerais.
        * **Cursos Técnicos (2023–2025):** A estrutura de acompanhamento dos Cursos Técnicos e do Itinerário de Formação Técnica (IFTP) passou por reformulações metodológicas no Censo Escolar, possuindo histórico contínuo padronizado a partir do ciclo de 2023.
        """)

    with st.container(border=True):
        st.markdown("### 4. Contabilização de Turmas nas Métricas")
        st.write(
            "Algumas variáveis de matrículas (como recortes por raça/cor, idade e sexo) representam atributos dos estudantes "
            "e não possuem uma coluna direta de contagem de turmas vinculada na tabela do INEP. Nessas métricas, a coluna 'Turmas' "
            "ficará exibida como `-` por não existir turmas para essas categorias."
        )

    with st.container(border=True):
        st.markdown("### 5. Contabilização de Outras Métricas")
        st.write(
            "Esta plataforma exibe resultados consolidados e gráficos sobre matrículas, turmas e cursos. "
            "Para a realização de análises avançadas ou cálculo de outros quantitativos específicos, "
            "é disponibilizado ao final de cada aba um arquivo em formato Excel (.xlsx) para download completo dos dados filtrados."
        )
