# main.py
import streamlit as st
import datetime
import json
import os
from db import get_session, Operacao, Usuario
from fpdf import FPDF
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Operação do GGIM", layout="wide")

# Formata data no padrão brasileiro
def formatar_data_br(data):
    return data.strftime("%d/%m/%Y") if data else ""

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "forcas" not in st.session_state:
    st.session_state.forcas = []

if "apreensoes_list" not in st.session_state: # Novo estado para apreensões
    st.session_state.apreensoes_list = []

# Variáveis de estado para controle de edição e exclusão
if "edit_op_id" not in st.session_state:
    st.session_state.edit_op_id = None
if "delete_op_id" not in st.session_state:
    st.session_state.delete_op_id = None

session = get_session()

def login():
    st.title("🔐 Login")
    username = st.text_input("Usuário", key="login_username")
    password = st.text_input("Senha", type="password", key="login_password")
    if st.button("Entrar", key="login_button"):
        user = session.query(Usuario).filter_by(username=username, senha=password).first()
        if user:
            st.session_state.usuario = username
            st.success("✅ Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("❌ Usuário ou senha inválidos.")

def cadastro_usuario():
    st.title("👤 Criar Conta")
    username = st.text_input("Novo usuário", key="cadastro_username")
    password = st.text_input("Nova senha", type="password", key="cadastro_password")
    if st.button("Cadastrar", key="cadastro_button"):
        if session.query(Usuario).filter_by(username=username).first():
            st.warning("⚠️ Usuário já existe!")
        else:
            novo = Usuario(username=username, senha=password)
            session.add(novo)
            session.commit()
            st.success("✅ Usuário cadastrado com sucesso!")

# Nova Classe FPDF para incluir o cabeçalho e rodapé
class PDF(FPDF):
    def header(self):
        # Logo no canto superior esquerdo
        if os.path.exists("logo_gcm.png"):
            page_width = self.w
            image_width = 40
            x_centered = (page_width - image_width) / 2
            self.image("logo_gcm.png", x_centered, 8, image_width)
        # Título do cabeçalho
        self.set_font('Arial', 'B', 15)
        self.ln(25) # Move down after the logo for the title
        self.cell(0, 10, 'Relatório de Operação GGIM', 0, 1, 'C')
        self.ln(10) # Linha de quebra para descer o conteúdo

    def footer(self):
        # Posição a 1.5 cm do rodapé
        self.set_y(-15)
        # Seta a fonte para Arial Itálico 8
        self.set_font('Arial', 'I', 8)
        # Número da página
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')
        # Data e Hora de Geração
        current_datetime = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.set_x(10) # Volta para a margem esquerda para o texto da data/hora
        self.cell(0, 10, f'Gerado em: {current_datetime}', 0, 0, 'L')


def gerar_pdf(op):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    line_height = 10
    col_width = pdf.w / 2.2

    # Informações gerais da operação (Edição, Nome, Data) - Ordem ajustada
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(col_width, line_height, txt="Edição:", border=0)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, line_height, txt=op.edicao, ln=True, border=0)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(col_width, line_height, txt="Nome da Operação:", border=0)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, line_height, txt=op.nome_operacao, border=0)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(col_width, line_height, txt="Data:", border=0)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, line_height, txt=formatar_data_br(op.data), ln=True, border=0)
    pdf.ln(5) # Espaço após as informações básicas

    # --- Forças Empregadas --- (Movido para cá)
    if op.forcas:
        forcas = json.loads(op.forcas)
        # Filtra forças com viaturas > 0 para exibir no PDF
        displayed_forcas = [f for f in forcas if f.get('viaturas', 0) > 0]
        if displayed_forcas:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, line_height, txt="Forças Empregadas", ln=True, align="C")
            pdf.ln(2)

            # Cabeçalho da tabela de forças
            pdf.set_fill_color(200, 220, 255)
            force_name_col_width = (pdf.w - pdf.l_margin - pdf.r_margin) * 0.7
            force_qty_col_width = (pdf.w - pdf.l_margin - pdf.r_margin) * 0.3
            pdf.cell(force_name_col_width, line_height, txt="Força", border=1, fill=True, align='C')
            pdf.cell(force_qty_col_width, line_height, txt="Viaturas", border=1, ln=True, fill=True, align='C')

            pdf.set_font("Arial", '', 12)
            for f in displayed_forcas:
                pdf.cell(force_name_col_width, line_height, txt=f['nome'], border=1)
                pdf.cell(force_qty_col_width, line_height, txt=str(f['viaturas']), border=1, ln=True)
            pdf.ln(5)

    # --- Apreensões Detalhadas --- (Movido para cá)
    if op.apreensoes:
        apreensoes_data = json.loads(op.apreensoes)
        # Filtra apreensões com quantidade > 0 para exibir no PDF
        displayed_apreensoes = [ap for ap in apreensoes_data if ap.get('quantidade', 0) > 0]
        if displayed_apreensoes:
            pdf.ln(2) # Pequena quebra antes das apreensões
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, line_height, txt="Apreensões Realizadas:", ln=True, align="C")
            pdf.ln(2) # Pequena quebra antes das apreensões
            pdf.set_font("Arial", '', 12)
            # Cabeçalho da tabela de apreensões
            ap_type_col_width = (pdf.w - pdf.l_margin - pdf.r_margin) * 0.7
            ap_qty_col_width = (pdf.w - pdf.l_margin - pdf.r_margin) * 0.3
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(ap_type_col_width, line_height, txt="Tipo de Apreensão", border=1, fill=True, align='C')
            pdf.cell(ap_qty_col_width, line_height, txt="Quantidade", border=1, ln=True, fill=True, align='C')
            for ap in displayed_apreensoes:
                pdf.cell(ap_type_col_width, line_height, txt=ap.get('tipo', 'N/A'), border=1)
                pdf.cell(ap_qty_col_width, line_height, txt=str(ap.get('quantidade', 0)), border=1, ln=True)
            pdf.ln(5)


    # --- Tabela de Resultados --- (Movido para cá)
    data_resultados = {
        "Pessoas Abordadas": op.pessoas_abordadas,
        "Estabelecimentos Fiscalizados": op.estabelecimentos_fiscalizados,
        "Pessoas Conduzidas": op.pessoas_conduzidas,
        "TCOs Lavrados": op.tco,
        "Estabelecimentos Interditados": op.interditados,
    }
    # Filtra resultados com quantidade > 0 para exibir no PDF
    displayed_resultados = {metrica: quantidade for metrica, quantidade in data_resultados.items() if quantidade > 0}

    if displayed_resultados:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, line_height, txt="Resultados da Operação", ln=True, align="C")
        pdf.ln(2)

        # Cabeçalho da tabela de resultados
        pdf.set_fill_color(200, 220, 255)
        table_col_width = (pdf.w - pdf.l_margin - pdf.r_margin) / 2
        pdf.cell(table_col_width, line_height, txt="Métrica", border=1, fill=True, align='C')
        pdf.cell(table_col_width, line_height, txt="Quantidade/Detalhes", border=1, ln=True, fill=True, align='C')

        pdf.set_font("Arial", '', 12)
        for metrica, quantidade in displayed_resultados.items():
            pdf.cell(table_col_width, line_height, txt=metrica, border=1)
            pdf.cell(table_col_width, line_height, txt=str(quantidade), border=1, ln=True)
        pdf.ln(5)

    # Locais (Movido para cá)
    # Apenas exibe se houver conteúdo
    if op.locais:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(col_width, line_height, txt="Locais:", border=0)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, line_height, txt=op.locais, border=0)
        pdf.ln(5)

    # Setores (Movido para cá)
    # Apenas exibe se houver conteúdo
    if op.descricao:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(col_width, line_height, txt="Setores:", border=0)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, line_height, txt=op.descricao, border=0)
        pdf.ln(5)


    path = f"relatorio_{op.id}.pdf"
    pdf.output(path)
    return path

# Nova função para gerar o relatório geral em PDF
def gerar_relatorio_geral_pdf(total_data):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Relatório Geral das Operações GGIM', 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font("Arial", '', 12)
    line_height = 8

    # Resumo Geral
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, line_height, "Resultados Totais:", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", '', 12)

    data_items = [
        ("Pessoas Abordadas", total_data["pessoas_abordadas"]),
        ("Estabelecimentos Fiscalizados", total_data["estabelecimentos_fiscalizados"]),
        ("Pessoas Conduzidas", total_data["pessoas_conduzidas"]),
        ("TCOs Lavrados", total_data["tco"]),
        ("Estabelecimentos Interditados", total_data["interditados"]),
        ("Total de Apreensões", total_data["total_apreensoes"]),
        ("Total de Viaturas Empregadas", total_data["total_viaturas_empregadas"])
    ]

    for label, value in data_items:
        pdf.cell(pdf.w / 2 - pdf.l_margin, line_height, txt=f"{label}:", border=0)
        pdf.cell(0, line_height, txt=str(value), ln=True, border=0)

    pdf.ln(10)

    # Detalhes das Apreensões (se houver)
    if total_data["detalhes_apreensoes"]:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, line_height, "Detalhes das Apreensões por Tipo:", ln=True)
        pdf.ln(2)
        pdf.set_font("Arial", '', 12)
        for tipo, quantidade in total_data["detalhes_apreensoes"].items():
            pdf.cell(pdf.w / 2 - pdf.l_margin, line_height, txt=f"{tipo}:", border=0)
            pdf.cell(0, line_height, txt=str(quantidade), ln=True, border=0)
        pdf.ln(10)
    
    # Detalhes das Forças (se houver)
    if total_data["detalhes_forcas"]:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, line_height, "Detalhes das Forças Empregadas:", ln=True)
        pdf.ln(2)
        pdf.set_font("Arial", '', 12)
        for forca_nome, viaturas in total_data["detalhes_forcas"].items():
            pdf.cell(pdf.w / 2 - pdf.l_margin, line_height, txt=f"{forca_nome}:", border=0)
            pdf.cell(0, line_height, txt=f"{viaturas} viaturas", ln=True, border=0)
        pdf.ln(10)


    filename = f"relatorio_geral_GGIM_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename


def adicionar_forca():
    st.session_state.forcas.append({"nome": "", "viaturas": 0})

def remover_ultima_forca():
    if st.session_state.forcas:
        st.session_state.forcas.pop()

def adicionar_apreensao(): # Nova função para adicionar apreensão
    st.session_state.apreensoes_list.append({"tipo": "", "quantidade": 0})

def remover_ultima_apreensao(): # Nova função para remover apreensão
    if st.session_state.apreensoes_list:
        st.session_state.apreensoes_list.pop()

def sistema():
    st.title("🚨 Operação do GGIM - Cadastro e Visualização")
    # Adicionada a opção "Relatório Geral" no menu
    menu = st.sidebar.selectbox("Menu", ["Cadastrar Operação", "Visualizar Operações", "Análise de Dados", "Relatório Geral", "Sair"], key="main_menu")

    if menu == "Cadastrar Operação":
        with st.form("form_operacao_cadastro"):
            st.markdown("### Informações da Operação")
            form_key = "form_operacao_cadastro_key"
            if "cadastro_form_submit_count" not in st.session_state:
                st.session_state.cadastro_form_submit_count = 0
            
            current_form_key = f"{form_key}_{st.session_state.cadastro_form_submit_count}"

            edicao = st.text_input("Edição", key=f"edicao_cad_{current_form_key}")
            nome_operacao = st.text_input("Nome da Operação", key=f"nome_op_cad_{current_form_key}")
            data = st.date_input("Data", datetime.date.today(), key=f"data_cad_{current_form_key}")
            locais = st.text_area("Locais Fiscalizados (separados por vírgula)", key=f"locais_cad_{current_form_key}")
            descricao = st.text_area("Setores", key=f"descricao_cad_{current_form_key}")

            st.markdown("---")
            st.markdown("### 🚓 Forças Empregadas")
            col_f_btn1, col_f_btn2 = st.columns([3, 1])
            with col_f_btn1:
                if st.form_submit_button("➕ Adicionar Força", help="Adiciona um novo campo para Força"):
                    adicionar_forca()
            with col_f_btn2:
                if st.form_submit_button("❌ Remover Última", help="Remove o último campo de Força"):
                    remover_ultima_forca()

            for i, forca in enumerate(st.session_state.forcas):
                col_f1, col_f2 = st.columns([3, 1])
                st.session_state.forcas[i]["nome"] = col_f1.text_input(
                    f"Nome da Força {i+1}",
                    value=st.session_state.forcas[i].get("nome", ""),
                    key=f"nome_forca_cad_{i}_{current_form_key}"
                )
                st.session_state.forcas[i]["viaturas"] = col_f2.number_input(
                    f"Viaturas {i+1}",
                    min_value=0,
                    value=st.session_state.forcas[i].get("viaturas", 0),
                    key=f"viaturas_forca_cad_{i}_{current_form_key}"
                )
            st.markdown("---")

            st.markdown("### 📦 Apreensões Realizadas")
            col_ap_btn1, col_ap_btn2 = st.columns([3, 1])
            with col_ap_btn1:
                if st.form_submit_button("➕ Adicionar Apreensão", help="Adiciona um novo campo para Apreensão"):
                    adicionar_apreensao()
            with col_ap_btn2:
                if st.form_submit_button("❌ Remover Última Apreensão", help="Remove o último campo de Apreensão"):
                    remover_ultima_apreensao()

            for i, apreensao in enumerate(st.session_state.apreensoes_list):
                col_ap_i1, col_ap_i2 = st.columns([3, 1])
                st.session_state.apreensoes_list[i]["tipo"] = col_ap_i1.text_input(
                    f"Tipo de Apreensão {i+1} (ex: Veículos, Caixa de Som)",
                    value=st.session_state.apreensoes_list[i].get("tipo", ""),
                    key=f"tipo_ap_cad_{i}_{current_form_key}"
                )
                st.session_state.apreensoes_list[i]["quantidade"] = col_ap_i2.number_input(
                    f"Quantidade {i+1}",
                    min_value=0,
                    value=st.session_state.apreensoes_list[i].get("quantidade", 0),
                    key=f"quantidade_ap_cad_{i}_{current_form_key}"
                )
            st.markdown("---")

            st.markdown("### Resultados Numéricos")
            pessoas_abordadas = st.number_input("Pessoas Abordadas", min_value=0, key=f"pessoas_abordadas_cad_{current_form_key}")
            estabelecimentos_fiscalizados = st.number_input("Estabelecimentos Fiscalizados", min_value=0, key=f"estabelecimentos_fiscalizados_cad_{current_form_key}")
            pessoas_conduzidas = st.number_input("Pessoas Conduzidas", min_value=0, key=f"pessoas_conduzidas_cad_{current_form_key}")
            tco = st.number_input("TCOs Lavrados", min_value=0, key=f"tco_cad_{current_form_key}")
            interditados = st.number_input("Estabelecimentos Interditados", min_value=0, key=f"interditados_cad_{current_form_key}")

            st.markdown("---")
            st.markdown("### Imagens")
            imagens_upload = st.file_uploader("Imagens da Operação", accept_multiple_files=True, type=["png", "jpg", "jpeg"], key=f"imagens_cad_{current_form_key}")

            submitted = st.form_submit_button("Salvar Operação")
            if submitted:
                imagem_paths = []
                os.makedirs("imagens", exist_ok=True)
                for img in imagens_upload:
                    path = os.path.join("imagens", f"{edicao}_{img.name}")
                    with open(path, "wb") as f:
                        f.write(img.getbuffer())
                    imagem_paths.append(path)

                nova_operacao = Operacao(
                    edicao=edicao,
                    nome_operacao=nome_operacao,
                    data=data,
                    descricao=descricao,
                    pessoas_abordadas=pessoas_abordadas,
                    estabelecimentos_fiscalizados=estabelecimentos_fiscalizados,
                    pessoas_conduzidas=pessoas_conduzidas,
                    tco=tco,
                    interditados=interditados,
                    apreensoes=json.dumps(st.session_state.apreensoes_list), # Salva como JSON
                    locais=locais,
                    forcas=json.dumps(st.session_state.forcas),
                    imagens=json.dumps(imagem_paths)
                )
                session.add(nova_operacao)
                session.commit()
                st.success("✅ Operação cadastrada com sucesso!")
                st.session_state.forcas.clear()
                st.session_state.apreensoes_list.clear() # Limpa as apreensões

                st.session_state.cadastro_form_submit_count += 1
                st.rerun()

    elif menu == "Visualizar Operações":
        st.header("📋 Operações Cadastradas")

        # Lógica de exclusão
        if st.session_state.delete_op_id:
            op_to_delete = session.query(Operacao).get(st.session_state.delete_op_id)
            if op_to_delete:
                st.warning(f"Tem certeza que deseja excluir a operação '{op_to_delete.nome_operacao}' da edição '{op_to_delete.edicao}'?")
                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    if st.button("Confirmar Exclusão", key="confirm_delete"):
                        if op_to_delete.imagens:
                            try:
                                img_paths = json.loads(op_to_delete.imagens)
                                for p in img_paths:
                                    if os.path.exists(p):
                                        os.remove(p)
                            except json.JSONDecodeError:
                                st.error("Erro ao decodificar caminhos de imagem.")
                            except Exception as e:
                                st.error(f"Erro ao remover arquivos de imagem: {e}")

                        session.delete(op_to_delete)
                        session.commit()
                        st.success("✅ Operação excluída com sucesso!")
                        st.session_state.delete_op_id = None
                        st.rerun()
                with col_del2:
                    if st.button("Cancelar", key="cancel_delete"):
                        st.session_state.delete_op_id = None
                        st.rerun()
            else:
                st.session_state.delete_op_id = None

        # Lógica de edição
        if st.session_state.edit_op_id:
            op_to_edit = session.query(Operacao).get(st.session_state.edit_op_id)
            if op_to_edit:
                st.subheader(f"✏️ Editando Operação: {op_to_edit.edicao} - {op_to_edit.nome_operacao}")

                # Preencher st.session_state.forcas com as forças da operação para edição
                if op_to_edit.forcas:
                    st.session_state.forcas = json.loads(op_to_edit.forcas)
                else:
                    st.session_state.forcas = []

                # Preencher st.session_state.apreensoes_list com as apreensões da operação para edição
                if op_to_edit.apreensoes:
                    st.session_state.apreensoes_list = json.loads(op_to_edit.apreensoes)
                else:
                    st.session_state.apreensoes_list = []

                with st.form("form_operacao_edicao"):
                    st.markdown("### Informações da Operação (Edição)")
                    new_edicao = st.text_input("Edição", value=op_to_edit.edicao, key="edicao_edit")
                    new_nome_operacao = st.text_input("Nome da Operação", value=op_to_edit.nome_operacao, key="nome_op_edit")
                    new_data = st.date_input("Data", value=op_to_edit.data, key="data_edit")
                    new_locais = st.text_area("Locais Fiscalizados (separados por vírgula)", value=op_to_edit.locais, key="locais_edit")
                    new_descricao = st.text_area("Descrição", value=op_to_edit.descricao, key="descricao_edit")

                    st.markdown("---")
                    st.markdown("### 🚓 Forças Empregadas (Edição)")
                    col_edit_f_btn1, col_edit_f_btn2 = st.columns([3, 1])
                    with col_edit_f_btn1:
                        if st.form_submit_button("➕ Adicionar Força (Edição)", help="Adiciona um novo campo para Força"):
                            adicionar_forca()
                    with col_edit_f_btn2:
                        if st.form_submit_button("❌ Remover Última (Edição)", help="Remove o último campo de Força"):
                            remover_ultima_forca()

                    for i, forca in enumerate(st.session_state.forcas):
                        col_edit_f_i1, col_edit_f_i2 = st.columns([3, 1])
                        st.session_state.forcas[i]["nome"] = col_edit_f_i1.text_input(
                            f"Nome da Força {i+1} (Edição)",
                            value=st.session_state.forcas[i].get("nome", ""),
                            key=f"nome_forca_edit_{i}"
                        )
                        st.session_state.forcas[i]["viaturas"] = col_edit_f_i2.number_input(
                            f"Viaturas {i+1} (Edição)",
                            min_value=0,
                            value=st.session_state.forcas[i].get("viaturas", 0),
                            key=f"viaturas_forca_edit_{i}"
                        )
                    st.markdown("---")

                    st.markdown("### 📦 Apreensões Realizadas (Edição)")
                    col_edit_ap_btn1, col_edit_ap_btn2 = st.columns([3, 1])
                    with col_edit_ap_btn1:
                        if st.form_submit_button("➕ Adicionar Apreensão (Edição)", help="Adiciona um novo campo para Apreensão"):
                            adicionar_apreensao()
                    with col_edit_ap_btn2:
                        if st.form_submit_button("❌ Remover Última Apreensão (Edição)", help="Remove o último campo de Apreensão"):
                            remover_ultima_apreensao()

                    for i, apreensao in enumerate(st.session_state.apreensoes_list):
                        col_edit_ap_i1, col_edit_ap_i2 = st.columns([3, 1])
                        st.session_state.apreensoes_list[i]["tipo"] = col_edit_ap_i1.text_input(
                            f"Tipo de Apreensão {i+1} (Edição)",
                            value=st.session_state.apreensoes_list[i].get("tipo", ""),
                            key=f"tipo_ap_edit_{i}"
                        )
                        st.session_state.apreensoes_list[i]["quantidade"] = col_edit_ap_i2.number_input(
                            f"Quantidade {i+1}",
                            min_value=0,
                            value=st.session_state.apreensoes_list[i].get("quantidade", 0),
                            key=f"quantidade_ap_edit_{i}"
                        )
                    st.markdown("---")

                    st.markdown("### Resultados Numéricos (Edição)")
                    new_pessoas_abordadas = st.number_input("Pessoas Abordadas", min_value=0, value=op_to_edit.pessoas_abordadas, key="pessoas_abordadas_edit")
                    new_estabelecimentos_fiscalizados = st.number_input("Estabelecimentos Fiscalizados", min_value=0, value=op_to_edit.estabelecimentos_fiscalizados, key="estabelecimentos_fiscalizados_edit")
                    new_pessoas_conduzidas = st.number_input("Pessoas Conduzidas", min_value=0, value=op_to_edit.pessoas_conduzidas, key="pessoas_conduzidas_edit")
                    new_tco = st.number_input("TCOs Lavrados", min_value=0, value=op_to_edit.tco, key="tco_edit")
                    new_interditados = st.number_input("Estabelecimentos Interditados", min_value=0, value=op_to_edit.interditados, key="interditados_edit")

                    st.markdown("---")
                    st.markdown("#### Imagens Atuais:")
                    if op_to_edit.imagens:
                        current_images = json.loads(op_to_edit.imagens)
                        if current_images:
                            for img_path in current_images:
                                if os.path.exists(img_path):
                                    st.image(img_path, width=200, caption=os.path.basename(img_path))
                                else:
                                    st.warning(f"Imagem não encontrada: {os.path.basename(img_path)}")
                        else:
                            st.info("Nenhuma imagem anexada atualmente.")
                    else:
                        st.info("Nenhuma imagem anexada atualmente.")

                    new_imagens_upload = st.file_uploader("Upload de Novas Imagens (substituirá as atuais)", accept_multiple_files=True, type=["png", "jpg", "jpeg"], key="imagens_edit")

                    col_save_edit1, col_save_edit2 = st.columns(2)
                    with col_save_edit1:
                        save_edited = st.form_submit_button("Salvar Edição")
                    with col_save_edit2:
                        cancel_edited = st.form_submit_button("Cancelar Edição")

                    if save_edited:
                        if new_imagens_upload:
                            if op_to_edit.imagens:
                                try:
                                    old_img_paths = json.loads(op_to_edit.imagens)
                                    for p in old_img_paths:
                                        if os.path.exists(p):
                                            os.remove(p)
                                except json.JSONDecodeError:
                                    st.error("Erro ao decodificar caminhos de imagem antigos.")
                                except Exception as e:
                                    st.error(f"Erro ao remover arquivos de imagem antigos: {e}")

                            imagem_paths = []
                            os.makedirs("imagens", exist_ok=True)
                            for img in new_imagens_upload:
                                path = os.path.join("imagens", f"{new_edicao}_{img.name}")
                                with open(path, "wb") as f:
                                    f.write(img.getbuffer())
                                imagem_paths.append(path)
                            op_to_edit.imagens = json.dumps(imagem_paths)
                        elif not new_imagens_upload and op_to_edit.imagens:
                            pass
                        elif not new_imagens_upload and not op_to_edit.imagens:
                            op_to_edit.imagens = json.dumps([])

                        op_to_edit.edicao = new_edicao
                        op_to_edit.nome_operacao = new_nome_operacao
                        op_to_edit.data = new_data
                        op_to_edit.descricao = new_descricao
                        op_to_edit.pessoas_abordadas = new_pessoas_abordadas
                        op_to_edit.estabelecimentos_fiscalizados = new_estabelecimentos_fiscalizados
                        op_to_edit.pessoas_conduzidas = new_pessoas_conduzidas
                        op_to_edit.tco = new_tco
                        op_to_edit.interditados = new_interditados
                        op_to_edit.apreensoes = json.dumps(st.session_state.apreensoes_list) # Salva como JSON
                        op_to_edit.locais = new_locais
                        op_to_edit.forcas = json.dumps(st.session_state.forcas)

                        session.commit()
                        st.success("✅ Operação atualizada com sucesso!")
                        st.session_state.edit_op_id = None
                        st.session_state.forcas.clear()
                        st.session_state.apreensoes_list.clear() # Limpa as apreensões
                        st.rerun()
                    elif cancel_edited:
                        st.session_state.edit_op_id = None
                        st.session_state.forcas.clear()
                        st.session_state.apreensoes_list.clear() # Limpa as apreensões
                        st.rerun()
            else:
                st.session_state.edit_op_id = None

        # Exibe as operações (se não estiver em modo de edição/exclusão)
        if not st.session_state.edit_op_id and not st.session_state.delete_op_id:
            operacoes = session.query(Operacao).order_by(Operacao.data.desc()).all()
            if operacoes:
                for op in operacoes:
                    with st.expander(f"📌 {op.edicao} - {op.nome_operacao} ({formatar_data_br(op.data)})", expanded=False):
                        st.markdown(f"🚨 **{op.edicao}** – **{op.nome_operacao}**")
                        st.markdown(f"📅 Data: {formatar_data_br(op.data)}")
                        st.markdown("---")

                        # Forças Empregadas
                        if op.forcas:
                            try:
                                forcas = json.loads(op.forcas)
                                displayed_forcas = [f for f in forcas if f.get('viaturas', 0) > 0]
                                if displayed_forcas:
                                    st.markdown("👮‍♂️👷‍♂️🚒🚓 **Forças Empregadas:**")
                                    for f in displayed_forcas:
                                        st.markdown(f"• 🚔 {f['viaturas']} viatura(s) da {f['nome']}")
                                else:
                                    pass # Não exibe a seção se não houver viaturas > 0
                            except json.JSONDecodeError:
                                st.warning("Dados de forças com formato inválido.")
                        st.markdown("---")


                        # Apreensões Realizadas
                        if op.apreensoes:
                            try:
                                apreensoes_data = json.loads(op.apreensoes)
                                displayed_apreensoes = [ap for ap in apreensoes_data if ap.get('quantidade', 0) > 0]
                                if displayed_apreensoes:
                                    st.markdown("🚨 **Apreensões Realizadas:**")
                                    for ap in displayed_apreensoes:
                                        st.markdown(f"• 🚨 {ap.get('quantidade', 0)} {ap.get('tipo', 'item(s)')}") # Alterado para 🚨
                                else:
                                    pass # Não exibe a seção se não houver apreensões > 0
                            except json.JSONDecodeError:
                                st.warning("Dados de apreensões com formato inválido.")
                        st.markdown("---")


                        # Resultados da Operação
                        has_results = False
                        st.markdown("🔍 **Resultados da Operação:**")
                        if op.pessoas_abordadas > 0:
                            st.markdown(f"• 👥 {op.pessoas_abordadas} pessoas abordadas e devidamente qualificadas")
                            has_results = True
                        if op.estabelecimentos_fiscalizados > 0:
                            st.markdown(f"• 🏪 {op.estabelecimentos_fiscalizados} estabelecimentos fiscalizados")
                            has_results = True
                        if op.pessoas_conduzidas > 0:
                            st.markdown(f"• 🚓 {op.pessoas_conduzidas} pessoas conduzidas")
                            has_results = True
                        if op.tco > 0:
                            st.markdown(f"• 📄 {op.tco} TCOs lavrados")
                            has_results = True
                        if op.interditados > 0:
                            st.markdown(f"• 🔒 {op.interditados} estabelecimentos interditados")
                            has_results = True
                        
                        if not has_results:
                            st.info("Nenhum resultado numérico registrado.")
                        st.markdown("---")

                        # Locais Fiscalizados
                        if op.locais:
                            st.markdown("📍 **Locais Fiscalizados:**")
                            st.markdown(op.locais)
                            st.markdown("---")
                        
                        # Setores
                        if op.descricao:
                            st.markdown("🗺️ **Setores:**")
                            st.markdown(op.descricao)
                            st.markdown("---")


                        st.markdown("### 🖼️ Imagens Anexadas:")
                        if op.imagens:
                            try:
                                img_paths = json.loads(op.imagens)
                                if img_paths:
                                    for img_path in img_paths:
                                        if os.path.exists(img_path):
                                            st.image(img_path, width=250, caption=os.path.basename(img_path))
                                        else:
                                            st.warning(f"Imagem não encontrada: {os.path.basename(img_path)}")
                                else:
                                    st.info("Nenhuma imagem anexada.")
                            except json.JSONDecodeError:
                                st.error("Erro ao carregar imagens. Formato inválido.")
                        else:
                            st.info("Nenhuma imagem anexada.")

                        col_actions1, col_actions2 = st.columns(2)
                        with col_actions1:
                            if st.button("✏️ Editar", key=f"edit_op_{op.id}"):
                                st.session_state.edit_op_id = op.id
                                st.rerun()
                        with col_actions2:
                            if st.button("🗑️ Excluir", key=f"delete_op_{op.id}"):
                                st.session_state.delete_op_id = op.id
                                st.rerun()

                        pdf_path = gerar_pdf(op)
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                "📄 Baixar Relatório em PDF",
                                f,
                                file_name=f"relatorio_{op.edicao}.pdf",
                                key=f"download_pdf_{op.id}"
                            )
            else:
                st.info("ℹ️ Nenhuma operação cadastrada ainda.")

    elif menu == "Análise de Dados":
        st.header("📈 Análise de Dados das Operações")
        operacoes = session.query(Operacao).all()

        if operacoes:
            dados = []
            for op in operacoes:
                total_apreensoes = 0
                if op.apreensoes:
                    try:
                        ap_list = json.loads(op.apreensoes)
                        for ap in ap_list:
                            total_apreensoes += ap.get('quantidade', 0)
                    except json.JSONDecodeError:
                        pass # Ignora se o JSON estiver mal formatado

                dados.append({
                    "Data": op.data,
                    "Data Formatada": formatar_data_br(op.data),
                    "Abordados": op.pessoas_abordadas,
                    "Fiscalizados": op.estabelecimentos_fiscalizados,
                    "Conduzidos": op.pessoas_conduzidas,
                    "TCOs": op.tco,
                    "Interditados": op.interditados,
                    "Total Apreensões": total_apreensoes, # Adiciona o total para gráfico
                    "Apreensões Detalhadas": op.apreensoes, # Mantém o JSON para tabela detalhada
                    "Operação": f"{op.edicao} - {op.nome_operacao}"
                })

            df = pd.DataFrame(dados)

            # Gráfico principal - Incluindo Total Apreensões
            numerical_columns = ["Abordados", "Fiscalizados", "Conduzidos", "TCOs", "Interditados", "Total Apreensões"]
            numeric_df = df[numerical_columns + ["Data Formatada"]]

            fig = px.bar(
                numeric_df,
                x="Data Formatada",
                y=numerical_columns,
                title="Estatísticas das Operações",
                labels={"value": "Quantidade", "variable": "Métrica"},
                barmode="group"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabela com dados detalhados
            st.subheader("Dados Completos")
            # Para exibir as apreensões detalhadas de forma legível na tabela
            df['Apreensões Detalhadas Formatadas'] = df['Apreensões Detalhadas'].apply(
                lambda x: ", ".join([f"{item.get('tipo', 'N/A')}: {item.get('quantidade', 0)}" for item in json.loads(x)]) if x else "N/A"
            )
            st.dataframe(df.drop(columns=["Data", "Apreensões Detalhadas"]), hide_index=True)
        else:
            st.info("ℹ️ Nenhuma operação cadastrada para análise.")

    # --- Nova seção: Relatório Geral ---
    elif menu == "Relatório Geral":
        st.header("📈 Relatório Geral de Todas as Operações")

        operacoes = session.query(Operacao).all()

        if not operacoes:
            st.info("Nenhuma operação cadastrada ainda para gerar um relatório geral.")
            return

        total_pessoas_abordadas = 0
        total_estabelecimentos_fiscalizados = 0
        total_pessoas_conduzidas = 0
        total_tco = 0
        total_interditados = 0
        total_apreensoes = 0
        total_viaturas_empregadas = 0
        detalhes_apreensoes = {} # Para somar por tipo
        detalhes_forcas = {} # Para somar viaturas por tipo de força

        for op in operacoes:
            total_pessoas_abordadas += op.pessoas_abordadas
            total_estabelecimentos_fiscalizados += op.estabelecimentos_fiscalizados
            total_pessoas_conduzidas += op.pessoas_conduzidas
            total_tco += op.tco
            total_interditados += op.interditados

            if op.apreensoes:
                try:
                    ap_list = json.loads(op.apreensoes)
                    for ap in ap_list:
                        qty = ap.get('quantidade', 0)
                        tipo = ap.get('tipo', 'Outros')
                        total_apreensoes += qty
                        detalhes_apreensoes[tipo] = detalhes_apreensoes.get(tipo, 0) + qty
                except json.JSONDecodeError:
                    st.warning(f"Erro ao decodificar apreensões da operação {op.id}.")
            
            if op.forcas:
                try:
                    forcas_list = json.loads(op.forcas)
                    for f in forcas_list:
                        viaturas = f.get('viaturas', 0)
                        nome_forca = f.get('nome', 'Desconhecido')
                        total_viaturas_empregadas += viaturas
                        detalhes_forcas[nome_forca] = detalhes_forcas.get(nome_forca, 0) + viaturas
                except json.JSONDecodeError:
                    st.warning(f"Erro ao decodificar forças da operação {op.id}.")

        total_data = {
            "pessoas_abordadas": total_pessoas_abordadas,
            "estabelecimentos_fiscalizados": total_estabelecimentos_fiscalizados,
            "pessoas_conduzidas": total_pessoas_conduzidas,
            "tco": total_tco,
            "interditados": total_interditados,
            "total_apreensoes": total_apreensoes,
            "total_viaturas_empregadas": total_viaturas_empregadas,
            "detalhes_apreensoes": detalhes_apreensoes,
            "detalhes_forcas": detalhes_forcas
        }

        st.subheader("Resultados Consolidados de Todas as Operações:")
        st.metric(label="Total de Pessoas Abordadas", value=total_pessoas_abordadas)
        st.metric(label="Total de Estabelecimentos Fiscalizados", value=total_estabelecimentos_fiscalizados)
        st.metric(label="Total de Pessoas Conduzidas", value=total_pessoas_conduzidas)
        st.metric(label="Total de TCOs Lavrados", value=total_tco)
        st.metric(label="Total de Estabelecimentos Interditados", value=total_interditados)
        st.metric(label="Total Geral de Apreensões", value=total_apreensoes)
        st.metric(label="Total de Viaturas Empregadas", value=total_viaturas_empregadas)

        if detalhes_apreensoes:
            st.subheader("Detalhes de Apreensões por Tipo:")
            df_apreensoes_detalhe = pd.DataFrame(list(detalhes_apreensoes.items()), columns=['Tipo de Apreensão', 'Quantidade'])
            st.dataframe(df_apreensoes_detalhe, hide_index=True)

        if detalhes_forcas:
            st.subheader("Detalhes de Viaturas por Força Empregada:")
            df_forcas_detalhe = pd.DataFrame(list(detalhes_forcas.items()), columns=['Força', 'Total de Viaturas'])
            st.dataframe(df_forcas_detalhe, hide_index=True)


        # Botão para gerar e baixar o PDF do relatório geral
        pdf_geral_path = gerar_relatorio_geral_pdf(total_data)
        with open(pdf_geral_path, "rb") as f:
            st.download_button(
                "📄 Baixar Relatório Geral em PDF",
                f,
                file_name=os.path.basename(pdf_geral_path),
                key="download_general_pdf"
            )
        # Opcional: remover o arquivo PDF após o download (descomente se desejar)
        # os.remove(pdf_geral_path)


    elif menu == "Sair":
        st.session_state.usuario = None
        st.rerun()

# Menu principal: Condição para mostrar "Conta" / "Login" / "Criar Conta"
if st.session_state.usuario:
    st.sidebar.success(f"Logado como: {st.session_state.usuario}")
    sistema()
else:
    abas = st.sidebar.radio("Conta", ["Login", "Criar Conta"], key="account_menu")
    if abas == "Login":
        login()
    else:
        cadastro_usuario()