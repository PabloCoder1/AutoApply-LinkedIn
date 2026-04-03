import asyncio
import random
import os
import re
import requests
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import playwright_stealth
from google import genai

load_dotenv()

# ==========================================
# ⚙️ CONFIGURAÇÕES PRINCIPAIS
# ==========================================
TERMOS_BUSCA = ["RPA", "Python Junior", "Automação"]
USER_DATA_DIR = "./linkedin_session"
MAX_PAGINAS = 3

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

cache_respostas = {}

# ==========================================
# 📍 PERFIL DO PABLO
# ==========================================
MEU_PERFIL_RESUMIDO = """
Nome: Pablo Lima  
E-mail: pablolima83352@gmail.com  
Código do país: +55  
Número de celular: +55 13 99156-0814  
CPF: xxx.xxx.xxx-xx
LinkedIn: https://www.linkedin.com/in/pablo-lima-aaba02269/
Cargo: Analista Júnior de Sistemas | RPA | Automação 

Resumo:
Profissional com perfil híbrido em desenvolvimento e automação, com 2 anos de experiência em ambiente 
corporativo (Vivo), atuando na criação de soluções para otimização de processos, integrações e construção 
de fluxos escaláveis. Forte atuação com hiperautomação, qualidade de software e eficiência operacional.

Experiência:
- Musical Store (3 meses): integração ERP (Tiny) e Mercado Livre, criação de anúncios, controle de estoque,
  automação com ferramentas Google, treinamento de colaboradores.
- Vivo (Telefônica Brasil) (2 anos): Power Platform (Power Automate/Power Apps), Excel avançado, portal 
  interno (Angular → React), integrações .NET, chatbots Microsoft Agents AI, testes de IA, automações Jira,
  PI Planning.

Skills Principais: Python (2a), JavaScript (2a), Node.js (1.5a), React (1a), C#/.NET (2a),
Power Platform (2a), SQL (1a), Git (2a)

Skills Complementares: TypeScript (1a), Java (1a), Kotlin (8m), Flutter (6m), HTML/CSS (2a),
APIs REST (2a), Google Apps Script/Sheets (1.5a), Excel/VBA (2a), Jira (2a), Scrum/Agile (2a)

NÃO tenho experiência com: Photoshop, Illustrator, design gráfico, CorelDraw, After Effects,
Premiere, edição de vídeo, AutoCAD, SAP (módulos financeiros), Salesforce, Ruby, PHP, Swift.

Local: Santos, SP (Híbrido em SP ou Remoto)
Idiomas: Inglês Avançado | Espanhol Avançado
Pretensão: CLT R$ 3.500 | PJ R$ 5.500
CNH: Sim
Disponibilidade para locomoção: Sim
"""

# ==========================================
# 🧩 INTERPRETADOR LOCAL
# ==========================================

SKILLS_ANOS = {
    "python": 2, "javascript": 2, "js": 2, "node": 1.5, "node.js": 1.5,
    "nodejs": 1.5, "react": 1, "c#": 2, "csharp": 2, ".net": 2, "dotnet": 2,
    "power automate": 2, "power apps": 2, "power platform": 2, "sql": 1,
    "git": 2, "typescript": 1, "java": 1, "kotlin": 0.8, "flutter": 0.5,
    "html": 2, "css": 2, "rpa": 2, "automação": 2, "automation": 2,
    "angular": 1, "jira": 2, "apps script": 1.5, "google sheets": 1.5,
    "rest": 2, "api": 2, "erp": 1, "excel": 2, "vba": 1, "scrum": 2,
    "agile": 2, "ti": 2, "tecnologia da informação": 2, "technology": 2,
    "information technology": 2, "desenvolvimento": 2,
    "software": 2, "programação": 2, "programming": 2,
}

# Skills que Pablo NAO tem — responde "Não" direto sem chamar IA
SKILLS_NAO_TENHO = {
    "photoshop", "illustrator", "corel", "coreldraw", "indesign",
    "after effects", "premiere", "edição de vídeo", "video editing",
    "design gráfico", "graphic design", "autocad", "cad",
    "sap fi", "sap mm", "sap sd", "salesforce", "ruby", "php",
    "swift", "objective-c", "matlab",
}

SKILLS_CONHECE = set(SKILLS_ANOS.keys()) | {
    "typescript", "java", "kotlin", "flutter", "mobile", "chatbot",
    "low-code", "low code", "agile", "scrum", "pi planning",
    "microsoft", "google", "azure", "ci/cd", "linux", "bash",
    "docker", "playwright", "selenium", "automação de testes",
    "test automation", "qa", "quality assurance", "desenvolvimento",
    "programação", "software", "tecnologia", "technology", "ti",
}

IDIOMAS = {
    "inglês": "Advanced", "english": "Advanced", "ingles": "Advanced",
    "espanhol": "Advanced", "spanish": "Advanced", "espanol": "Advanced",
    "português": "Nativo", "portuguese": "Nativo",
}

PHONE_COUNTRY_CODES = {
    "country code": "Brazil (+55)",
    "código do país": "Brazil (+55)",
    "phone country": "Brazil (+55)",
    "country phone": "Brazil (+55)",
    "ddi": "+55",
    "código de país": "Brazil (+55)",
}


def interpretar_pergunta_local(pergunta: str, opcoes: list = None):
    """
    Tenta responder a pergunta SEM chamar a IA.
    Retorna a resposta como string, ou None se não souber.
    """
    p = pergunta.lower().strip()

    # --- 1. PHONE COUNTRY CODE ---
    for gatilho, resposta in PHONE_COUNTRY_CODES.items():
        if gatilho in p:
            return _match_opcao(resposta, opcoes) or _match_opcao("Brazil", opcoes) or resposta

    # --- 2. LOCALIZAÇÃO ---
    loc_triggers = ["location", "onde você mora", "current location", "cidade", "city", "where are you", "endereço"]
    if any(t in p for t in loc_triggers):
        return _match_opcao("Santos", opcoes) or "Santos, SP, Brazil"

    # --- 3. LOCOMOÇÃO / DESLOCAMENTO ---
    loco_triggers = ["locomover", "locomoção", "deslocar", "deslocamento", "commute", "relocate", "presencialmente"]
    if any(t in p for t in loco_triggers):
        return _match_opcao("Sim", opcoes) or "Sim"

    # --- 4. REMOTO / HÍBRIDO ---
    if any(t in p for t in ["remoto", "remote", "home office", "trabalho remoto"]):
        return _match_opcao("Sim", opcoes) or "Sim"
    if any(t in p for t in ["híbrido", "hybrid", "hibrido"]):
        return _match_opcao("Sim", opcoes) or "Sim"

    # --- 5. IDIOMAS ---
    for idioma, nivel in IDIOMAS.items():
        if idioma in p:
            return _match_opcao(nivel, opcoes) or nivel

    # --- 6. PRETENSÃO SALARIAL (Com Leitor de Faixas Matemáticas) ---
    salary_triggers = ["salário", "salary", "pretensão", "remuneração", "compensation", "expectativa salarial"]
    if any(t in p for t in salary_triggers):
        alvo = 5500 if any(x in p for x in ["pj", "pessoa jurídica", "freelance"]) else 3500
        if opcoes:
            for opt in opcoes:
                # Extrai números maiores que 1000 ignorando pontos e vírgulas
                nums = [int(n) for n in re.findall(r'\d{4,}', opt.replace('.', ''))]
                if len(nums) == 2 and nums[0] <= alvo <= nums[1]:
                    return opt # Achou a faixa (ex: Entre 3000 e 4000)
                elif len(nums) == 1 and ("acima" in opt.lower() or "mais" in opt.lower()) and alvo >= nums[0]:
                    return opt
                elif len(nums) == 1 and ("até" in opt.lower() or "menos" in opt.lower()) and alvo <= nums[0]:
                    return opt
        return str(alvo)

    # --- 7. CPF E LINKEDIN (Novos) ---
    if any(t in p for t in ["cpf", "cadastro de pessoa física"]):
        return "498.114.278-10" # Formato com pontuação por segurança
        
    if any(t in p for t in ["linkedin", "perfil do linkedin", "url do linkedin", "seu linkedin"]):
        return "https://www.linkedin.com/in/pablo-lima-aaba02269/"

    # --- 8. INDICAÇÃO E E-MAIL CORPORATIVO (Novos) ---
    if any(t in p for t in ["indicação", "indicou", "referral", "referred", "indicado"]):
        if any(x in p for x in ["e-mail", "email", "nome", "name", "informe"]):
            return "Não fui indicado" # Campo de texto atrelado à indicação
        return _match_opcao("Não", opcoes) or "Não" # Checkbox/Radio de indicação

    # --- 9. CAIXAS DE MÚLTIPLA ESCOLHA (Novos: Como conheceu e Motivos) ---
    if any(t in p for t in ["como você conheceu", "how did you hear", "onde nos encontrou", "como chegou"]):
        boas_opcoes = ["Site de emprego", "LinkedIn", "Redes sociais", "Plataforma de vagas"]
        for opt in boas_opcoes:
            match = _match_opcao(opt, opcoes)
            if match: return match
        return opcoes[0] if opcoes else "LinkedIn"

    if any(t in p for t in ["motivo te fez querer", "por que quer trabalhar", "why do you want to join"]):
        boas_opcoes = ["ambiente inovador", "Desafios no dia a dia", "Identificação", "propósito", "inovador"]
        for opt in boas_opcoes:
            match = _match_opcao(opt, opcoes)
            if match: return match
        return opcoes[0] if opcoes else "Busco um ambiente inovador e desafios."

    # --- 10. SKILLS QUE NÃO TENHO ---
    for skill_negativa in SKILLS_NAO_TENHO:
        if skill_negativa in p:
            return _match_opcao("Não", opcoes) or "Não"

    # --- 11. ANOS DE EXPERIÊNCIA ---
    exp_triggers = ["anos de experiência", "years of experience", "tempo de experiência", "quantos anos"]
    if any(t in p for t in exp_triggers):
        anos = _identificar_anos_skill(p)
        if anos is not None:
            if opcoes: return _match_numero_opcoes(anos, opcoes)
            return str(int(anos)) if anos >= 1 else "1"
            
        ti_generico = ["tecnologia da informação", "desenvolvimento", "software", "programação", "ti ", "it "]
        if any(t in p for t in ti_generico):
            if opcoes: return _match_numero_opcoes(2, opcoes) or "2"
            return "2"
            
        # Se pedir anos de exp em algo que não temos mapeado (ex: gestão de carteira)
        return _match_numero_opcoes(0, opcoes) or "0"

    # --- 12. TEM EXPERIÊNCIA COM X? ---
    conhece_triggers = ["tem experiência", "conhece", "já trabalhou com", "conhecimento em", "sabe usar"]
    if any(t in p for t in conhece_triggers):
        skill_encontrada = _encontrar_skill_na_pergunta(p)
        if skill_encontrada is not None:
            resposta = "Sim" if skill_encontrada else "Não"
            return _match_opcao(resposta, opcoes) or resposta
        return _match_opcao("Não", opcoes) or "Não" # Desconhecido = Não por segurança

    # --- 13. NÍVEL DE PROFICIÊNCIA ---
    nivel_triggers = ["nível", "level", "proficiency", "proficiência", "skill level"]
    if any(t in p for t in nivel_triggers):
        anos = _identificar_anos_skill(p)
        if anos is not None:
            nivel = _anos_para_nivel(anos)
            return _match_opcao(nivel, opcoes) or nivel

    # --- 14. DEMAIS GATILHOS (Vistos, CNH, PCD, Viagem) ---
    avail_triggers = ["disponível", "available", "elegível", "pode começar", "imediato"]
    if any(t in p for t in avail_triggers):
        if any(x in p for x in ["notice", "aviso", "prazo"]): return _match_opcao("Imediato", opcoes) or "Imediato"
        return _match_opcao("Sim", opcoes) or "Sim"

    if any(t in p for t in ["visa", "visto", "sponsorship", "patrocínio", "sponsor"]):
        return _match_opcao("Não", opcoes) or "Não"

    if any(x in p for x in ["cnh", "habilitação", "driver", "carteira de motorista"]):
        return _match_opcao("Sim", opcoes) or "Sim"

    if any(t in p for t in ["pcd", "deficiência", "disability"]):
        return _match_opcao("Não", opcoes) or "Não"

    if any(t in p for t in ["multinacional", "multinational", "internacional", "global"]):
        return _match_opcao("Sim", opcoes) or "Sim"

    if any(t in p for t in ["tipo de contrato", "contract type", "modalidade", "regime"]):
        return _match_opcao("CLT", opcoes) or "CLT"

    if any(t in p for t in ["viagem", "travel", "viajar", "disponibilidade para viagem"]):
        return _match_opcao("Sim", opcoes) or "Sim"

    return None


# ==========================================
# 🔧 AUXILIARES DO INTERPRETADOR
# ==========================================

def _match_opcao(resposta_ideal: str, opcoes: list):
    if not opcoes:
        return None
    resp_lower = resposta_ideal.lower()
    for opcao in opcoes:
        if resp_lower == opcao.lower().strip():
            return opcao
    for opcao in opcoes:
        if resp_lower in opcao.lower() or opcao.lower() in resp_lower:
            return opcao
    positivos = ["sim", "yes", "disponível", "available", "advanced", "fluent", "nativo", "brazil"]
    for opcao in opcoes:
        if any(pos in opcao.lower() for pos in positivos):
            return opcao
    return None


def _match_numero_opcoes(anos: float, opcoes: list):
    if not opcoes:
        return str(int(anos))
    melhor = None
    melhor_val = -1
    for opcao in opcoes:
        nums = re.findall(r'\d+', opcao)
        if nums:
            val = int(nums[0])
            if val <= anos and val > melhor_val:
                melhor_val = val
                melhor = opcao
    return melhor or opcoes[0]


def _identificar_anos_skill(pergunta: str):
    for skill, anos in SKILLS_ANOS.items():
        if skill in pergunta:
            return anos
    return None


def _encontrar_skill_na_pergunta(pergunta: str):
    for skill in SKILLS_NAO_TENHO:
        if skill in pergunta:
            return False
    for skill in SKILLS_CONHECE:
        if skill in pergunta:
            return True
    return None


def _anos_para_nivel(anos: float) -> str:
    if anos < 1:   return "Iniciante"
    if anos < 2:   return "Junior"
    if anos < 4:   return "Pleno"
    return "Sênior"


# ==========================================
# 🗄️ SISTEMA DE MEMÓRIA (SQLite)
# ==========================================
def iniciar_db():
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidaturas (
            id_vaga TEXT PRIMARY KEY,
            titulo TEXT,
            termo_busca TEXT,
            data_processamento TEXT,
            status TEXT,
            link TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memoria_perguntas (
            pergunta_limpa TEXT PRIMARY KEY,
            resposta TEXT,
            data_criacao TEXT
        )
    """)
    # Tabela de campos que o bot nao conseguiu preencher
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campos_nao_preenchidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vaga TEXT,
            titulo_vaga TEXT,
            pergunta TEXT,
            tipo_campo TEXT,
            opcoes TEXT,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()


def vaga_ja_processada(id_vaga):
    if not id_vaga:
        return False
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM candidaturas WHERE id_vaga = ?", (id_vaga,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None


def registrar_no_db(id_vaga, titulo, termo, status, link):
    if not id_vaga:
        return
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO candidaturas
            (id_vaga, titulo, termo_busca, data_processamento, status, link)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_vaga, titulo, termo, data_atual, status, link))
        conn.commit()
    except:
        pass
    finally:
        conn.close()


def registrar_campo_nao_preenchido(id_vaga, titulo_vaga, pergunta, tipo_campo, opcoes=None):
    """Salva no banco todo campo que o bot nao conseguiu preencher."""
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opcoes_str = ", ".join(opcoes) if opcoes else ""
    try:
        cursor.execute("""
            INSERT INTO campos_nao_preenchidos
            (id_vaga, titulo_vaga, pergunta, tipo_campo, opcoes, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_vaga, titulo_vaga, pergunta, tipo_campo, opcoes_str, data_atual))
        conn.commit()
    except:
        pass
    finally:
        conn.close()


def buscar_resposta_salva(pergunta):
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT resposta FROM memoria_perguntas WHERE pergunta_limpa = ?", (pergunta,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None


def salvar_resposta_na_memoria(pergunta, resposta):
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    data = datetime.now().strftime("%Y-%m-%d")
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO memoria_perguntas VALUES (?, ?, ?)",
            (pergunta, resposta, data)
        )
        conn.commit()
    except:
        pass
    finally:
        conn.close()


def listar_campos_nao_preenchidos():
    """Imprime no terminal todos os campos problematicos salvos."""
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT titulo_vaga, pergunta, tipo_campo, opcoes, data
        FROM campos_nao_preenchidos
        ORDER BY data DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        print("✅ Nenhum campo nao preenchido registrado.")
        return
    print(f"\n{'='*60}")
    print(f"⚠️  CAMPOS NAO PREENCHIDOS ({len(rows)} registros recentes)")
    print(f"{'='*60}")
    for vaga, pergunta, tipo, opcoes, data in rows:
        print(f"[{data}]  {vaga[:40]}")
        print(f"  Tipo : {tipo}")
        print(f"  Campo: {pergunta[:70]}")
        if opcoes:
            print(f"  Opts : {opcoes[:90]}")
        print()


# ==========================================
# 🛠️ FUNÇÕES DE APOIO
# ==========================================
async def human_delay(a=1.5, b=3.5):
    await asyncio.sleep(random.uniform(a, b))


def enviar_telegram(msg):
    if not TELEGRAM_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🤖 AutoApply:\n\n{msg}"},
            timeout=5,
        )
    except:
        pass


async def rolar_lista_de_vagas(page):
    try:
        painel_vagas = page.locator(".jobs-search-results-list")
        if await painel_vagas.is_visible():
            for _ in range(3):
                await painel_vagas.evaluate("el => el.scrollBy(0, 1000)")
                await asyncio.sleep(1)
    except:
        pass


# ==========================================
# 🧠 CÉREBRO DA IA — 5 camadas
# ==========================================
# Contexto da vaga atual (usado no log de falhas)
_vaga_atual = {"id": "", "titulo": ""}


async def perguntar_para_ia(pergunta, descricao, opcoes=None, tipo_campo="input"):
    if not client:
        print("❌ ERRO FATAL: Cliente Gemini nao carregado.")
        return None

    pergunta_limpa = str(pergunta).split('\n')[0].strip()
    p_lower = pergunta_limpa.lower()

    # --- CAMADA 1: Hardcode ---
    if "first name" in p_lower or "primeiro nome" in p_lower:
        return "Pablo"
    if "last name" in p_lower or "sobrenome" in p_lower:
        return "Lima"
    if "e-mail" in p_lower or "email" in p_lower:
        return "pablolima83352@gmail.com"
    # Telefone só quando não for código de país
    if any(t in p_lower for t in ["phone", "celular", "telefone"]):
        if not any(x in p_lower for x in ["country", "código", "code", "ddi"]):
            return "13991560814"

    # --- CAMADA 2: Interpretador local ---
    resposta_local = interpretar_pergunta_local(p_lower, opcoes)
    if resposta_local:
        print(f"   🟢 [LOCAL] → {resposta_local}")
        return resposta_local

    # --- CAMADA 3: Memória SQLite ---
    resposta_salva = buscar_resposta_salva(pergunta_limpa)
    if resposta_salva:
        print(f"   💾 [MEM]   → {resposta_salva}")
        return resposta_salva

    # --- CAMADA 4: Cache RAM ---
    chave = f"{pergunta_limpa}_{str(opcoes)}"
    if chave in cache_respostas:
        return cache_respostas[chave]

    # --- CAMADA 5: Gemini (último recurso) ---
    print(f"   🤖 [GEMINI] → {pergunta_limpa[:55]}...")

    contexto_opcoes = f"\nOPÇÕES (Escolha uma): {', '.join(opcoes)}" if opcoes else ""

    prompt = f"""
Você é o assistente de carreira do Pablo Lima.
PERFIL: {MEU_PERFIL_RESUMIDO}

PERGUNTA DO FORMULÁRIO: "{pergunta_limpa}" {contexto_opcoes}

REGRAS:
1. Responda APENAS o que foi pedido, sem explicações adicionais.
2. Escolha a resposta que MAXIMIZA as chances de avançar no processo.
3. Evite respostas negativas a menos que seja absolutamente necessário.
4. Localização → "Santos, SP, Brazil"
5. Remoto/Híbrido → "Sim"
6. Inglês → "Advanced" | Espanhol → "Advanced"
7. Salário CLT → "3500" | PJ → "5500"
8. "Are you authorized to work?" → "Yes"
9. "Do you need visa sponsorship?" → "No"
10. Skills no perfil → "Sim" | Skills similares → "Sim" | Skills ausentes → "Não"
11. Perguntas abertas → resposta curta (1-2 linhas) focada em automação + eficiência.
12. Anos de experiência → use o maior número realista sem mentir.
13. Disponibilidade para locomoção/deslocamento → "Sim"
14. CPF: 49811427810
15. Link Linkedin: https://www.linkedin.com/in/pablo-lima-aaba02269/

RESPOSTA:
"""

    tentativas = 0
    while tentativas < 3:
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            resposta = response.text.strip()

            if any(t in p_lower for t in ["anos", "quantos", "years", "experience"]):
                nums = re.findall(r'\d+', resposta)
                resposta = nums[0] if nums else "1"

            cache_respostas[chave] = resposta
            salvar_resposta_na_memoria(pergunta_limpa, resposta)
            return resposta

        except Exception as e:
            erro_str = str(e)
            if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                print(f"   ⏳ Cota atingida. Pausando 40s... ({tentativas + 1}/3)")
                await asyncio.sleep(40)
                tentativas += 1
            else:
                print(f"   ❌ Erro API: {erro_str}")
                registrar_campo_nao_preenchido(
                    _vaga_atual["id"], _vaga_atual["titulo"],
                    pergunta_limpa, tipo_campo, opcoes
                )
                return None

    print(f"   ❌ Cota esgotada. Campo registrado como nao preenchido.")
    registrar_campo_nao_preenchido(
        _vaga_atual["id"], _vaga_atual["titulo"],
        pergunta_limpa, tipo_campo, opcoes
    )
    return None


# ==========================================
# 📍 ANÁLISE DE LOCALIZAÇÃO DA VAGA
# ==========================================
async def analisar_local_vaga(page):
    try:
        header_text = await page.locator(
            ".job-details-jobs-unified-top-card__primary-description-container"
        ).inner_text()
        header_lower = header_text.lower()

        is_remoto  = any(x in header_lower for x in ["remoto", "home office", "remote"])
        is_hibrido = any(x in header_lower for x in ["híbrido", "hybrid"])
        is_sp      = any(x in header_lower for x in ["são paulo", " sp", ", sp", "santos"])

        if not is_remoto and not is_hibrido and not is_sp:
            return False, f"Presencial fora de SP ({header_text.strip()[:60]})"
        return True, "Localização OK"
    except:
        return True, "Localização ignorada"


# ==========================================
# 🤖 PREENCHEDOR DE FORMULÁRIOS
# ==========================================
async def responder_formulario(page, descricao):
    try:
        modal = page.locator("[role='dialog']").last
        if not await modal.is_visible():
            return

        seletores = (
            "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), "
            "textarea, select, [role='combobox'], [role='textbox']"
        )
        campos = await modal.locator(seletores).all()

        for campo in campos:
            if not await campo.is_visible() or not await campo.is_enabled():
                continue

            await campo.evaluate("el => el.style.border = '3px solid yellow'")

            pergunta = (
                await campo.get_attribute("aria-label")
                or await campo.get_attribute("placeholder")
                or ""
            )
            p_id = await campo.get_attribute("id")

            if not pergunta and p_id:
                label = page.locator(f"label[for='{p_id}']")
                if await label.count() > 0:
                    pergunta = await label.inner_text()

            if not pergunta:
                pergunta = await campo.evaluate("""el => {
                    let container = el.closest(
                        '.jobs-easy-apply-form-section__grouping, .fb-dash-form-element'
                    );
                    if (container) return container.innerText.split('\\n')[0];
                    let prev = el.previousElementSibling;
                    if (prev) return prev.innerText;
                    return '';
                }""")

            pergunta = pergunta.strip()
            if len(pergunta) < 2:
                await campo.evaluate("el => el.style.border = ''")
                continue

            print(f"🔎 [{pergunta[:60]}]")

            tag  = await campo.evaluate("el => el.tagName")
            role = await campo.get_attribute("role")

            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

            # --- SELECT nativo ---
            if tag == "SELECT":
                opcoes = await campo.locator("option").all_inner_texts()
                opcoes = [o.strip() for o in opcoes if o.strip() and "selecione" not in o.lower()]
                resposta = await perguntar_para_ia(pergunta, descricao, opcoes, tipo_campo="select")
                if resposta:
                    try:
                        await campo.select_option(label=resposta)
                    except:
                        try:
                            await campo.select_option(value=resposta)
                        except:
                            print(f"   ⚠️  SELECT falhou para: {resposta}")
                            registrar_campo_nao_preenchido(
                                _vaga_atual["id"], _vaga_atual["titulo"],
                                pergunta, "select", opcoes
                            )
                else:
                    registrar_campo_nao_preenchido(
                        _vaga_atual["id"], _vaga_atual["titulo"],
                        pergunta, "select", opcoes
                    )

            # --- COMBOBOX dinâmico ---
            elif role == "combobox":
                await campo.click(force=True)
                await asyncio.sleep(1)

                opcoes_locator = modal.locator("[role='option']")
                opcoes = await opcoes_locator.all_inner_texts()
                opcoes = [o.strip() for o in opcoes if o.strip()]

                resposta = await perguntar_para_ia(pergunta, descricao, opcoes, tipo_campo="combobox")
                if resposta:
                    try:
                        opcao_alvo = opcoes_locator.filter(has_text=resposta).first
                        await opcao_alvo.click(force=True)
                    except:
                        try:
                            await campo.fill(str(resposta))
                            await asyncio.sleep(0.5)
                            await page.keyboard.press("ArrowDown")
                            await page.keyboard.press("Enter")
                        except:
                            print(f"   ⚠️  COMBOBOX falhou para: {resposta}")
                            registrar_campo_nao_preenchido(
                                _vaga_atual["id"], _vaga_atual["titulo"],
                                pergunta, "combobox", opcoes
                            )
                else:
                    registrar_campo_nao_preenchido(
                        _vaga_atual["id"], _vaga_atual["titulo"],
                        pergunta, "combobox", opcoes
                    )

            # --- INPUT / TEXTAREA ---
            else:
                valor_atual = await campo.input_value()
                if not valor_atual:
                    resposta = await perguntar_para_ia(pergunta, descricao, tipo_campo="input")
                    if resposta:
                        await campo.click(force=True)
                        await campo.focus()
                        await page.keyboard.type(str(resposta), delay=50)
                    else:
                        registrar_campo_nao_preenchido(
                            _vaga_atual["id"], _vaga_atual["titulo"],
                            pergunta, "input"
                        )

            await campo.evaluate("el => el.style.border = ''")

        # --- RÁDIOS (fieldset) ---
        fieldsets = await modal.locator("fieldset").all()
        for fs in fieldsets:
            if not await fs.is_visible():
                continue
            try:
                legend_el = fs.locator("legend").first
                if await legend_el.count() > 0:
                    legend = await legend_el.inner_text()
                else:
                    legend = await fs.locator("span").first.inner_text()

                legend = legend.strip()
                if len(legend) < 2:
                    continue

                print(f"🔘 [{legend[:60]}]")

                labels_radios = await fs.locator("label").all_inner_texts()
                labels_radios = [l.strip() for l in labels_radios if l.strip()]

                resposta = await perguntar_para_ia(
                    legend, descricao, labels_radios, tipo_campo="radio"
                )

                if resposta:
                    botao = fs.locator(f"label:has-text('{resposta}')")
                    if await botao.count() > 0:
                        await botao.first.click(force=True)
                        print(f"   ✅ Rádio: {resposta}")
                    else:
                        radio_input = fs.locator(f"input[type='radio'][value='{resposta}']")
                        if await radio_input.count() > 0:
                            await radio_input.first.click(force=True)
                            print(f"   ✅ Rádio (valor): {resposta}")
                        else:
                            print(f"   ⚠️  Rádio nao encontrado: {resposta}")
                            registrar_campo_nao_preenchido(
                                _vaga_atual["id"], _vaga_atual["titulo"],
                                legend, "radio", labels_radios
                            )
                else:
                    registrar_campo_nao_preenchido(
                        _vaga_atual["id"], _vaga_atual["titulo"],
                        legend, "radio", labels_radios
                    )
            except Exception as e:
                print(f"   ⚠️  Erro no fieldset: {e}")

    except Exception as e:
        print(f"⚠️ Erro ao preencher form: {e}")


# ==========================================
# 🚀 FLUXO DE CANDIDATURA
# ==========================================
async def aplicar(page):
    try:
        vaga_ok, motivo_local = await analisar_local_vaga(page)
        if not vaga_ok:
            return "PULO", motivo_local

        descricao = await page.locator("#job-details").inner_text()

        botao = page.locator(".jobs-apply-button").first
        if not await botao.is_visible():
            return "PULO", "Sem botão Simplificada"

        await botao.click()

        for _ in range(6):
            await human_delay(2, 3)
            await responder_formulario(page, descricao)

            botoes_enviar = ["Enviar candidatura", "Submit application"]
            for texto in botoes_enviar:
                btn_send = (
                    page.get_by_role("button", name=texto, exact=False)
                    .filter(has_text=texto)
                )
                if await btn_send.is_visible() and await btn_send.is_enabled():
                    await btn_send.click()
                    await human_delay(2, 3)
                    await page.keyboard.press("Escape")
                    return "SUCESSO", "Candidatura enviada"

            botoes_next = ["Avançar", "Próximo", "Next", "Review", "Revisar", "Continuar"]
            clicou_avancar = False
            for texto in botoes_next:
                btn_next = (
                    page.get_by_role("button", name=texto, exact=False)
                    .filter(has_text=texto)
                )
                if await btn_next.is_visible() and await btn_next.is_enabled():
                    await btn_next.click()
                    clicou_avancar = True
                    break

            if clicou_avancar:
                continue
            break

        await page.keyboard.press("Escape")
        try:
            await page.get_by_role("button", name="Descartar").click()
        except:
            pass
        return "PULO", "Fluxo incompleto ou travado"

    except Exception as e:
        return "ERRO", str(e)


# ==========================================
# ⚙️ EXECUTOR PRINCIPAL
# ==========================================
async def main():
    iniciar_db()

    # Para ver campos problemáticos das últimas execuções, descomente:
    # listar_campos_nao_preenchidos(); return

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await browser.new_page()

        try:
            if hasattr(playwright_stealth, "stealth_async"):
                await playwright_stealth.stealth_async(page)
            else:
                playwright_stealth.stealth_sync(page)
        except:
            pass

        await page.goto("https://www.linkedin.com/jobs")
        if "login" in page.url or await page.locator('button:has-text("Entrar")').is_visible():
            input("⚠️ FAÇA LOGIN NO NAVEGADOR E PRESSIONE ENTER AQUI...")

        for termo in TERMOS_BUSCA:
            for pagina in range(MAX_PAGINAS):
                offset = pagina * 25
                print(f"\n{'='*60}")
                print(f"🔎 TERMO: {termo} | PÁGINA: {pagina + 1}/{MAX_PAGINAS}")
                print(f"{'='*60}")

                url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={termo}&f_TPR=r86400&f_AL=true&f_E=2%2C3&start={offset}"
                )
                await page.goto(url)
                await human_delay(4, 6)

                await rolar_lista_de_vagas(page)
                vagas = await page.locator(".job-card-container--clickable").all()

                if not vagas:
                    print("📭 Fim das vagas para este termo.")
                    break

                print(f"📋 {len(vagas)} vagas encontradas.")

                for i in range(len(vagas)):
                    try:
                        id_vaga = await vagas[i].get_attribute("data-job-id")

                        if vaga_ja_processada(id_vaga):
                            print(f"⏭️  [CACHE] {id_vaga}")
                            continue

                        await vagas[i].click()
                        await human_delay(2, 3)

                        try:
                            titulo = await page.locator("h1").inner_text()
                        except:
                            titulo = "Vaga"

                        # Atualiza contexto para log de falhas
                        _vaga_atual["id"]     = id_vaga or ""
                        _vaga_atual["titulo"] = titulo

                        print(f"\n📌 {titulo[:55]}")

                        status, motivo = await aplicar(page)
                        icone = "✅" if status == "SUCESSO" else "⏭️ " if status == "PULO" else "❌"
                        print(f"{icone} [{status}] {motivo}")

                        registrar_no_db(id_vaga, titulo, termo, status, page.url)

                        if status == "SUCESSO":
                            enviar_telegram(f"✅ Nova Candidatura!\nVaga: {titulo}\nTermo: {termo}")

                        await human_delay(3, 5)

                    except Exception as e:
                        print(f"⚠️ Erro no loop: {e}")

        print(f"\n{'='*60}")
        print("✅ CICLO FINALIZADO!")

        # Exibe resumo de campos problematicos ao final da execução
        listar_campos_nao_preenchidos()

        enviar_telegram("🏁 O AutoApply concluiu as buscas com sucesso!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())