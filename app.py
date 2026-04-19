import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF 

# --- CONEXÃO E CRIAÇÃO DO BANCO ---
conn = sqlite3.connect('escola_viana_oficial.db', check_same_thread=False)
c = conn.cursor()

def criar_tabelas():
    c.execute('CREATE TABLE IF NOT EXISTS usuarios(nome TEXT, usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS planos(
                 autor TEXT, data TEXT, horario TEXT, serie TEXT, componente TEXT, 
                 habilidades TEXT, conteudo TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS notas(professor TEXT, aluno TEXT, turma TEXT, nota REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS frequencia(professor TEXT, data TEXT, turma TEXT, aluno TEXT, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS mural(autor TEXT, titulo TEXT, mensagem TEXT, data TEXT, prioridade INTEGER)')
    conn.commit()

criar_tabelas()

# --- FUNÇÕES DE SISTEMA ---
def criar_hash(senha): 
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha, h): 
    return hashlib.sha256(senha.encode()).hexdigest() == h

def gerar_pdf_plano(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Escola Municipal Pascoal Possidonio Gomes - Plano de Aula", ln=True, align='C')
    pdf.set_font("Arial", '', 11)
    pdf.ln(5)
    
    for chave, valor in dados.items():
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"{chave}:", ln=True)
        pdf.set_font("Arial", '', 11)
        # Limpeza para evitar erros de acentuação no PDF
        texto_limpo = str(valor).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, texto_limpo)
        pdf.ln(3)
        
    return pdf.output(dest='S').encode('latin-1')

# --- CONFIGURAÇÃO DA PÁGINA (FUNDO BRANCO) ---
st.set_page_config(page_title="EduDesk - Pascoal Possidônio", layout="wide", page_icon="🏫")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #0056b3; color: white; border: none; }
    .stButton>button:hover { background-color: #003d82; color: white; }
    </style>
    """, unsafe_allow_html=True)
    """, unsafe_allow_html=True)
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None
    st.session_state.usuario = None

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    col1, col2 = st.columns([1, 4])
    with col1:
        try: 
            st.image("logo_escola.png", width=120)
        except: 
            st.info("Logo não encontrada")
    with col2: 
        st.title("EduDesk - Portal de Acesso")
        st.subheader("Escola Municipal Pascoal Possidônio Gomes")
    
    aba1, aba2 = st.tabs(["🔐 Entrar", "📝 Cadastro de Servidor"])
    
    with aba1:
        u = st.text_input("Usuário", key="login_usuario")
        p = st.text_input("Senha", type="password", key="login_senha")
        if st.button("Acessar Sistema"):
            c.execute('SELECT senha, perfil FROM usuarios WHERE usuario = ?', (u,))
            res = c.fetchone()
            if res and verificar_senha(p, res[0]):
                st.session_state.logado, st.session_state.usuario, st.session_state.perfil = True, u, res[1]
                st.rerun()
            else:
                st.error("Credenciais incorretas.")
                
    with aba2:
        n_nome = st.text_input("Nome Completo", key="cad_nome")
        n_user = st.text_input("Login", key="cad_login")
        n_pw = st.text_input("Senha", type="password", key="cad_senha")
        n_perf = st.radio("Cargo", ["Professor", "Gestor"], key="cad_cargo")
        if st.button("Realizar Cadastro"):
            try:
                c.execute('INSERT INTO usuarios VALUES(?,?,?,?)', (n_nome, n_user, criar_hash(n_pw), n_perf))
                conn.commit()
                st.success("Cadastro realizado! Retorne à aba Entrar.")
            except: 
                st.error("Erro: Este usuário já existe.")

# --- SISTEMA LOGADO ---
else:
    st.sidebar.title(f"Olá, {st.session_state.usuario}")
    st.sidebar.caption(f"Perfil: {st.session_state.perfil}")
    st.sidebar.divider()
    
    turmas_escola = ["6º Ano", "7º Ano", "8º Ano", "9º Ano"]
    horarios_aula = ["1º Horário", "2º Horário", "3º Horário", "4º Horário", "5º Horário"]
    
    if st.session_state.perfil == "Gestor":
        menu = st.sidebar.radio("Menu de Gestão", ["Mural da Escola", "Relatórios Gerais", "Planos de Aula (Arquivo)", "Sair"])
    else:
        menu = st.sidebar.radio("Menu Pedagógico", ["Mural da Escola", "Frequência Digital", "Diário de Notas", "Planejamento (DCTMA)", "Sair"])

    if menu == "Sair":
        st.session_state.logado = False
        st.rerun()

    # --- MURAL ---
    elif menu == "Mural da Escola":
        st.header("📌 Mural de Comunicações")
        with st.expander("Colar novo recado"):
            t = st.text_input("Título do Recado")
            m = st.text_area("Mensagem")
            prio = 1 if st.session_state.perfil == "Gestor" and st.checkbox("Marcar como Comunicado Oficial") else 0
            if st.button("Publicar no Mural"):
                data_post = datetime.now().strftime("%d/%m/%Y %H:%M")
                c.execute('INSERT INTO mural VALUES(?,?,?,?,?)', (st.session_state.usuario, t, m, data_post, prio))
                conn.commit()
                st.rerun()
                
        avisos = pd.read_sql("SELECT * FROM mural ORDER BY prioridade DESC, data DESC", conn)
        for _, av in avisos.iterrows():
            if av['prioridade'] == 1:
                st.warning(f"📢 **OFICIAL: {av['titulo']}** ({av['data']})\n\n{av['mensagem']}")
            else:
                st.info(f"**{av['titulo']}** - {av['autor']} ({av['data']})\n\n{av['mensagem']}")

    # --- PLANO DE AULA ---
    elif menu == "Planejamento (DCTMA)":
        st.header("📝 Planejador de Aula (Alinhado à BNCC/DCTMA)")
        with st.form("plano_aula"):
            col1, col2 = st.columns(2)
            with col1:
                d = st.date_input("Data da Aula")
                s = st.selectbox("Série", turmas_escola)
            with col2:
                h = st.selectbox("Horário", horarios_aula)
                comp = st.selectbox("Componente Curricular", [
                    "Língua Portuguesa", "Computação", "Matemática", "História", 
                    "Geografia", "Ciências", "Arte", "Educação Física", "Ensino Religioso", "Língua Inglesa"
                ])
            
            # Banco de Habilidades Estruturado
            habs_dict = {
                "Língua Portuguesa": [
                    "EF69LP01 - Diferenciar liberdade de expressão de discursos de ódio em textos argumentativos.",
                    "EF67LP03 - Comparar informações sobre um mesmo fato em diferentes mídias.",
                    "EF89LP04 - Identificar argumentos e recursos de persuasão.",
                    "EF69LP44 - Inferir a presença de valores sociais, culturais e humanos.",
                    "EF09LP01 - Analisar a criação de neologismos e usos de regionalismos."
                ],
                "Computação": [
                    "EF06CO01 - Analisar o impacto das tecnologias digitais de informação e comunicação.",
                    "EF07CO02 - Desenvolver e testar algoritmos para a resolução de problemas.",
                    "EF08CO03 - Compreender o funcionamento estrutural da internet e redes.",
                    "EF09CO04 - Aplicar o pensamento computacional e abstração de dados."
                ],
                "Matemática": [
                    "EF06MA01 - Comparar, ordenar e ler números naturais e racionais.",
                    "EF07MA04 - Resolver e elaborar problemas que envolvam operações com números inteiros.",
                    "EF08MA06 - Resolver e elaborar problemas que envolvam cálculo de porcentagens.",
                    "EF09MA09 - Compreender os processos de fatoração de expressões algébricas."
                ],
                "Ciências": [
                    "EF06CI01 - Classificar como homogênea ou heterogênea a mistura de dois ou mais materiais.",
                    "EF07CI07 - Caracterizar os principais ecossistemas brasileiros.",
                    "EF08CI01 - Identificar e classificar diferentes fontes (renováveis e não renováveis).",
                    "EF09CI01 - Investigar as mudanças de estado físico da matéria."
                ]
            }
            
            lista_habs = habs_dict.get(comp, ["Habilidades específicas não listadas. Insira no conteúdo."])
            hab_sel = st.multiselect("Selecione as Habilidades", lista_habs)
            
            txt = st.text_area("Desenvolvimento / Procedimentos Didáticos")
            
            if st.form_submit_button("Salvar e Gerar PDF"):
                if hab_sel and txt:
                    habs_texto = "\n".join(hab_sel)
                    dados = {
                        "Professor": st.session_state.usuario, "Data": d.strftime("%d/%m/%Y"), 
                        "Horário": h, "Série": s, "Componente": comp, 
                        "Habilidades": habs_texto, "Procedimentos": txt
                    }
                    c.execute('INSERT INTO planos VALUES(?,?,?,?,?,?,?)', tuple(dados.values()))
                    conn.commit()
                    st.success("Plano arquivado com sucesso!")
                    
                    pdf_bytes = gerar_pdf_plano(dados)
                    st.download_button(
                        label="📥 Baixar Plano em PDF", 
                        data=pdf_bytes, 
                        file_name=f"Plano_{comp}_{d.strftime('%d-%m-%Y')}.pdf", 
                        mime="application/pdf"
                    )
                else:
                    st.warning("Selecione as habilidades e preencha o desenvolvimento.")

    # --- FREQUÊNCIA ---
    elif menu == "Frequência Digital":
        st.header("📅 Controle de Frequência")
        data_chamada = st.date_input("Data da Chamada")
        t_sel = st.selectbox("Turma", turmas_escola)
        
        aluno = st.text_input("Nome do Aluno")
        status = st.radio("Status", ["Presente", "Faltou"])
        
        if st.button("Registrar Presença/Falta"):
            if aluno:
                c.execute('INSERT INTO frequencia VALUES(?,?,?,?,?)', 
                          (st.session_state.usuario, data_chamada.strftime("%d/%m/%Y"), t_sel, aluno, status))
                conn.commit()
                st.success(f"Registro de {aluno} efetuado!")
            else:
                st.error("Digite o nome do aluno.")
                
        st.divider()
        st.subheader(f"Lançamentos: {data_chamada.strftime('%d/%m/%Y')} - {t_sel}")
        df_f = pd.read_sql(f"SELECT aluno, status FROM frequencia WHERE data = '{data_chamada.strftime('%d/%m/%Y')}' AND turma = '{t_sel}' AND professor = '{st.session_state.usuario}'", conn)
        st.dataframe(df_f, use_container_width=True)

    # --- NOTAS ---
    elif menu == "Diário de Notas":
        st.header("✍️ Lançamento de Notas")
        with st.container():
            aluno_n = st.text_input("Nome do Aluno")
            turma_n = st.selectbox("Turma", turmas_escola)
            nota_n = st.number_input("Nota", 0.0, 10.0, step=0.5)
            if st.button("Salvar Nota"):
                if aluno_n:
                    c.execute('INSERT INTO notas VALUES(?,?,?,?)', (st.session_state.usuario, aluno_n, turma_n, nota_n))
                    conn.commit()
                    st.success("Nota salva com sucesso!")
                else:
                    st.error("Informe o nome do aluno.")
        
        st.divider()
        st.subheader("Minhas Notas Lançadas")
        df_notas = pd.read_sql(f"SELECT aluno, turma, nota FROM notas WHERE professor = '{st.session_state.usuario}'", conn)
        st.dataframe(df_notas, use_container_width=True)

    # --- RELATÓRIOS GERAIS (GESTOR) ---
    elif menu == "Relatórios Gerais":
        st.header("📊 Painel de Gestão Automatizado")
        
        tab1, tab2 = st.tabs(["Desempenho (Notas)", "Evasão (Faltas)"])
        with tab1:
            df_notas_geral = pd.read_sql("SELECT * FROM notas", conn)
            if not df_notas_geral.empty:
                st.subheader("Média Geral por Turma")
                st.bar_chart(df_notas_geral.groupby('turma')['nota'].mean())
                st.dataframe(df_notas_geral, use_container_width=True)
            else:
                st.write("Sem notas lançadas no momento.")
                
        with tab2:
            df_freq_geral = pd.read_sql("SELECT * FROM frequencia", conn)
            if not df_freq_geral.empty:
                faltas = df_freq_geral[df_freq_geral['status'] == 'Faltou'].groupby('aluno').size()
                if not faltas.empty:
                    st.warning("Gráfico de Faltas por Aluno")
                    st.bar_chart(faltas)
                else:
                    st.success("Nenhuma falta registrada no sistema!")
                st.dataframe(df_freq_geral, use_container_width=True)
            else:
                st.write("Sem frequências lançadas no momento.")

    elif menu == "Planos de Aula (Arquivo)":
        st.header("📂 Arquivo Institucional de Planos")
        df_planos_geral = pd.read_sql("SELECT * FROM planos", conn)
        st.dataframe(df_planos_geral, use_container_width=True)
