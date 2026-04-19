import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- CONEXÃO COM O BANCO DE DADOS ---
conn = sqlite3.connect('escola_pascoal.db', check_same_thread=False)
c = conn.cursor()

def criar_tabelas():
    # Tabela de Usuários
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (nome TEXT, usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)''')
    # Tabela de Planos de Aula
    c.execute('CREATE TABLE IF NOT EXISTS planos(autor TEXT, serie TEXT, habilidade TEXT, conteudo TEXT)')
    # Tabela de Notas
    c.execute('CREATE TABLE IF NOT EXISTS notas(professor TEXT, aluno TEXT, turma TEXT, nota REAL)')
    # Tabela do Mural (com suporte a prioridade para o gestor)
    c.execute('''CREATE TABLE IF NOT EXISTS mural
                 (autor TEXT, titulo TEXT, mensagem TEXT, data TEXT, prioridade INTEGER DEFAULT 0)''')
    conn.commit()

criar_tabelas()

# --- FUNÇÕES DE SEGURANÇA ---
def criar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha, senha_hash):
    return hashlib.sha256(senha.encode()).hexdigest() == senha_hash

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EduDesk - Pascoal Possidônio Gomes", layout="wide", page_icon="🏫")

if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None
    st.session_state.usuario = None

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    col_logo, col_tit = st.columns([1, 4])
    with col_logo:
        try:
            # Tenta carregar a imagem que você subiu para o GitHub
            st.image("logo_escola.png", width=140)
        except:
            st.info("Logo da Escola")
            
    with col_tit:
        st.title("EduDesk - Portal de Acesso")
        st.subheader("Escola Municipal Pascoal Possidônio Gomes")

    tab1, tab2 = st.tabs(["🔐 Entrar no Sistema", "📝 Criar Nova Conta"])
    
    with tab1:
        user = st.text_input("Seu Usuário", key="login_user")
        pw = st.text_input("Sua Senha", type="password", key="login_pw")
        if st.button("Acessar Painel"):
            c.execute('SELECT senha, perfil FROM usuarios WHERE usuario = ?', (user,))
            res = c.fetchone()
            if res and verificar_senha(pw, res[0]):
                st.session_state.logado = True
                st.session_state.usuario = user
                st.session_state.perfil = res[1]
                st.rerun()
            else:
                st.error("Erro: Usuário ou senha incorretos.")

    with tab2:
        st.subheader("Cadastro de Novo Colaborador")
        novo_nome = st.text_input("Nome Completo")
        novo_user = st.text_input("Nome de Usuário (Login)")
        nova_pw = st.text_input("Senha de Acesso", type="password")
        perfil_sel = st.radio("Selecione seu cargo:", ["Professor", "Gestor"])
        if st.button("Confirmar Cadastro"):
            if novo_nome and novo_user and nova_pw:
                try:
                    c.execute('INSERT INTO usuarios VALUES(?,?,?,?)', 
                              (novo_nome, novo_user, criar_hash(nova_pw), perfil_sel))
                    conn.commit()
                    st.success("Conta criada com sucesso! Faça login para continuar.")
                except:
                    st.error("Este usuário já está cadastrado no sistema.")
            else:
                st.warning("Preencha todos os campos obrigatórios.")

# --- ÁREA INTERNA (SISTEMA LOGADO) ---
else:
    # Barra Lateral
    try:
        st.sidebar.image("logo_escola.png", width=120)
    except:
        pass
    st.sidebar.title(f"Bem-vindo, {st.session_state.usuario}")
    st.sidebar.write(f"Nível: **{st.session_state.perfil}**")
    st.sidebar.divider()
    
    # Menus Condicionais
    if st.session_state.perfil == "Gestor":
        menu = st.sidebar.radio("Painel Administrativo", ["Mural Escolar", "Relatório de Notas", "Arquivo de Planos", "Sair"])
    else:
        menu = st.sidebar.radio("Painel Pedagógico", ["Mural Escolar", "Meu Diário de Notas", "Planejamento BNCC", "Sair"])

    if menu == "Sair":
        st.session_state.logado = False
        st.rerun()

    # --- MÓDULO 1: MURAL DE COMUNICADOS ---
    elif menu == "Mural Escolar":
        st.header("📌 Mural da Comunidade Escolar")
        
        # Espaço para colar novo aviso
        with st.expander("➕ Publicar novo recado no mural"):
            titulo_aviso = st.text_input("Título do Aviso")
            msg_aviso = st.text_area("Mensagem completa")
            
            prio_mural = 0
            if st.session_state.perfil == "Gestor":
                # Apenas gestores podem fixar comunicados oficiais
                if st.checkbox("🚩 Destacar como Comunicado Oficial da Gestão"):
                    prio_mural = 1
            
            if st.button("Publicar no Mural"):
                data_post = datetime.now().strftime("%d/%m/%Y %H:%M")
                c.execute('INSERT INTO mural VALUES(?,?,?,?,?)', 
                          (st.session_state.usuario, titulo_aviso, msg_aviso, data_post, prio_mural))
                conn.commit()
                st.success("Postagem realizada com sucesso!")
                st.rerun()

        st.divider()
        
        # Exibição: Primeiro os oficiais, depois os comuns por data
        c.execute('SELECT * FROM mural ORDER BY prioridade DESC, data DESC')
        avisos = c.fetchall()
        
        if avisos:
            for autor, titulo, msg, data, prio in avisos:
                if prio == 1:
                    # Estilo especial para o Gestor
                    with st.container():
                        st.warning(f"📢 **COMUNICADO OFICIAL: {titulo}**")
                        st.write(msg)
                        st.caption(f"Gestão Escolar | {data}")
                        st.divider()
                else:
                    # Estilo para Professores
                    with st.container():
                        st.info(f"**{titulo}**")
                        st.write(msg)
                        st.caption(f"Postado por: {autor} em {data}")
                        st.divider()
        else:
            st.write("O mural ainda não possui postagens.")

    # --- MÓDULO 2: GESTÃO DE NOTAS (VISÃO GESTOR VS PROFESSOR) ---
    elif menu in ["Relatório de Notas", "Meu Diário de Notas"]:
        st.header("📊 Sistema de Notas")
        
        if st.session_state.perfil == "Professor":
            with st.expander("➕ Lançar Nova Nota"):
                aluno_n = st.text_input("Nome do Aluno")
                turma_n = st.selectbox("Turma", ["601", "701", "801", "901"])
                nota_n = st.number_input("Nota Final", 0.0, 10.0, step=0.5)
                if st.button("Registrar no Diário"):
                    if aluno_n:
                        c.execute('INSERT INTO notas VALUES(?,?,?,?)', 
                                  (st.session_state.usuario, aluno_n, turma_n, nota_n))
                        conn.commit()
                        st.success("Nota gravada!")
                    else:
                        st.error("Informe o nome do aluno.")
            
            st.subheader("Meu Histórico de Lançamentos")
            df_p = pd.read_sql(f"SELECT aluno, turma, nota FROM notas WHERE professor = '{st.session_state.usuario}'", conn)
            st.dataframe(df_p, use_container_width=True)
            
        else: # Visão do Gestor
            df_g = pd.read_sql("SELECT * FROM notas", conn)
            if not df_g.empty:
                st.subheader("Desempenho Geral por Turma")
                st.bar_chart(df_g.groupby('turma')['nota'].mean())
                st.subheader("Todos os Registros da Escola")
                st.dataframe(df_g, use_container_width=True)
            else:
                st.info("Nenhuma nota lançada pelos professores ainda.")

    # --- MÓDULO 3: PLANOS DE AULA ---
    elif menu in ["Arquivo de Planos", "Planejamento BNCC"]:
        st.header("📝 Gestão de Planos de Aula")
        
        if st.session_state.perfil == "Professor":
            with st.form("plano_form"):
                serie_p = st.selectbox("Série alvo", ["6º Ano", "7º Ano", "8º Ano", "9º Ano"])
                habil_p = st.multiselect("Habilidades BNCC", [
                    "EF69LP01", "EF67LP03", "EF89LP04", "EF09LP01", "EF69LP44"
                ])
                cont_p = st.text_area("Desenvolvimento Didático")
                if st.form_submit_button("Salvar Planejamento"):
                    if habil_p and cont_p:
                        c.execute('INSERT INTO planos VALUES(?,?,?,?)', 
                                  (st.session_state.usuario, serie_p, str(habil_p), cont_p))
                        conn.commit()
                        st.success("Plano salvo e enviado para o arquivo da escola!")
                    else:
                        st.warning("Preencha todos os campos do plano.")
        else:
            df_planos = pd.read_sql("SELECT * FROM planos", conn)
            st.dataframe(df_planos, use_container_width=True)
