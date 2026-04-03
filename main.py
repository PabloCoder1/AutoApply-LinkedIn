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

# Carrega as chaves do arquivo .env
load_dotenv()

# ==========================================
# ⚙️ CONFIGURAÇÕES PRINCIPAIS
# ==========================================
TERMOS_BUSCA = ["RPA", "Python Junior", "Automação"]
USER_DATA_DIR = "./linkedin_session"
MAX_PAGINAS = 3 # Lê até 75 vagas por termo (3 páginas de 25)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Memória de curto prazo
cache_respostas = {}

# ==========================================
# 📍 SEU PERFIL (A base da IA)
# ==========================================
MEU_PERFIL_RESUMIDO = """
Nome: Pablo Lima. 
E-mail: pablolima83352@gmail.com
Código do país: +55
Número de celular: 13991560814
Currículo: Pablo Lima dos Santos.pdf
Cargo: Analista Junior de Sistemas e RPA.
Skills: Python (2 anos), React (1 ano), Node.js (1 ano), C#/.NET (2 anos), SQL, Git.
Local: Santos, SP (Disponibilidade para Híbrido em SP ou Remoto).
Inglês: Avançado. Espanhol: Avançado.
Pretensão: CLT 3500, PJ 5500. CNH: Sim.
Experiência corporativa: Trabalhou na Vivo (Telefónica).
"""

# ==========================================
# 🗄️ SISTEMA DE MEMÓRIA (SQLite)
# ==========================================
def iniciar_db():
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    # Tabela 1: Vagas processadas
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
    # Tabela 2: Memória Permanente de Perguntas (Economia de API)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memoria_perguntas (
            pergunta_limpa TEXT PRIMARY KEY,
            resposta TEXT,
            data_criacao TEXT
        )
    """)
    conn.commit()
    conn.close()

def vaga_ja_processada(id_vaga):
    if not id_vaga: return False
    conn = sqlite3.connect("dados_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM candidaturas WHERE id_vaga = ?", (id_vaga,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None

def registrar_no_db(id_vaga, titulo, termo, status, link):
    if not id_vaga: return
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
    except: pass
    finally: conn.close()

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
        cursor.execute("INSERT OR REPLACE INTO memoria_perguntas VALUES (?, ?, ?)", (pergunta, resposta, data))
        conn.commit()
    except: pass
    finally: conn.close()

# ==========================================
# 🛠️ FUNÇÕES DE APOIO
# ==========================================
async def human_delay(a=1.5, b=3.5):
    await asyncio.sleep(random.uniform(a, b))

def enviar_telegram(msg):
    if not TELEGRAM_TOKEN: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🤖 AutoApply:\n\n{msg}"},
            timeout=5
        )
    except: pass

async def rolar_lista_de_vagas(page):
    try:
        painel_vagas = page.locator(".jobs-search-results-list")
        if await painel_vagas.is_visible():
            for _ in range(3): 
                await painel_vagas.evaluate("el => el.scrollBy(0, 1000)")
                await asyncio.sleep(1)
    except: pass

# ==========================================
# 🧠 CÉREBRO DA IA (Gestão de Cota + SQLite)
# ==========================================
async def perguntar_para_ia(pergunta, descricao, opcoes=None):
    if not client: 
        print("❌ ERRO FATAL: Cliente Gemini não carregado.")
        return None

    pergunta_limpa = str(pergunta).split('\n')[0].strip()
    p_lower = pergunta_limpa.lower()

    # 1. Filtro de Hardcode (Respostas óbvias sem gastar API)
    if "first name" in p_lower or "primeiro nome" in p_lower: return "Pablo"
    if "last name" in p_lower or "sobrenome" in p_lower: return "Lima"
    if "e-mail" in p_lower or "email" in p_lower: return "pablolima83352@gmail.com"
    if "phone" in p_lower or "celular" in p_lower or "telefone" in p_lower: return "13991560814"

    # 2. Busca na Memória SQLite (Nunca pergunta a mesma coisa duas vezes)
    resposta_salva = buscar_resposta_salva(pergunta_limpa)
    if resposta_salva:
        print(f"💾 [MEMÓRIA] Usando resposta salva para: {pergunta_limpa[:30]}...")
        return resposta_salva

    # 3. Busca no Cache de Memória RAM (Sessão atual)
    chave = f"{pergunta_limpa}_{str(opcoes)}"
    if chave in cache_respostas:
        return cache_respostas[chave]

    contexto_opcoes = f"\nOPÇÕES (Escolha uma): {', '.join(opcoes)}" if opcoes else ""

    prompt = f"""
    Você é o assistente de carreira do Pablo Lima.
    PERFIL: {MEU_PERFIL_RESUMIDO}
    
    PERGUNTA DO FORMULÁRIO: "{pergunta_limpa}" {contexto_opcoes}
    
    REGRAS CRÍTICAS:
    1. Se perguntar de "Location", "País" ou "Onde você mora", responda: "Brasil (+55)" ou "Santos, SP, Brazil" dependendo das opções.
    2. Se for sobre multinacional, responda 'Sim'.
    3. Se for salário, aceite se for maior ou igual a 3500.
    4. Responda APENAS o necessário. Nada de enrolação.
    
    RESPOSTA:"""
    
    tentativas = 0
    while tentativas < 3: 
        try:
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            resposta = response.text.strip()
            
            if any(t in p_lower for t in ["anos", "quantos", "years", "experience"]):
                nums = re.findall(r'\d+', resposta)
                resposta = nums[0] if nums else "1"

            # Salva nas memórias para o futuro
            cache_respostas[chave] = resposta
            salvar_resposta_na_memoria(pergunta_limpa, resposta)
            
            return resposta
            
        except Exception as e:
            erro_str = str(e)
            if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                print(f"⏳ Cota atingida! Pausando por 40 segundos... (Tentativa {tentativas + 1}/3)")
                await asyncio.sleep(40)
                tentativas += 1
            else:
                print(f"❌ ERRO REAL DA API: {erro_str}")
                return None 
                
    return None 

async def analisar_local_vaga(page):
    try:
        header_text = await page.locator(".job-details-jobs-unified-top-card__primary-description-container").inner_text()
        header_lower = header_text.lower()

        is_remoto = any(x in header_lower for x in ["remoto", "home office", "remote"])
        is_hibrido = any(x in header_lower for x in ["híbrido", "hybrid"])
        is_sp = any(x in header_lower for x in ["são paulo", " sp", ", sp"])

        if not is_remoto and not is_hibrido and not is_sp:
            return False, f"Presencial fora de SP ({header_text.strip()})"
        return True, "Localização OK"
    except: return True, "Localização ignorada"

# ==========================================
# 🤖 PREENCHEDOR DE FORMULÁRIOS PRO
# ==========================================
async def responder_formulario(page, descricao):
    try:
        # Foco exclusivo no Modal da candidatura
        modal = page.locator("[role='dialog']").last
        if not await modal.is_visible():
            return 

        seletores = "input:not([type='hidden']):not([type='checkbox']):not([type='radio']), textarea, select, [role='combobox'], [role='textbox']"
        campos = await modal.locator(seletores).all()
        
        for campo in campos:
            if not await campo.is_visible() or not await campo.is_enabled(): continue
            
            await campo.evaluate("el => el.style.border = '3px solid yellow'")

            pergunta = await campo.get_attribute("aria-label") or await campo.get_attribute("placeholder") or ""
            p_id = await campo.get_attribute("id")
            
            if not pergunta and p_id:
                label = page.locator(f"label[for='{p_id}']")
                if await label.count() > 0:
                    pergunta = await label.inner_text()

            if not pergunta:
                pergunta = await campo.evaluate("""el => {
                    let container = el.closest('.jobs-easy-apply-form-section__grouping, .fb-dash-form-element');
                    if (container) return container.innerText.split('\\n')[0];
                    let prev = el.previousElementSibling;
                    if (prev) return prev.innerText;
                    return '';
                }""")

            pergunta = pergunta.strip()
            if len(pergunta) < 2: 
                await campo.evaluate("el => el.style.border = ''")
                continue

            print(f"🔎 Analisando: {pergunta[:45]}...")

            tag = await campo.evaluate("el => el.tagName")
            role = await campo.get_attribute("role")

            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

            if tag == "SELECT":
                opcoes = await campo.locator("option").all_inner_texts()
                opcoes = [o.strip() for o in opcoes if o.strip() and "selecione" not in o.lower()]
                resposta = await perguntar_para_ia(pergunta, descricao, opcoes)
                if resposta:
                    print(f"🧠 Bot preencheu: {resposta}")
                    try: await campo.select_option(label=resposta)
                    except: pass

            elif role == "combobox":
                await campo.click(force=True)
                await asyncio.sleep(1)
                
                opcoes_locator = modal.locator("[role='option']")
                opcoes = await opcoes_locator.all_inner_texts()
                opcoes = [o.strip() for o in opcoes if o.strip()]
                
                resposta = await perguntar_para_ia(pergunta, descricao, opcoes)
                if resposta:
                    print(f"🧠 Bot preencheu: {resposta}")
                    try:
                        opcao_alvo = opcoes_locator.filter(has_text=resposta).first
                        await opcao_alvo.click(force=True)
                    except:
                        try:
                            await campo.fill(str(resposta))
                            await asyncio.sleep(0.5)
                            await page.keyboard.press("ArrowDown")
                            await page.keyboard.press("Enter")
                        except: pass
            
            else:
                if not await campo.input_value():
                    resposta = await perguntar_para_ia(pergunta, descricao)
                    if resposta:
                        print(f"🧠 Bot digitou: {resposta}")
                        await campo.click(force=True)
                        await campo.focus()
                        await page.keyboard.type(str(resposta), delay=50)

            await campo.evaluate("el => el.style.border = ''")

        # Rádios (Sim/Não) 
        fieldsets = await modal.locator("fieldset").all()
        for fs in fieldsets:
            if not await fs.is_visible(): continue
            try:
                legend = await fs.locator("legend, span").first.inner_text()
                resposta = await perguntar_para_ia(legend, descricao)
                if resposta:
                    print(f"🧠 Bot escolheu Rádio: {resposta}")
                    botao = fs.locator(f"label:has-text('{resposta}')")
                    if await botao.count() > 0: await botao.first.click(force=True)
            except: pass

    except Exception as e:
        print(f"⚠️ Erro ao preencher form: {e}")

# ==========================================
# 🚀 FLUXO DE CANDIDATURA
# ==========================================
async def aplicar(page):
    try:
        vaga_ok, motivo_local = await analisar_local_vaga(page)
        if not vaga_ok: return "PULO", motivo_local

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
                btn_send = page.get_by_role("button", name=texto, exact=False).filter(has_text=texto)
                if await btn_send.is_visible() and await btn_send.is_enabled():
                    await btn_send.click()
                    await human_delay(2, 3)
                    await page.keyboard.press("Escape") 
                    return "SUCESSO", "Candidatura enviada"

            botoes_next = ["Avançar", "Próximo", "Next", "Review", "Revisar", "Continuar"]
            clicou_avancar = False
            for texto in botoes_next:
                btn_next = page.get_by_role("button", name=texto, exact=False).filter(has_text=texto)
                if await btn_next.is_visible() and await btn_next.is_enabled():
                    await btn_next.click()
                    clicou_avancar = True
                    break
            
            if clicou_avancar: continue
            break 

        await page.keyboard.press("Escape")
        try: await page.get_by_role("button", name="Descartar").click()
        except: pass
        return "PULO", "Fluxo incompleto ou travado"

    except Exception as e:
        return "ERRO", str(e)

# ==========================================
# ⚙️ EXECUTOR PRINCIPAL
# ==========================================
async def main():
    iniciar_db()

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()

        try:
            if hasattr(playwright_stealth, "stealth_async"):
                await playwright_stealth.stealth_async(page)
            else:
                playwright_stealth.stealth_sync(page)
        except: pass

        await page.goto("https://www.linkedin.com/jobs")
        if "login" in page.url or await page.locator('button:has-text("Entrar")').is_visible():
            input("⚠️ FAÇA LOGIN NO NAVEGADOR E PRESSIONE ENTER AQUI...")

        for termo in TERMOS_BUSCA:
            for pagina in range(MAX_PAGINAS):
                offset = pagina * 25
                print(f"\n🔎 BUSCANDO: {termo} | PÁGINA: {pagina+1}")
                
                url = f"https://www.linkedin.com/jobs/search/?keywords={termo}&f_TPR=r86400&f_AL=true&f_E=2%2C3&start={offset}"
                await page.goto(url)
                await human_delay(4, 6)

                await rolar_lista_de_vagas(page)
                vagas = await page.locator(".job-card-container--clickable").all()

                if not vagas:
                    print("📭 Fim das vagas para este termo.")
                    break

                for i in range(len(vagas)):
                    try:
                        id_vaga = await vagas[i].get_attribute("data-job-id")

                        if vaga_ja_processada(id_vaga):
                            print(f"⏭️ [CACHE] Vaga {id_vaga} ignorada (Já processada).")
                            continue

                        await vagas[i].click()
                        await human_delay(2, 3)

                        try: titulo = await page.locator("h1").inner_text()
                        except: titulo = "Vaga"

                        status, motivo = await aplicar(page)
                        print(f"[{status}] {titulo[:40]} -> {motivo}")

                        registrar_no_db(id_vaga, titulo, termo, status, page.url)

                        if status == "SUCESSO":
                            enviar_telegram(f"✅ Nova Candidatura!\nVaga: {titulo}\nTermo: {termo}")

                        await human_delay(3, 5)

                    except Exception as e:
                        print(f"⚠️ Erro no loop de vagas: {e}")

        print("\n✅ CICLO DE BUSCA FINALIZADO!")
        enviar_telegram("🏁 O AutoApply concluiu as buscas com sucesso!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())