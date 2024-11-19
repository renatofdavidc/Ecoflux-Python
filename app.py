#Imports das funcionalidades a serem usadas
import oracledb
import requests
import json

#Configurações de conexão com o Oracle
def conectar_banco():
    try:
        #Se desejar testar o sistema, crie as tabelas e utilize seu próprio banco de dados oracle
        conn = oracledb.connect(
            user='',
            password='',
            dsn=''
        )
        return conn
    except oracledb.Error as e:
        print(f'Erro de conexão: {e}')

#Imprimir o menu principal
def menu():
    impressao_menu = '''
============== ECOFLUX ==============
[1] - Registrar empresa
[2] - Alternar usuários
[3] - Registrar consumo de energia
[4] - Analisar consumo de energia
[5] - Gerar relatório
[6] - Dicas de consumo
[7] - Sair
=======================================
'''
    print(impressao_menu)

#Ler e validar se a opção escolhida é válida
def ler_opcao(mensagem):
    while True:
        try:
            opcao = int(input(mensagem))
            return opcao
        except ValueError:
            print('Por favor, apenas utilize números!')
            input('Pressione Enter para tentar novamente...')

#Verificar se o CNPJ é válido
def validar_cnpj(cnpj):
    if len(cnpj) != 14:
        print('CNPJ inválido. Deve conter 14 dígitos.')
        return False

    try:
        url = f'https://open.cnpja.com/office/{cnpj}'
        
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print('CNPJ não encontrado.')
        else:
            print(f'Erro na validação. Status: {response.status_code}')
        
        return False
    
    except Exception as e:
        print(f'Erro de conexão: {e}')
        return False

#Função para criar um novo usuário, e salvá-lo no banco de dados
def criar_usuario():
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        
        print("\n===== CRIAR USUÁRIO =====")

        while True:
            username = input("Username (sem espaços): ").strip()
            if ' ' in username:
                print("Username não pode conter espaços.")
                continue

            cursor.execute("SELECT username FROM users_ecoflux WHERE username = :1", [username])
            if cursor.fetchone():
                print("Username já existe. Escolha outro.")
                continue
            break

        while True:
            senha = input("Senha (mínimo 6 caracteres): ")
            if len(senha) < 6:
                print("Senha deve ter pelo menos 6 caracteres.")
                continue
            
            confirma_senha = input("Confirme a senha: ")
            if senha != confirma_senha:
                print("Senhas não coincidem.")
                continue
            break

        nome_completo = input("Nome completo: ")

        email = input("Email: ")

        cursor.execute('''
            INSERT INTO users_ecoflux 
            (username, senha, nome_completo, email) 
            VALUES (:1, :2, :3, :4)
        ''', (username, senha, nome_completo, email))
        
        conexao.commit()
        print("Usuário criado com sucesso!")
        return username
    
    except oracledb.Error as erro:
        print(f"Erro ao criar usuário: {erro}")
        return None
    finally:
        cursor.close()
        conexao.close()

#Função de login, para verificar usuário e senha
def login():
    username = input("Username: ")
    senha = input("Senha: ")
    
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        
        cursor.execute("SELECT username FROM users_ecoflux WHERE username = :1 AND senha = :2", 
                       [username, senha])
        
        usuario = cursor.fetchone()
        
        if usuario:
            print(f"Bem-vindo, {username}!")
            return username
        else:
            print("Usuário ou senha inválidos.")
            return None
    
    except oracledb.Error as erro:
        print(f"Erro no login: {erro}")
        return None
    finally:
        cursor.close()
        conexao.close()

#Função para cadastrar uma nova empresa, usando o cnpj
def cadastrar_empresa(usuario_logado):
    if usuario_logado == None:
        print("Erro: Usuário não autenticado. Faça login primeiro.")
        return

    while True:
        cnpj = input('CNPJ: ')
        
        dados_empresa = validar_cnpj(cnpj)
        
        if not dados_empresa:
            continuar = input('Deseja tentar novamente? (S/N): ')
            if continuar.upper() != 'S':
                return
            continue

        razao_social = dados_empresa.get('company', {}).get('name', 'Não informado')

        nome_fantasia = dados_empresa.get('alias') or razao_social

        setor = (
            dados_empresa.get('mainActivity', {}).get('text') or 
            dados_empresa.get('company', {}).get('mainActivity', {}).get('text') or 
            'Não informado'
        )

        endereco_dados = dados_empresa.get('address', {})
        endereco = f"{endereco_dados.get('street', '')} {endereco_dados.get('number', '')}".strip()

        responsavel = dados_empresa.get('company', {}).get('members', [{}])[0].get('person', {}).get('name', 'Não informado')

        contato = 'Não informado'
        emails = dados_empresa.get('emails', [])
        if emails:
            contato = emails[0].get('address', 'Não informado')

        if contato == 'Não informado':
            telefones = dados_empresa.get('phones', [])
            if telefones:
                contato = f"({telefones[0].get('area', '')}) {telefones[0].get('number', '')}"

        while True:
            try:
                num_funcionarios = int(input('Número de Funcionários: '))
                break
            except ValueError:
                print('Valor inválido. Digite um número.')

        while True:
            try:
                area = float(input('Área Total (m²): ').replace(',', '.'))
                break
            except ValueError:
                print('Valor inválido. Digite um número.')

        try:
            conexao = conectar_banco()
            if not conexao:
                print('Falha na conexão com o banco de dados.')
                return
            
            cursor = conexao.cursor()
            
            cursor.execute('''
                INSERT INTO empresas 
                (cnpj, razao_social, nome_fantasia, setor, 
                 endereco, responsavel, contato, 
                 num_funcionarios, area_total, usuario_cadastro)
                VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
            ''', (
                cnpj, razao_social, nome_fantasia, setor, 
                endereco, responsavel, contato, 
                num_funcionarios, area, usuario_logado
            ))
            
            conexao.commit()
            print('Empresa cadastrada com sucesso!')
            break
        
        except oracledb.Error as erro:
            print(f'Erro ao cadastrar: {erro}')
            if input('Tentar novamente? (S/N): ').upper() != 'S':
                break
        
        finally:
            cursor.close()
            conexao.close()

#Função de listar as empresas cadastradas
def listar_empresas():
    try:
        conexao = conectar_banco()
        if not conexao:
            print('Falha na conexão com o banco de dados.')
            return
        
        cursor = conexao.cursor()

        cursor.execute('''
            SELECT cnpj, razao_social, nome_fantasia, setor 
            FROM empresas 
            ORDER BY razao_social
        ''')
        
        empresas = cursor.fetchall()
        
        if not empresas:
            print('Nenhuma empresa cadastrada.')
            return

        print('\n===== EMPRESAS CADASTRADAS =====')
        print(f'{"CNPJ":<20} {"Razão Social":<40} {"Nome Fantasia":<40} {"Setor":<30}')
        print('-' * 130)

        for empresa in empresas:
            print(f'{empresa[0]:<20} {empresa[1]:<40} {empresa[2]:<40} {empresa[3]:<30}')
        
        print(f'\nTotal de empresas: {len(empresas)}')
    
    except oracledb.Error as erro:
        print(f'Erro ao listar empresas: {erro}')
    
    finally:
        if 'conexao' in locals():
            cursor.close()
            conexao.close()
        
        input('\nPressione Enter para continuar...')

#Função de registrar o consumo de uma empresa registrada
def registrar_consumo(usuario_logado):
    if usuario_logado is None:
        print("Erro: Usuário não autenticado. Faça login primeiro.")
        return

    try:
        conexao = conectar_banco()
        if not conexao:
            print('Falha na conexão com o banco de dados.')
            return
        
        cursor = conexao.cursor()

        cursor.execute('''
            SELECT cnpj, razao_social 
            FROM empresas 
            ORDER BY razao_social
        ''')
        
        empresas = cursor.fetchall()
        
        if not empresas:
            print('Nenhuma empresa cadastrada.')
            input('Pressione Enter para continuar...')
            return

        print('\n===== SELECIONE A EMPRESA =====')
        for i, empresa in enumerate(empresas, 1):
            print(f'[{i}] {empresa[1]} (CNPJ: {empresa[0]})')

        while True:
            try:
                escolha = int(input('Escolha o número da empresa: '))
                if 1 <= escolha <= len(empresas):
                    cnpj_selecionado = empresas[escolha-1][0]
                    break
                else:
                    print('Opção inválida. Tente novamente.')
            except ValueError:
                print('Por favor, digite um número válido.')

        while True:
            try:
                consumo_kwh = float(input('Consumo de energia (kWh): ').replace(',', '.'))
                break
            except ValueError:
                print('Valor inválido. Digite um número.')
        
        while True:
            try:
                custo_total = float(input('Custo total (R$): ').replace(',', '.'))
                break
            except ValueError:
                print('Valor inválido. Digite um número.')
        
        setor = input('Setor/Departamento: ') or 'Não especificado'
        observacoes = input('Observações (opcional): ') or 'Sem observações'

        cursor.execute('''
            INSERT INTO consumo_energetico 
            (cnpj_empresa, data_registro, consumo_kwh, custo_total, setor, observacoes, usuario_registro)
            VALUES (:1, SYSDATE, :2, :3, :4, :5, :6)
        ''', (
            cnpj_selecionado, 
            consumo_kwh, 
            custo_total, 
            setor, 
            observacoes,
            usuario_logado
        ))
        
        conexao.commit()
        print('Consumo registrado com sucesso!')
    
    except oracledb.Error as erro:
        print(f'Erro ao registrar consumo: {erro}')
        conexao.rollback()
    
    finally:
        if 'conexao' in locals():
            cursor.close()
            conexao.close()
        
        input('Pressione Enter para continuar...')

#Função para fazer análise do consumo de energia
def analisar_consumo(usuario_logado):
    if usuario_logado is None:
        print("Erro: Usuário não autenticado. Faça login primeiro.")
        return

    try:
        conexao = conectar_banco()
        if not conexao:
            print('Falha na conexão com o banco de dados.')
            return
        
        cursor = conexao.cursor()

        cursor.execute('''
            SELECT cnpj, razao_social 
            FROM empresas 
            ORDER BY razao_social
        ''')
        
        empresas = cursor.fetchall()
        
        if not empresas:
            print('Nenhuma empresa cadastrada.')
            input('Pressione Enter para continuar...')
            return

        print('\n===== SELECIONE A EMPRESA =====')
        for i, empresa in enumerate(empresas, 1):
            print(f'[{i}] {empresa[1]} (CNPJ: {empresa[0]})')

        while True:
            try:
                escolha = int(input('Escolha o número da empresa: '))
                if 1 <= escolha <= len(empresas):
                    cnpj_selecionado = empresas[escolha-1][0]
                    break
                else:
                    print('Opção inválida. Tente novamente.')
            except ValueError:
                print('Por favor, digite um número válido.')

        cursor.execute('''
            SELECT 
                data_registro, 
                consumo_kwh, 
                custo_total,
                setor
            FROM consumo_energetico 
            WHERE cnpj_empresa = :1 
            AND data_registro >= ADD_MONTHS(SYSDATE, -6)
            ORDER BY data_registro DESC
        ''', [cnpj_selecionado])
        
        consumos = cursor.fetchall()
        
        if not consumos:
            print('Nenhum consumo registrado nos últimos 6 meses.')
            input('Pressione Enter para continuar...')
            return

        total_consumo = sum(consumo[1] for consumo in consumos)
        media_consumo = total_consumo / len(consumos)
        total_custo = sum(consumo[2] for consumo in consumos)
        media_custo = total_custo / len(consumos)

        print('\n===== ANÁLISE DE CONSUMO =====')
        print(f'Total de registros: {len(consumos)}')
        print(f'Consumo total: {total_consumo:.2f} kWh')
        print(f'Média de consumo: {media_consumo:.2f} kWh')
        print(f'Custo total: R$ {total_custo:.2f}')
        print(f'Média de custo: R$ {media_custo:.2f}')

        print('\nDetalhes dos Consumos:')
        print(f'{"Data":<15} {"Consumo (kWh)":<20} {"Custo (R$)":<15} {"Setor":<20}')
        print('-' * 70)
        for consumo in consumos:
            print(f'{consumo[0].strftime("%d/%m/%Y"):<15} {consumo[1]:<20.2f} {consumo[2]:<15.2f} {consumo[3]:<20}')
    
    except oracledb.Error as erro:
        print(f'Erro ao analisar consumo: {erro}')
    
    finally:
        if 'conexao' in locals():
            cursor.close()
            conexao.close()
        
        input('\nPressione Enter para continuar...')

#Função para gerar relatório em JSON do consumo
def gerar_relatorio(usuario_logado):
    if usuario_logado is None:
        print("Erro: Usuário não autenticado. Faça login primeiro.")
        return

    try:
        conexao = conectar_banco()
        if not conexao:
            print('Falha na conexão com o banco de dados.')
            return
        
        cursor = conexao.cursor()

        cursor.execute('''
            SELECT cnpj, razao_social 
            FROM empresas 
            ORDER BY razao_social
        ''')
        
        empresas = cursor.fetchall()
        
        if not empresas:
            print('Nenhuma empresa cadastrada.')
            input('Pressione Enter para continuar...')
            return

        print('\n===== SELECIONE A EMPRESA =====')
        for i, empresa in enumerate(empresas, 1):
            print(f'[{i}] {empresa[1]} (CNPJ: {empresa[0]})')

        while True:
            try:
                escolha = int(input('Escolha o número da empresa: '))
                if 1 <= escolha <= len(empresas):
                    cnpj_selecionado = empresas[escolha-1][0]
                    razao_social_selecionada = empresas[escolha-1][1]
                    break
                else:
                    print('Opção inválida. Tente novamente.')
            except ValueError:
                print('Por favor, digite um número válido.')

        cursor.execute('''
            SELECT 
                data_registro, 
                consumo_kwh, 
                custo_total,
                setor,
                observacoes
            FROM consumo_energetico 
            WHERE cnpj_empresa = :1 
            ORDER BY data_registro DESC
        ''', [cnpj_selecionado])
        
        consumos = cursor.fetchall()
        
        if not consumos:
            print('Nenhum consumo registrado para esta empresa.')
            input('Pressione Enter para continuar...')
            return

        relatorio = {
            "cnpj": cnpj_selecionado,
            "razao_social": razao_social_selecionada,
            "consumos": [
                {
                    "data_registro": consumo[0].strftime("%Y-%m-%d"),
                    "consumo_kwh": consumo[1],
                    "custo_total": consumo[2],
                    "setor": consumo[3],
                    "observacoes": consumo[4]
                } for consumo in consumos
            ]
        }

        nome_arquivo = f"relatorio_{cnpj_selecionado}.json"

        with open(nome_arquivo, 'w', encoding='utf-8') as arquivo:
            json.dump(relatorio, arquivo, indent=4, ensure_ascii=False)
        
        print(f"\nRelatório salvo com sucesso em '{nome_arquivo}'")
    
    except oracledb.Error as erro:
        print(f'Erro ao gerar relatório: {erro}')
    
    finally:
        if 'conexao' in locals():
            cursor.close()
            conexao.close()
        
        input('\nPressione Enter para continuar...')

#Lógica principal do programa
def main():
    usuario_logado = None
    
    while usuario_logado is None:
        print("\n===== ECOFLUX =====")
        print("[1] Fazer Login")
        print("[2] Criar Usuário")
        print("[3] Sair")
        
        opcao = ler_opcao("Escolha uma opção: ")
        
        match opcao:
            case 1:
                usuario_logado = login()
            case 2:
                usuario_logado = criar_usuario()
            case 3:
                print("Encerrando o programa...")
                return
            case _:
                print("Opção inválida!")

    while True:

        menu()

        opcao = ler_opcao('Escolha uma opção: ')

        match opcao:
            case 1:
                cadastrar_empresa(usuario_logado)
            case 2:
                print('Função de alternar usuários removida')
                input('Pressione Enter para continuar...')
            case 3:
                registrar_consumo(usuario_logado)
            case 4:
                analisar_consumo(usuario_logado)
            case 5:
                gerar_relatorio(usuario_logado)
            case 6:
                print('''
1. Realize auditorias energéticas periódicas.
2. Substitua lâmpadas incandescentes e fluorescentes por LEDs.
3. Instale sensores de presença para desligar luzes automaticamente.
4. Aproveite a luz natural ao máximo, com janelas amplas e claraboias.
5. Utilize sistemas de climatização eficientes (como ar-condicionado inverter).
6. Mantenha os sistemas de HVAC (aquecimento, ventilação e ar-condicionado) bem mantidos.
7. Investir em equipamentos com selo Procel ou Energy Star.
8. Instale termostatos programáveis para controlar a temperatura.
9. Faça manutenção regular de equipamentos para garantir que funcionem de forma eficiente.
10. Utilize dispositivos de medição de consumo de energia para monitorar e otimizar o uso.
11. Implante sistemas de automação predial para controlar luzes e temperatura.
12. Incentive os funcionários a desligarem computadores e outros equipamentos no final do expediente.
13. Desligue equipamentos não utilizados por longos períodos, como impressoras e copiers.
14. Reduza o uso de equipamentos de aquecimento elétrico, optando por soluções mais eficientes.
15. Invista em fontes de energia renovável, como painéis solares ou eólica.
16. Estabeleça um plano de eficiência energética e incentive os colaboradores a aderirem.
17. Otimize o uso de computadores, evitando sobrecarga e mantendo-os atualizados.
18. Use a energia de forma estratégica, priorizando o consumo durante horários de menor demanda.
19. Escolha equipamentos multifuncionais que combinem várias funções em um único dispositivo.
20. Realize treinamentos periódicos com os colaboradores sobre boas práticas de economia de energia.
21. Realize upgrades para sistemas de iluminação com controle de intensidade (dimmer).
22. Estabeleça políticas de uso consciente de energia nos setores de produção e operação.
23. Instale sistemas de energia de backup (como geradores) com eficiência energética.
24. Utilize sistemas de energia inteligente que ajustam o consumo de acordo com a demanda.
25. Aplique a reciclagem e o reuso de equipamentos sempre que possível para reduzir o impacto ambiental.
''')
                input('Pressione Enter para continuar...')
            case 7:
                print('Desconectando...')
                break
            case _:
                print('Encerrando o programa...')
                return

#Executa o programa
main()