import streamlit as st
import pandas as pd
import sqlite3
import hashlib

# --- CONEXÃO COM O BANCO DE DADOS ---
# O arquivo escola.db será criado automaticamente na primeira execução
conn = sqlite3.connect('escola.db', check_same_thread=False)
c = conn.cursor()

def criar_tabelas():
    # Tabela de Usuários (Professores e Gestores)
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (nome TEXT, usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)''')
    # Tabela de Planos de Aula
    c.execute('CREATE TABLE IF NOT EXISTS planos(autor TEXT, serie TEXT, habilidade TEXT, conteudo TEXT)')
    # Tabela de Notas
    c.execute('CREATE TABLE IF NOT EXISTS notas(professor TEXT, aluno TEXT, turma TEXT, nota REAL)')
    conn.commit()

criar_tabelas()

# --- FUNÇÕES DE SEGURANÇA ---
def criar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha, senha_hash):
    return hashlib.sha256(senha.encode()).hexdigest() == senha_hash

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EduDesk Pro - Viana MA", layout="wide", page_icon="🏫")

# Inicialização do estado da sessão
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None
    st.session_state.usuario = None

# --- TELA DE LOGIN E CADASTRO ---
if not st.session_state.logado:
    st.title("🔐 EduDesk - Portal de Acesso")
    
    tab1, tab2 = st.tabs(["Fazer Login", "Cadastrar Novo Usuário"])
    
    with tab1:
        user = st.text_input("Usuário", key="login_user")
        pw = st.text_input("Senha", type="password", key="login_pw")
        if st.button("Entrar"):
            c.execute('SELECT senha, perfil FROM usuarios WHERE usuario = ?', (user,))
            res = c.fetchone()
            if res and verificar_senha(pw, res[0]):
                st.session_state.logado = True
                st.session_state.usuario = user
                st.session_state.perfil = res[1]
                st.success(f"Bem-vindo, {user}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with tab2:
        st.subheader("Criar nova conta")
        novo_nome = st.text_input("Nome Completo")
        novo_user = st.text_input("Escolha um Usuário de Acesso")
        nova_pw = st.text_input("Escolha uma Senha", type="password")
        perfil_selecionado = st.radio("Seu cargo na escola:", ["Professor", "Gestor"])
        
        if st.button("Finalizar Cadastro"):
            if novo_nome and novo_user and nova_pw:
                try:
                    c.execute('INSERT INTO usuarios VALUES(?,?,?,?)', 
                              (novo_nome, novo_user, criar_hash(nova_pw), perfil_selecionado))
                    conn.commit()
                    st.success("Conta criada com sucesso! Mude para a aba de Login.")
                except sqlite3.IntegrityError:
                    st.error("Erro: Este nome de usuário já está em uso.")
            else:
                st.warning("Por favor, preencha todos os campos.")

# --- ÁREA RESTRITA (APÓS LOGIN) ---
else:
    # Barra Lateral
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.write(f"🏷️ Perfil: **{st.session_state.perfil}**")
    st.sidebar.divider()

    # Definição de Menus baseada no Perfil
    if st.session_state.perfil == "Gestor":
        menu = st.sidebar.radio("Painel de Gestão", ["Visão Geral (Notas)", "Banco de Planos de Aula", "Sair"])
    else:
        menu = st.sidebar.radio("Painel do Professor", ["Meu Diário de Notas", "Planejamento BNCC", "Sair"])

    if menu == "Sair":
        st.session_state.logado = False
        st.session_state.perfil = None
        st.session_state.usuario = None
        st.rerun()

    # --- LÓGICA DO GESTOR (VISUALIZAÇÃO) ---
    elif menu == "Visão Geral (Notas)":
        st.header("📈 Relatório de Desempenho Escolar")
        df_geral = pd.read_sql("SELECT * FROM notas", conn)
        
        if not df_geral.empty:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("Média por Turma")
                media_turma = df_geral.groupby('turma')['nota'].mean()
                st.bar_chart(media_turma)
            
            with col2:
                st.subheader("Dados Consolidados")
                st.dataframe(df_geral, use_container_width=True)
        else:
            st.info("Aguardando os professores lançarem as primeiras notas.")

    elif menu == "Banco de Planos de Aula":
        st.header("📂 Repositório de Planos de Aula")
        df_planos = pd.read_sql("SELECT * FROM planos", conn)
        if not df_planos.empty:
            st.dataframe(df_planos, use_container_width=True)
        else:
            st.info("Nenhum plano de aula cadastrado até o momento.")

    # --- LÓGICA DO PROFESSOR (LANÇAMENTOS) ---
    elif menu == "Meu Diário de Notas":
        st.header("✍️ Lançamento de Notas")
        
        with st.expander("➕ Registrar Nota de Aluno"):
            aluno_nome = st.text_input("Nome do Aluno")
            turma_sel = st.selectbox("Turma", ["601", "701", "801", "901"])
            nota_valor = st.number_input("Nota (0 a 10)", 0.0, 10.0, step=0.5)
            
            if st.button("Salvar no Diário"):
                if aluno_nome:
                    c.execute('INSERT INTO notas VALUES(?,?,?,?)', 
                              (st.session_state.usuario, aluno_nome, turma_sel, nota_valor))
                    conn.commit()
                    st.success(f"Nota de {aluno_nome} registrada!")
                else:
                    st.error("Digite o nome do aluno.")

        st.subheader("Minhas Notas Lançadas")
        df_prof = pd.read_sql(f"SELECT aluno, turma, nota FROM notas WHERE professor = '{st.session_state.usuario}'", conn)
        st.dataframe(df_prof, use_container_width=True)

    elif menu == "Planejamento BNCC":
        st.header("📝 Planejador de Aula Automático")
        
        with st.form("form_plano"):
            serie_plano = st.selectbox("Série", ["6º Ano", "7º Ano", "8º Ano", "9º Ano"])
            habilidades = st.multiselect("Selecione as Habilidades (BNCC)", [
                "EF69LP01 - Analisar textos jornalísticos",
                "EF67LP03 - Comparar peças publicitárias",
                "EF89LP04 - Identificar recursos de persuasão",
                "EF09LP01 - Analisar neologismos e regionalismos",
                "EF69LP44 - Inferir a presença de valores sociais e culturais"
            ])
            conteudo_aula = st.text_area("Descrição da Aula / Metodologia")
            
            if st.form_submit_button("📜 Salvar e Gerar Plano"):
                if habilidades and conteudo_aula:
                    hab_string = ", ".join(habilidades)
                    c.execute('INSERT INTO planos VALUES(?,?,?,?)', 
                              (st.session_state.usuario, serie_plano, hab_string, conteudo_aula))
                    conn.commit()
                    st.success("Plano de aula salvo no banco de dados da escola!")
                else:
                    st.warning("Preencha as habilidades e o conteúdo.")
