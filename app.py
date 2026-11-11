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

# Garante que a porta 8501 seja configurada automaticamente via código
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

# =============================================================================
# MÉTRICAS DINÂMICAS DA SUPER TABELA: TODAS AS COLUNAS QT_MAT_* E QT_TUR_*
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
    import re
    s = str(sufixo).strip().upper()

    if s in {"BAS_FEM", "BAS_MASC"}:
        return "Sexo"

    if s in {"BAS_BRANCA", "BAS_PRETA", "BAS_PARDA", "BAS_AMARELA", "BAS_INDIGENA", "BAS_ND"}:
        return "Raça/Cor"

    if re.search(r"(^|_)INT($|_)", s):
        return "Integral"

    if re.search(r"_(D|N|DM|DV)$", s):
        return "Turno"

    if re.search(r"(^|_)(0_3|4_5|6_10|11_14|15_17|18_MAIS)(_|$)", s):
        return "Faixa Etária"

    if (
        s in {"PROF", "EJA", "ESP"}
        or s.startswith(("PROF_", "EJA_", "ESP_"))
        or s.startswith("MED_IFTP_")
        or s == "MED_IFTP"
        or s.startswith("BAS_DISC_PROFISSIONA")
    ):
        return "Etapas: Profissional, EJA e Especial"

    return "Etapa Comum"

def descricao_sufixo_qt(sufixo):
    coluna_mat = f"QT_MAT_{sufixo}"
    mapas = [OPCOES_ETAPAS, OPCOES_SEXO, OPCOES_RACA, OPCOES_IDADE, OPCOES_TURNO]
    for mapa in mapas:
        if coluna_mat in mapa:
            return mapa[coluna_mat].split(" (")[0]

    mapa_idade_ref = {
        "BAS_0_3_REF_31_03": "0 a 3 anos (Ref. 31/03)",
        "BAS_4_5_REF_31_03": "4 a 5 anos (Ref. 31/03)",
        "BAS_6_10_REF_31_03": "6 a 10 anos (Ref. 31/03)",
        "BAS_11_14_REF_31_03": "11 a 14 anos (Ref. 31/03)",
        "BAS_15_17_REF_31_03": "15 a 17 anos (Ref. 31/03)",
        "BAS_18_MAIS_REF_31_03": "18 anos ou mais (Ref. 31/03)",
    }
    if str(sufixo).upper() in mapa_idade_ref:
        return mapa_idade_ref[str(sufixo).upper()]
    tokens = {
        "BAS": "Educação Básica", "INF": "Educação Infantil", "CRE": "Creche",
        "PRE": "Pré-escola", "FUND": "Ensino Fundamental", "AI": "Anos Iniciais",
        "AF": "Anos Finais", "MED": "Ensino Médio", "PROF": "Educação Profissional",
        "TEC": "Técnico", "EJA": "EJA", "ESP": "Educação Especial",
        "CC": "Classes Comuns", "CE": "Classes Exclusivas", "FEM": "Feminino",
        "MASC": "Masculino", "BRANCA": "Branca", "PRETA": "Preta",
        "PARDA": "Parda", "AMARELA": "Amarela", "INDIGENA": "Indígena",
        "ND": "Não declarado", "INT": "Integral", "D": "Diurno",
        "N": "Noturno", "EAD": "Educação a distância (turno não aplicável)",
        "DM": "Manhã", "DV": "Tarde",
        "MULTIETAPA": "Multietapa", "DISC": "Disciplina",
        "LINGUA": "Língua", "PORT": "Portuguesa", "ING": "Inglesa",
        "ESPA": "Espanhola", "FRANC": "Francesa", "LIBRAS": "Libras",
        "INDIG": "Indígena", "MATEMATICA": "Matemática", "CIENCIAS": "Ciências",
        "FISICA": "Física", "QUIMICA": "Química", "BIOLOGIA": "Biologia",
        "HISTORIA": "História", "GEOGRAFIA": "Geografia", "SOCIOLOGIA": "Sociologia",
        "FILOSOFIA": "Filosofia", "PROFISSIONA": "Profissionalizante",
        "PROJETO": "Projeto", "VIDA": "de Vida", "OUTRAS": "Outras",
        "OUTRA": "Outra", "CURSO": "Curso", "CONC": "Concomitante",
        "SUBS": "Subsequente", "NM": "Normal/Magistério", "NS": "Não se aplica",
        "IFTP": "Itinerário de Formação Técnica e Profissional", "IFA": "Itinerário de Formação e Aprofundamento",
        "CT": "Concomitante", "QP": "Qualificação Profissional", "MT": "Médio-técnico",
        "OTME": "Outras modalidades", "OE": "Outros eixos", "ZR": "Zona de residência",
        "URB": "Urbana", "RUR": "Rural", "NA": "Não se aplica", "REF": "Referência",
        "31": "31", "03": "03", "0": "0", "1": "1º", "2": "2º",
        "3": "3º", "4": "4º", "5": "5º", "6": "6º", "7": "7º",
        "8": "8º", "9": "9º", "10": "10", "11": "11", "14": "14",
        "15": "15", "17": "17", "18": "18 ou mais", "MAIS": "ou mais",
        "BILINGUE": "Bilíngue", "SEG": "Segunda", "PORT_SEG": "Português como segunda língua",
        "EDUC": "Educação", "FISICA": "Física", "ARTES": "Artes",
        "EST": "Estudos", "SOCIAIS": "Sociais", "INFO": "Informática",
        "COMPUTACAO": "Computação", "RELIGIOSO": "Religioso", "ESTAGIO": "Estágio",
        "SUPER": "Supervisionado", "PEDAGOGICAS": "Pedagógicas", "CORRFLUXO": "Correção de fluxo",
        "PROP": "Propedêutico", "EXC": "Exclusivo", "LING": "Linguagens",
        "MATE": "Matemática", "CIENC": "Ciências da Natureza", "HUMA": "Ciências Humanas",
        "FIC": "Formação Inicial e Continuada", "NPROF": "Não profissionalizante",
        "TECNICO": "Técnico", "NAO": "Não", "MISTO": "Misto", "CONCL": "Concluinte",
    }
    partes = [tokens.get(parte, parte.replace("-", " ").title()) for parte in str(sufixo).split("_")]
    descricao = " · ".join(partes)
    return descricao or str(sufixo)


def construir_opcoes_metricas_qt(colunas_df):
    colunas = {str(c).strip().upper() for c in colunas_df}
    sufixos = set()
    for col in colunas:
        if col.startswith("QT_MAT_"):
            sufixos.add(col[len("QT_MAT_"):])
        elif col.startswith("QT_TUR_"):
            sufixos.add(col[len("QT_TUR_"):])

    grupos = {nome: {} for nome in GRUPOS_METRICAS_QT}
    inventario = []

    for sufixo in sorted(sufixos):
        col_mat = f"QT_MAT_{sufixo}"
        col_tur = f"QT_TUR_{sufixo}"
        tem_mat = col_mat in colunas
        tem_tur = col_tur in colunas
        categoria = categorias_metrica_qt(sufixo)
        descricao = descricao_sufixo_qt(sufixo)

        codigos = []
        if tem_mat:
            codigos.append(col_mat)
        if tem_tur:
            codigos.append(col_tur)
        rotulo = f"{descricao} — {' | '.join(codigos)}"
        grupos[categoria][sufixo] = rotulo

        inventario.append({
            "Grupo de visualização": categoria,
            "Descrição": descricao,
            "Coluna QT_MAT": col_mat if tem_mat else "—",
            "Coluna QT_TUR": col_tur if tem_tur else "—",
            "Matrículas disponível": "Sim" if tem_mat else "Não",
            "Turmas disponível": "Sim" if tem_tur else "Não",
        })

    return grupos, inventario


def _sincronizar_selecao_metricas(state_key, todos_key, item_data, widget_key, rotulo):
    selecionados = set(st.session_state.get(state_key, []))
    if st.session_state.get(widget_key, False):
        selecionados.add(rotulo)
    else:
        selecionados.discard(rotulo)
        
    st.session_state[state_key] = [r for _wk, r in item_data if r in selecionados]
    st.session_state[todos_key] = len(st.session_state[state_key]) == len(item_data)


def _alternar_todas_metricas(state_key, todos_key, item_data):
    marcar = bool(st.session_state.get(todos_key, False))
    for widget_key, rotulo in item_data:
        st.session_state[widget_key] = marcar
    st.session_state[state_key] = [rotulo for _widget_key, rotulo in item_data] if marcar else []


def criar_seletor_metricas(titulo, opcoes, chave):
    opcoes = opcoes or {}
    pares = list(opcoes.items())
    if not pares:
        st.caption(f"Nenhuma coluna disponível para {titulo} nesta base.")
        return []

    item_data = [
        (f"{chave}__item__{sufixo}", rotulo)
        for sufixo, rotulo in pares
    ]
    rotulos_validos = [rotulo for _widget_key, rotulo in item_data]
    state_key = f"{chave}__popover_selecionados"
    todos_key = f"{chave}__popover_todos"
    busca_key = f"{chave}__busca_input"

    if state_key not in st.session_state:
        escolha_anterior = st.session_state.get(f"{chave}__multi_v4", [])
        st.session_state[state_key] = [x for x in escolha_anterior if x in rotulos_validos]

    selecionados_salvos = set(st.session_state.get(state_key, []))

    for widget_key, rotulo in item_data:
        if widget_key not in st.session_state:
            st.session_state[widget_key] = rotulo in selecionados_salvos

    st.session_state[todos_key] = bool(item_data) and len(selecionados_salvos) == len(item_data)

    with st.popover(titulo):
        termo_busca = st.text_input(
            "🔎 Pesquisar termo ou código:",
            key=busca_key,
            placeholder="Ex: creche, diurno, QT_MAT..."
        ).strip().lower()

        st.checkbox(
            "Todos",
            key=todos_key,
            on_change=_alternar_todas_metricas,
            args=(state_key, todos_key, item_data),
            help="Marque ou desmarque todas as colunas deste grupo."
        )
        st.markdown("---")

        itens_filtrados = [
            (widget_key, rotulo) for widget_key, rotulo in item_data
            if not termo_busca or termo_busca in str(rotulo).lower()
        ]

        if not itens_filtrados:
            st.caption(f"Nenhuma opção encontrada para '{termo_busca}'.")
        else:
            for widget_key, rotulo in itens_filtrados:
                st.checkbox(
                    str(rotulo),
                    key=widget_key,
                    on_change=_sincronizar_selecao_metricas,
                    args=(state_key, todos_key, item_data, widget_key, rotulo)
                )

    return list(st.session_state.get(state_key, []))


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
        st.session_state[estado_chave] = [x for x in list(inicial) if x in opcoes_lista]

    selecionados = [x for x in st.session_state[estado_chave] if x in opcoes_lista]
    todos_atual = (len(selecionados) == len(opcoes_lista) and len(opcoes_lista) > 0)

    with st.popover(titulo):
        todos_novo = st.checkbox("Todos", value=todos_atual, key=todos_chave)
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
            marcado = st.checkbox(str(opcao), key=item_key)
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
    return st.selectbox(titulo, options=opcoes, index=opcoes.index(valor_atual), key=key, help=f"Selecione uma opção ou '{valor_padrao}' para incluir todos")

def get_opcoes_cruzadas_completas(df_in, nre_sel=None, mun_sel=None, dep_sel=None, loc_sel=None, cod_sel=None, nome_sel=None):
    nre_ativo = nre_sel if nre_sel not in [None, "", "Todas", "Todos"] else None
    dep_sel = list(dep_sel or [])
    loc_ativo = loc_sel if loc_sel not in [None, "", "Todas", "Todos"] else None
    mun_ativo = mun_sel if mun_sel not in [None, "", "Todas", "Todos"] else None
    cod_ativo = str(cod_sel).split(".")[0].strip() if cod_sel not in [None, "", "Todos"] else None
    nome_ativo = str(nome_sel).strip() if nome_sel not in [None, "", "Todas", "Todos"] else None

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
# CAMINHOS E CARREGAMENTO OTIMIZADOS (Evita estourar a RAM do Streamlit Cloud)
# =============================================================================

CAMINHO_ESCOLAS_PARQUET = "v1_super_tabela_escolas.parquet"
CAMINHO_TECNICOS = "v2_super_tabela_cursos_tecnicos.parquet"
CAMINHO_DICIONARIO_PARQUET = "dicionario_super_tabelas.parquet"

@st.cache_data(show_spinner="A carregar metadados de escolas para os filtros...")
def carregar_tabela_escolas(caminho_parquet, data_modificacao):
    con = duckdb.connect()
    try:
        sql = f"""
            SELECT NU_ANO_CENSO, NO_REGIAO, SG_UF, CO_NRE, NO_NRE, 
                   CO_MUNICIPIO, NO_MUNICIPIO, CO_ENTIDADE, NO_ENTIDADE, 
                   TP_DEPENDENCIA, TP_LOCALIZACAO 
            FROM read_parquet('{caminho_parquet}')
        """
        df = con.execute(sql).df()
        df.columns = df.columns.str.strip().str.upper()
        return df
    finally:
        con.close()

@st.cache_data(show_spinner="A carregar a Tabela de Cursos Técnicos...")
def carregar_tabela_tecnicos(caminho, data_modificacao):
    con = duckdb.connect()
    try:
        df = con.execute(f"SELECT * FROM read_parquet('{caminho}')").df()
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
        df = con.execute(sql).df()
        df.columns = df.columns.str.strip().str.upper()
        return df
    finally:
        con.close()

def quebrar_anos_em_lotes(anos, tamanho=3):
    """Divide os anos selecionados em lotes pequenos, sem alterar a seleção do usuário."""
    anos_limpos = sorted({int(a) for a in (anos or [])})
    for inicio in range(0, len(anos_limpos), tamanho):
        yield anos_limpos[inicio:inicio + tamanho]


def identificador_sql(nome_coluna):
    """Protege nomes de colunas do Parquet ao utilizá-los em SQL."""
    return '"' + str(nome_coluna).replace('"', '""') + '"'


def obter_colunas_parquet(caminho_parquet):
    """Obtém somente o esquema do Parquet, sem carregar seus registros."""
    con = duckdb.connect()
    try:
        descricao = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{caminho_parquet}')"
        ).fetchall()
        return [str(linha[0]).strip().upper() for linha in descricao]
    finally:
        con.close()


def montar_where_escolas(where_base="", anos=None, nre=None, municipio=None,
                         dependencias=None, localizacao=None, codigo=None, nome=None):
    """Monta os filtros para uma consulta, permitindo informar os anos por lote."""
    condicoes = []
    if where_base:
        condicoes.append(f"({where_base})")

    if anos:
        anos_sql = ", ".join(str(int(a)) for a in anos)
        condicoes.append(f"{sql_int_safe('NU_ANO_CENSO')} IN ({anos_sql})")

    if nre and nre not in ["Todas", "Todos"]:
        valor = str(nre).replace("'", "''")
        condicoes.append(f"TRIM(CAST(NO_NRE AS VARCHAR)) = '{valor}'")

    if municipio and municipio not in ["Todas", "Todos"]:
        valor = str(municipio).replace("'", "''")
        condicoes.append(f"TRIM(CAST(NO_MUNICIPIO AS VARCHAR)) = '{valor}'")

    if dependencias:
        ids = [int(str(d).split(" - ")[0]) for d in dependencias]
        condicoes.append(
            f"{sql_int_safe('TP_DEPENDENCIA')} IN ({', '.join(map(str, ids))})"
        )

    if localizacao and localizacao not in ["Todas", "Todos"]:
        loc_id = int(str(localizacao).split(" - ")[0])
        condicoes.append(f"{sql_int_safe('TP_LOCALIZACAO')} = {loc_id}")

    if codigo and codigo not in ["Todos", "Todas"]:
        cod = str(codigo).split(".")[0].strip().replace("'", "''")
        condicoes.append(
            f"TRIM(SPLIT_PART(CAST(CO_ENTIDADE AS VARCHAR), '.', 1)) = '{cod}'"
        )

    if nome and nome not in ["Todas", "Todos"]:
        valor = str(nome).replace("'", "''")
        condicoes.append(f"TRIM(CAST(NO_ENTIDADE AS VARCHAR)) = '{valor}'")

    return " AND ".join(condicoes)


def consultar_contagens_escolas(caminho_parquet, where_clause):
    """Retorna contagem de escolas distintas e de registros sem materializar a base."""
    con = duckdb.connect()
    try:
        sql = f"""
            SELECT
                COUNT(DISTINCT CO_ENTIDADE) AS ESCOLAS,
                COUNT(*) AS REGISTROS
            FROM read_parquet('{caminho_parquet}')
        """
        if where_clause:
            sql += f" WHERE {where_clause}"
        escolas, registros = con.execute(sql).fetchone()
        return int(escolas or 0), int(registros or 0)
    finally:
        con.close()


def consultar_somas_metricas_parquet(caminho_parquet, where_clause, colunas):
    """Soma somente as métricas selecionadas, sem carregar as linhas individuais."""
    colunas = list(dict.fromkeys(colunas or []))
    if not colunas:
        return {}

    expressoes = [
        f"COALESCE(SUM(TRY_CAST({identificador_sql(col)} AS DOUBLE)), 0) AS {identificador_sql(col)}"
        for col in colunas
    ]
    sql = (
        f"SELECT {', '.join(expressoes)} "
        f"FROM read_parquet('{caminho_parquet}')"
    )
    if where_clause:
        sql += f" WHERE {where_clause}"

    con = duckdb.connect()
    try:
        linha = con.execute(sql).fetchone()
        return {col: (linha[i] or 0) for i, col in enumerate(colunas)}
    finally:
        con.close()


def consultar_evolucao_metricas_lotes(caminho_parquet, where_base, anos,
                                       colunas_mat, colunas_tur, tamanho_lote=3):
    """Calcula a evolução em lotes de até três anos e retorna somente os totais anuais."""
    colunas_soma = list(dict.fromkeys((colunas_mat or []) + (colunas_tur or [])))
    if not anos or not colunas_soma:
        return pd.DataFrame(columns=["ANO", "Matrículas", "Turmas"])

    expressoes = [
        f"COALESCE(SUM(TRY_CAST({identificador_sql(col)} AS DOUBLE)), 0) AS {identificador_sql(col)}"
        for col in colunas_soma
    ]
    registros = []
    con = duckdb.connect()
    try:
        for lote_anos in quebrar_anos_em_lotes(anos, tamanho_lote):
            where_lote = montar_where_escolas(where_base, anos=lote_anos)
            sql = f"""
                SELECT {sql_int_safe('NU_ANO_CENSO')} AS ANO,
                       {', '.join(expressoes)}
                FROM read_parquet('{caminho_parquet}')
                WHERE {where_lote}
                GROUP BY ANO
                ORDER BY ANO
            """
            resultado_lote = con.execute(sql).df()
            for _, linha in resultado_lote.iterrows():
                valor_mat = sum(float(linha.get(c, 0) or 0) for c in (colunas_mat or []))
                valor_tur = sum(float(linha.get(c, 0) or 0) for c in (colunas_tur or []))
                registros.append({
                    "ANO": int(linha["ANO"]),
                    "Matrículas": valor_mat,
                    "Turmas": valor_tur,
                })
    finally:
        con.close()

    return pd.DataFrame(registros, columns=["ANO", "Matrículas", "Turmas"])


def consultar_escolas_preview(caminho_parquet, where_clause, colunas, limite=1000):
    """Carrega somente as colunas do relatório e as primeiras linhas para a tela."""
    if not colunas:
        return pd.DataFrame()
    colunas_sql = ", ".join(identificador_sql(c) for c in colunas)
    sql = f"SELECT {colunas_sql} FROM read_parquet('{caminho_parquet}')"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += f" LIMIT {int(limite)}"
    con = duckdb.connect()
    try:
        df = con.execute(sql).df()
        df.columns = df.columns.str.strip().str.upper()
        return df
    finally:
        con.close()


def exportar_escolas_excel_lotes(caminho_parquet, where_base, anos, colunas, tamanho_lote=3):
    """Gera o Excel percorrendo lotes de três anos e lotes Arrow menores."""
    from openpyxl import Workbook

    saida = io.BytesIO()
    workbook = Workbook(write_only=True)
    planilha_numero = 1
    planilha = workbook.create_sheet(title="Relatorio_1")
    planilha.append(list(colunas))
    linhas_na_planilha = 0
    limite_linhas = 1_048_575

    colunas_sql = ", ".join(identificador_sql(c) for c in colunas)
    con = duckdb.connect()
    try:
        lotes = list(quebrar_anos_em_lotes(anos, tamanho_lote)) if anos else [None]
        for lote_anos in lotes:
            where_lote = montar_where_escolas(where_base, anos=lote_anos)
            sql = f"SELECT {colunas_sql} FROM read_parquet('{caminho_parquet}')"
            if where_lote:
                sql += f" WHERE {where_lote}"

            with con.sql(sql).to_arrow_reader(batch_size=50_000) as leitor:
                for lote_arrow in leitor:
                    for registro in lote_arrow.to_pylist():
                        if linhas_na_planilha >= limite_linhas:
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

if not os.path.exists(CAMINHO_ESCOLAS_PARQUET) or not os.path.exists(CAMINHO_TECNICOS):
    st.error("ERRO: O ficheiro Parquet das escolas ou o ficheiro de cursos técnicos não foi encontrado.")
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
            for area_selecao in ("t1", "a2"):
                for slug_grupo in CHAVES_GRUPOS_METRICAS_QT.values():
                    st.session_state.pop(f"sel_{slug_grupo}_{area_selecao}__multi_v4", None)
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
    if nre_esc and nre_esc not in ["Todas", "Todos"]:
        valor_nre = str(nre_esc).replace("'", "''")
        where_esc.append(f"TRIM(CAST(NO_NRE AS VARCHAR)) = '{valor_nre}'")
    if mun_esc and mun_esc != "Todas":
        valor_municipio = str(mun_esc).replace("'", "''")
        where_esc.append(f"TRIM(CAST(NO_MUNICIPIO AS VARCHAR)) = '{valor_municipio}'")
    if dep_esc:
        deps = [int(d.split(' - ')[0]) for d in dep_esc]
        where_esc.append(f"{sql_int_safe('TP_DEPENDENCIA')} IN ({', '.join(map(str, deps))})")
    if loc_esc and loc_esc not in ["Todas", "Todos"]:
        loc_id = int(loc_esc.split(' - ')[0])
        where_esc.append(f"{sql_int_safe('TP_LOCALIZACAO')} = {loc_id}")

    where_clause_filtros_escolas = " AND ".join(where_esc)
    where_clause_escolas = montar_where_escolas(
        where_clause_filtros_escolas,
        anos=ano_esc
    )

    try:
        colunas_escolas = obter_colunas_parquet(CAMINHO_ESCOLAS_PARQUET)
        df_escolas = pd.DataFrame(columns=colunas_escolas)

        df_escolas_meta = df_escolas_raw
        if ano_esc and "NU_ANO_CENSO" in df_escolas_meta.columns:
            anos_meta = df_escolas_meta["NU_ANO_CENSO"].astype(str).str.split('.').str[0].str.strip()
            df_escolas_meta = df_escolas_meta.loc[anos_meta.isin([str(a) for a in ano_esc])]
        if nre_esc and nre_esc not in ["Todas", "Todos"]:
            df_escolas_meta = df_escolas_meta.loc[
                df_escolas_meta["NO_NRE"].astype(str).str.strip() == str(nre_esc)
            ]
        if mun_esc and mun_esc not in ["Todas", "Todos"]:
            df_escolas_meta = df_escolas_meta.loc[
                df_escolas_meta["NO_MUNICIPIO"].astype(str).str.strip() == str(mun_esc)
            ]
        if dep_esc:
            deps_meta = [str(d).split(" - ")[0].strip() for d in dep_esc]
            dep_meta = df_escolas_meta["TP_DEPENDENCIA"].astype(str).str.split('.').str[0].str.strip()
            df_escolas_meta = df_escolas_meta.loc[dep_meta.isin(deps_meta)]
        if loc_esc and loc_esc not in ["Todas", "Todos"]:
            loc_meta_id = str(loc_esc).split(" - ")[0].strip()
            loc_meta = df_escolas_meta["TP_LOCALIZACAO"].astype(str).str.split('.').str[0].str.strip()
            df_escolas_meta = df_escolas_meta.loc[loc_meta == loc_meta_id]

        qtd_escolas_unicas, qtd_registros_escolas = consultar_contagens_escolas(
            CAMINHO_ESCOLAS_PARQUET,
            where_clause_escolas
        )

        rotulo_ano = formatar_anos(ano_esc)
        m1, m2 = st.columns(2)
        m1.metric("Escolas Encontradas", fmt_num(qtd_escolas_unicas))
        m2.metric("Ano(s) do Censo", rotulo_ano)

        # ---------------------------------------------------------------------
        # 1º Bloco: 🔎 Seleção de Visualização Instantânea das Tabelas
        # ---------------------------------------------------------------------
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
                    df_escolas_meta, nre_sel=cur_nre_t1, mun_sel=cur_mun_t1, dep_sel=cur_dep_t1, loc_sel=cur_loc_t1, cod_sel=cur_cod_t1, nome_sel=cur_nome_t1
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
                
                grupos_opcoes_t, _ = construir_opcoes_metricas_qt(colunas_escolas)
                selecoes_metricas_t = {}
                for inicio_grupos in range(0, len(GRUPOS_METRICAS_QT), 4):
                    nomes_linha_grupos = GRUPOS_METRICAS_QT[inicio_grupos:inicio_grupos + 4]
                    colunas_grupos_ui = st.columns(len(nomes_linha_grupos))
                    for coluna_ui, nome_grupo_ui in zip(colunas_grupos_ui, nomes_linha_grupos):
                        with coluna_ui:
                            chave_grupo_ui = CHAVES_GRUPOS_METRICAS_QT[nome_grupo_ui]
                            selecoes_metricas_t[nome_grupo_ui] = criar_seletor_metricas(
                                nome_grupo_ui,
                                grupos_opcoes_t[nome_grupo_ui],
                                f"sel_{chave_grupo_ui}_t1"
                            )

                grupos_metricas_a1 = {
                    nome_grupo: (selecoes_metricas_t[nome_grupo], grupos_opcoes_t[nome_grupo])
                    for nome_grupo in GRUPOS_METRICAS_QT
                    if selecoes_metricas_t.get(nome_grupo)
                }

                if grupos_metricas_a1:
                    where_tabela = montar_where_escolas(
                        where_clause_filtros_escolas,
                        anos=[ano_totais_visualizacao] if ano_totais_visualizacao else ano_esc,
                        nre=nre_t_sel,
                        municipio=mun_t_sel,
                        dependencias=dep_t_sel,
                        localizacao=loc_t_sel,
                        codigo=cod_t_sel,
                        nome=nome_t_sel
                    )

                    colunas_para_somar = []
                    for _titulo, (selecionados, opcoes) in grupos_metricas_a1.items():
                        inverso = {rotulo: sufixo for sufixo, rotulo in opcoes.items()}
                        for rotulo in selecionados:
                            sufixo = inverso.get(rotulo)
                            if not sufixo:
                                continue
                            for coluna in (f"QT_MAT_{sufixo}", f"QT_TUR_{sufixo}"):
                                if coluna in colunas_escolas:
                                    colunas_para_somar.append(coluna)

                    totais_metricas = consultar_somas_metricas_parquet(
                        CAMINHO_ESCOLAS_PARQUET,
                        where_tabela,
                        colunas_para_somar
                    )

                    dados_ano = {}
                    for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_a1.items():
                        if not selecionados_grupo:
                            continue
                        linhas_totais = []
                        total_matriculas = 0
                        total_turmas = 0
                        tem_coluna_mat_grupo = False
                        tem_coluna_tur_grupo = False
                        inv_map = {v: k for k, v in opcoes_grupo.items()}

                        for rotulo in selecionados_grupo:
                            sufixo_metrica = inv_map.get(rotulo)
                            if not sufixo_metrica:
                                continue
                            coluna_mat = f"QT_MAT_{sufixo_metrica}"
                            coluna_tur = f"QT_TUR_{sufixo_metrica}"
                            tem_mat = coluna_mat in colunas_escolas
                            tem_tur = coluna_tur in colunas_escolas
                            if not tem_mat and not tem_tur:
                                continue

                            valor_mat = totais_metricas.get(coluna_mat, 0) if tem_mat else 0
                            valor_tur = totais_metricas.get(coluna_tur, 0) if tem_tur else 0
                            tem_coluna_mat_grupo = tem_coluna_mat_grupo or tem_mat
                            tem_coluna_tur_grupo = tem_coluna_tur_grupo or tem_tur
                            total_matriculas += valor_mat
                            total_turmas += valor_tur

                            linhas_totais.append({
                                "Seleção": rotulo,
                                "Matrículas": fmt_num(valor_mat) if tem_mat else "—",
                                "Turmas": fmt_num(valor_tur) if tem_tur else "—"
                            })

                        if linhas_totais:
                            linhas_totais.append({
                                "Seleção": "TOTAL DO GRUPO",
                                "Matrículas": fmt_num(total_matriculas) if tem_coluna_mat_grupo else "—",
                                "Turmas": fmt_num(total_turmas) if tem_coluna_tur_grupo else "—"
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
                                        safe_file_name = CHAVES_GRUPOS_METRICAS_QT.get(titulo_grupo, titulo_grupo.lower().replace("/", "_").replace(" ", "_"))
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

        # ---------------------------------------------------------------------
        # 2º Bloco: 🔎 Seleção de Visualização Instantânea dos Gráficos
        # ---------------------------------------------------------------------
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
                    df_escolas_meta, nre_sel=cur_nre_g1, mun_sel=cur_mun_g1, dep_sel=cur_dep_g1, loc_sel=cur_loc_g1, cod_sel=cur_cod_g1, nome_sel=cur_nome_g1
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
                
                grupos_opcoes_g = construir_opcoes_metricas_qt(colunas_escolas)[0]
                selecoes_metricas_g = {}
                for inicio_grupos in range(0, len(GRUPOS_METRICAS_QT), 4):
                    nomes_linha_grupos = GRUPOS_METRICAS_QT[inicio_grupos:inicio_grupos + 4]
                    colunas_grupos_ui = st.columns(len(nomes_linha_grupos))
                    for coluna_ui, nome_grupo_ui in zip(colunas_grupos_ui, nomes_linha_grupos):
                        with coluna_ui:
                            chave_grupo_ui = CHAVES_GRUPOS_METRICAS_QT[nome_grupo_ui]
                            selecoes_metricas_g[nome_grupo_ui] = criar_seletor_metricas(
                                nome_grupo_ui,
                                grupos_opcoes_g[nome_grupo_ui],
                                f"sel_{chave_grupo_ui}_a2"
                            )

                grupos_metricas_a2 = {
                    nome_grupo: (selecoes_metricas_g[nome_grupo], grupos_opcoes_g[nome_grupo])
                    for nome_grupo in GRUPOS_METRICAS_QT
                    if selecoes_metricas_g.get(nome_grupo)
                }

                if grupos_metricas_a2:
                    anos_grafico = [
                        str(a) for a in (ano_esc or anos_disponiveis)
                        if anos_selecionados[0] <= int(a) <= anos_selecionados[1]
                    ]
                    where_grafico = montar_where_escolas(
                        where_clause_filtros_escolas,
                        nre=nre_esc_graf,
                        municipio=mun_esc_graf,
                        dependencias=dep_esc_graf,
                        localizacao=loc_esc_graf,
                        codigo=cod_esc_sel_g,
                        nome=nome_esc_sel_g
                    )

                    for titulo_grupo, (selecionados_grupo, opcoes_grupo) in grupos_metricas_a2.items():
                        sufixos_grupo = extrair_chaves_por_rotulos(selecionados_grupo, opcoes_grupo)
                        if not sufixos_grupo:
                            continue

                        colunas_mat_grupo = [
                            f"QT_MAT_{s}" for s in sufixos_grupo
                            if f"QT_MAT_{s}" in colunas_escolas
                        ]
                        colunas_turma_grupo = [
                            f"QT_TUR_{s}" for s in sufixos_grupo
                            if f"QT_TUR_{s}" in colunas_escolas
                        ]

                        if not (colunas_mat_grupo or colunas_turma_grupo) or not anos_grafico:
                            continue

                        df_agrupado = consultar_evolucao_metricas_lotes(
                            CAMINHO_ESCOLAS_PARQUET,
                            where_grafico,
                            anos_grafico,
                            colunas_mat_grupo,
                            colunas_turma_grupo,
                            tamanho_lote=3
                        )
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

                        tem_matriculas = bool(colunas_mat_grupo)
                        tem_turmas = bool(colunas_turma_grupo)
                        safe_key_suffix = CHAVES_GRUPOS_METRICAS_QT.get(titulo_grupo, titulo_grupo.lower().replace("/", "_").replace(" ", "_"))

                        if tem_matriculas and tem_turmas:
                            g1, g2 = st.columns(2)
                            with g1:
                                st.plotly_chart(fig_mat, use_container_width=True, config={'displayModeBar': False}, key=f"mat_{safe_key_suffix}")
                            with g2:
                                st.plotly_chart(fig_tur, use_container_width=True, config={'displayModeBar': False}, key=f"tur_{safe_key_suffix}")
                        elif tem_matriculas:
                            st.plotly_chart(fig_mat, use_container_width=True, config={'displayModeBar': False}, key=f"mat_{safe_key_suffix}")
                        elif tem_turmas:
                            st.plotly_chart(fig_tur, use_container_width=True, config={'displayModeBar': False}, key=f"tur_{safe_key_suffix}")

                        st.markdown("---")
                else:
                    st.info("ℹ️ Selecione ao menos uma métrica acima para exibir os gráficos.")

            mostrar_graficos_escolas_fragmento()

        st.markdown("<br>", unsafe_allow_html=True)

        # RELATÓRIO DA ABA 1
        @st.fragment
        def fragmento_tabela_escolas():
            with st.expander("⚙️ **Personalizar Colunas Adicionais do Relatório**", expanded=False):
                st.caption("🔒 As colunas de identificação, localização, NRE, rede e código do município são fixadas automaticamente.")
                todas_cols_esc = list(colunas_escolas)
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
            cols_finais_validas = [c for c in cols_finais_esc if c in colunas_escolas]

            where_relatorio = montar_where_escolas(
                where_clause_filtros_escolas,
                anos=ano_esc
            )
            df_escolas_exibir = consultar_escolas_preview(
                CAMINHO_ESCOLAS_PARQUET,
                where_relatorio,
                cols_finais_validas,
                limite=1000
            )

            if not df_escolas_exibir.empty:
                assinatura_export = (
                    where_clause_filtros_escolas,
                    tuple(sorted(str(a) for a in (ano_esc or []))),
                    tuple(cols_finais_validas)
                )
                if st.session_state.get("_assinatura_export_escolas") != assinatura_export:
                    st.session_state.pop("_excel_escolas_bytes", None)
                    st.session_state["_assinatura_export_escolas"] = assinatura_export

                st.info(
                    f"💡 Apresenta as primeiras 1000 escolas. "
                    f"O botão abaixo prepara o Excel com todos os {fmt_num(qtd_registros_escolas)} registros."
                )
                st.dataframe(df_escolas_exibir, use_container_width=True, height=500)

                if st.button("📄 Preparar arquivo Excel para download", key="btn_preparar_excel_escolas"):
                    with st.spinner("Preparando o Excel para download..."):
                        st.session_state["_excel_escolas_bytes"] = exportar_escolas_excel_lotes(
                            CAMINHO_ESCOLAS_PARQUET,
                            where_clause_filtros_escolas,
                            ano_esc,
                            cols_finais_validas,
                            tamanho_lote=3
                        )

                if st.session_state.get("_excel_escolas_bytes") is not None:
                    st.download_button(
                        "📥 Baixar Excel (.xlsx)",
                        data=st.session_state["_excel_escolas_bytes"],
                        file_name="censo_escolas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel_escolas"
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
        if st.button("🧹 Limpar Todos os Filtros", key="btn_limpar_a3"):
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

        # ---------------------------------------------------------------------
        # 1º Bloco Aba 2: 🔎 Seleção de Visualização Instantânea das Tabelas
        # ---------------------------------------------------------------------
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
                with t_col1: 
                    sel_qtd_tec = criar_seletor_metricas("Quantidade de Cursos", OPCOES_CURSOS_QTD, "sel_qtd_tec_t1")
                with t_col2: 
                    sel_mat_tec = criar_seletor_metricas("Quantidade de Matrículas", OPCOES_CURSOS_MAT, "sel_mat_tec_t1")

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

        # ---------------------------------------------------------------------
        # 2º Bloco: 🔎 Seleção de Visualização Instantânea dos Gráficos (Aba 2)
        # ---------------------------------------------------------------------
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
                with gt1: 
                    sel_qtd_tec_graf = criar_seletor_metricas("Quantidade de Cursos", OPCOES_CURSOS_QTD, "sel_qtd_tec_g1")
                with gt2: 
                    sel_mat_tec_graf = criar_seletor_metricas("Quantidade de Matrículas", OPCOES_CURSOS_MAT, "sel_mat_tec_g1")

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

        # RELATÓRIO DA ABA 2
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
                st.info(f"💡 Apresenta os primeiros 1000 cursos. O botão de download exporta todos os {fmt_num(len(df_tecnicos_exibir))} registros.")
                st.dataframe(df_tecnicos_exibir.head(1000), use_container_width=True, height=500)
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
        st.write("Os microdados da **Super Tabela de Escolas** disponibilizados pelo INEP refletem agregações por instituição. Portanto, **não é possível realizar cruzamentos multidimensionais diretos** entre variáveis categóricas distintas.")
        st.info("**Exemplo Prático:** É possível visualizar a quantidade total de alunos pretos/pardos na escola e a quantidade total de alunos no turno noturno. No entanto, **não é possível identificar quantos alunos pretos/pardos estudam especificamente no turno noturno**, pois tais variáveis são contabilizadas de forma independente na declaração da escola.")
    
    with st.container(border=True):
        st.markdown("### 2. Disponibilidade de Variáveis por Ano (Evolução Temporal)")
        st.write("Determinadas colunas podem não estar disponíveis na seleção dependendo do ano do censo escolhido:")
        st.markdown("""
        * **Variáveis Futuras:** O ano selecionado pode ser anterior à criação da variável no Censo Escolar (ainda não existia na época).
        * **Variáveis Excluídas:** Anos posteriores podem deixar de exibir determinadas colunas devido à descontinuidade, exclusão ou substituição de métricas nas diretrizes do INEP.
        
        **Atenção:** As colunas exibidas adaptam-se dinamicamente ao ano ou período filtrado, ocultando automaticamente campos que não possuem registros ou que não faziam parte daquele ciclo censitário.
        """)

    with st.container(border=True):
        st.markdown("### 3. Granularidade do Turno das Turmas")
        st.write("A base agregada disponibiliza informações sobre os turnos em nível macro e, para determinadas etapas e modalidades, também apresenta detalhamentos por período do dia:")
        st.markdown("""
        * **Diurno (`QT_MAT_BAS_D`):** Total agregado de matrículas diurnas, podendo abranger os períodos matutino, vespertino e intermediário.
        * **Manhã (`QT_MAT_BAS_DM`):** Matrículas do período diurno matutino, quando disponível.
        * **Tarde (`QT_MAT_BAS_DV`):** Matrículas do período diurno vespertino, quando disponível.
        * **Noturno (`QT_MAT_BAS_N`):** Matrículas do período noturno.
        * **Educação a Distância (`QT_MAT_BAS_EAD`):** Matrículas classificadas nessa categoria, quando disponível.

        **Atenção:** as colunas agregadas e seus detalhamentos não devem ser somados indiscriminadamente, pois podem representar conjuntos sobrepostos. A disponibilidade de cada detalhamento depende das colunas existentes na base.
        """)

    with st.container(border=True):
        st.markdown("### 4. Histórico e Série Temporal")
        st.markdown("""
        * **Super Tabela Escolas (2007–2025):** Série temporal longa para análise de infraestrutura, turmas e matrículas gerais.
        * **Cursos Técnicos (2023–2025):** A estrutura de acompanhamento dos Cursos Técnicos e do Itinerário de Formação Técnica (IFTP) passou por reformulações metodológicas no Censo Escolar, possuindo histórico contínuo padronizado a partir do ciclo de 2023.
        """)

    with st.container(border=True):
        st.markdown("### 5. Contabilização de Turmas nas Métricas")
        st.write("Algumas variáveis de matrículas (como recortes por raça/cor, idade e sexo) representam atributos dos estudantes e não possuem uma coluna direta de contagem de turmas vinculada na tabela do INEP. Nessas métricas, a coluna 'Turmas' ficará exibida como `-` por não existir turmas para essas categorias.")

    with st.container(border=True):
        st.markdown("### 6. Contabilização de Outras Métricas")
        st.write("Esta plataforma exibe resultados consolidados e gráficos sobre matrículas, turmas e cursos. Para a realização de análises avançadas ou cálculo de outros quantitativos específicos, é disponibilizado ao final de cada aba um arquivo em formato Excel (.xlsx) para download completo dos dados filtrados.")

# =============================================================================
# ABA 4 - DICIONÁRIO DE DADOS (3 COLUNAS)
# =============================================================================

with aba_dic:
    st.markdown("## 📖 Dicionário de Dados — Super Tabelas")
    st.caption(
        "Consulta detalhada dos códigos originais das colunas, nomes do"
        " dicionário e interpretações amigáveis do painel."
    )
    st.markdown("---")

    df_dicionario = carregar_dicionario_dados(CAMINHO_DICIONARIO_PARQUET)

    if not df_dicionario.empty:

        def normalizar_texto(texto):
            texto = unicodedata.normalize("NFD", str(texto))
            texto = "".join(
                caractere
                for caractere in texto
                if unicodedata.category(caractere) != "Mn"
            )
            texto = texto.lower()
            texto = re.sub(r"[\W_]+", " ", texto)
            return " ".join(texto.split())

        def normalizar_preservando_separadores(texto):
            texto = unicodedata.normalize("NFD", str(texto))
            texto = "".join(
                caractere
                for caractere in texto
                if unicodedata.category(caractere) != "Mn"
            )
            texto = texto.lower()
            texto = re.sub(r"\s*([/._-])\s*", r"\1", texto)
            return " ".join(texto.split())

        entrada_pesquisa_dic = st.text_input(
            "🔎 Pesquisar no dicionário (código, dicionário ou interpretação):",
            placeholder="Ex: QT_MAT_EJA, Fundamental Anos Finais, NRE...",
        ).strip()

        termo_pesquisa_dic = normalizar_texto(entrada_pesquisa_dic)
        consulta_preservada = normalizar_preservando_separadores(entrada_pesquisa_dic)
        fragmentos_com_separador = re.findall(r"[^\s]*[-/._][^\s]*", consulta_preservada)

        if termo_pesquisa_dic:
            termos = termo_pesquisa_dic.split()

            def linha_corresponde(row):
                textos_originais = [
                    normalizar_preservando_separadores(valor)
                    for valor in row
                ]

                if fragmentos_com_separador:
                    for fragmento in fragmentos_com_separador:
                        if not any(
                            fragmento in texto
                            for texto in textos_originais
                        ):
                            return False

                textos = [
                    normalizar_texto(valor)
                    for valor in row
                ]

                palavras = [
                    palavra
                    for texto in textos
                    for palavra in texto.split()
                ]

                texto_compacto_original = "".join(palavras)

                def termo_corresponde(termo):
                    variantes_termo = [termo]

                    if termo.endswith("s") and len(termo) > 1:
                        variantes_termo.append(termo[:-1])
                    else:
                        variantes_termo.append(termo + "s")

                    for termo_variante in variantes_termo:
                        palavras_busca = [
                            palavra
                            for palavra in palavras
                            if not (
                                len(termo_variante) >= 4
                                and not termo_variante.endswith(("a", "o"))
                                and len(palavra) == len(termo_variante) + 1
                                and palavra.startswith(termo_variante)
                                and palavra[-1] in ("a", "o")
                            )
                        ]

                        texto_compacto = "".join(palavras_busca)

                        if (
                            any(
                                palavra.startswith(termo_variante)
                                for palavra in palavras_busca
                            )
                            or termo_variante in texto_compacto
                        ):
                            return True

                        if termo_variante.endswith("o"):
                            variante_genero = termo_variante[:-1] + "a"
                        elif termo_variante.endswith("a"):
                            variante_genero = termo_variante[:-1] + "o"
                        else:
                            variante_genero = None

                        if variante_genero:
                            if (
                                any(
                                    palavra.startswith(variante_genero)
                                    for palavra in palavras
                                )
                                or variante_genero in texto_compacto_original
                            ):
                                return True

                    return False

                return all(
                    termo_corresponde(termo)
                    for termo in termos
                )

            mask = df_dicionario.apply(
                linha_corresponde,
                axis=1
            )
            df_dicionario_exibir = df_dicionario[mask]
        else:
            df_dicionario_exibir = df_dicionario

        st.info(
            f"A mostrar {len(df_dicionario_exibir)} de {len(df_dicionario)}"
            " variáveis cadastradas."
        )

        st.dataframe(
            df_dicionario_exibir,
            use_container_width=True,
            hide_index=True,
            height=600,
        )

        excel_dic_bytes = converter_df_para_excel(df_dicionario_exibir)

        st.download_button(
            "📥 Baixar Dicionário Completo (.xlsx)",
            data=excel_dic_bytes,
            file_name="dicionario_super_tabelas_3_colunas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.markdown("---")

        st.markdown("##### ⏬ Baixar Dicionário Oficial do INEP por Ano")
        st.caption("Selecione o ano desejado para efetuar o download do arquivo Excel original INEP.")

        PASTA_EXCEL_INEP = "dicionarios_censo_escolar"
        anos_disponiveis = list(range(2025, 2006, -1))

        col_ano, col_btn = st.columns([1, 2])

        with col_ano:
            ano_selecionado = st.selectbox(
                "Selecione o ano:",
                options=anos_disponiveis,
                index=0,
                key="sb_ano_dicionario_inep"
            )

        caminho_xlsx_inep = None
        if os.path.exists(PASTA_EXCEL_INEP):
            for arquivo in os.listdir(PASTA_EXCEL_INEP):
                if str(ano_selecionado) in arquivo and arquivo.endswith(".xlsx") and not arquivo.startswith("~$"):
                    caminho_xlsx_inep = os.path.join(PASTA_EXCEL_INEP, arquivo)
                    break

        with col_btn:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if caminho_xlsx_inep and os.path.exists(caminho_xlsx_inep):
                with open(caminho_xlsx_inep, "rb") as f:
                    bytes_xlsx = f.read()

                st.download_button(
                    label=f"📥 Baixar Dicionário Oficial INEP ({ano_selecionado}) [Original .xlsx]",
                    data=bytes_xlsx,
                    file_name=os.path.basename(caminho_xlsx_inep),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"btn_dl_inep_xlsx_{ano_selecionado}"
                )
            else:
                st.warning(f"Arquivo Excel original do ano {ano_selecionado} não foi encontrado na pasta {PASTA_EXCEL_INEP}.")
