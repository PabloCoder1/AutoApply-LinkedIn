import asyncio
import random
import os
import csv
from datetime import datetime
from playwright.async_api import async_playwright
import playwright_stealth

# ==========================================
# ⚙️ CONFIGURAÇÕES PRINCIPAIS E PERFIL
# ==========================================
TERMOS_BUSCA = ["Python", "React", "Node", "C#", "Junior"]
USER_DATA_DIR = "./linkedin_session"
ARQUIVO_PENDENTES = "vagas_pendentes.csv"

MEU_PERFIL = {
    "experiencia_anos": {
        "python": "2", "react": "1", "node": "1", "node.js": "1",
        "javascript": "2", "js": "2", "sql": "1", "mysql": "1",
        "postgres": "1", "c#": "2", "csharp": "2", "dotnet": "2",
        ".net": "2", "html": "2", "css": "2", "tailwind": "1",
        "bootstrap": "1", "api": "1", "rest": "1", "git": "1",
        "docker": "0"
    },
    "anos_padrao": "2",
    "telefone": "13991560814",
    
    "salario_clt": "3500",
    "salario_pj": "5500",

    "idiomas_nivel": {
        "english": "Advanced",
        "inglês": "Avançado",
        "spanish": "Advanced",
        "espanhol": "Avançado"
    },

    "sim_nao": {
        "12x36": "Não", "madrugada": "Não", "noturno": "Não",
        "plantão": "Não", "finais de semana": "Não", "fim de semana": "Não",
        
        "cnh": "Sim", "driver license": "Sim", "driving license": "Sim",
        "carro": "Não", "vehicle": "Não",
        "deficiencia": "Não", "disability": "Não", "pcd": "Não",
        "availability": "Sim", "available": "Sim",
        "travel": "Sim", "relocate": "Sim", "relocation": "Sim",
        "visa": "Sim", "work permit": "Sim", "authorized": "Sim",
        "remote": "Sim", "home office": "Sim", "on-site": "Não", 
        "onsite": "Não", "presencial": "Não", "hybrid": "Sim",
        "background check": "Sim", "criminal record": "Não",
        "degree": "Sim", "bachelor": "Sim", "college": "Sim", "university": "Sim",
        "locomover": "Sim", "deslocar": "Sim", "deslocamento": "Sim", "commute": "Sim"
    }
}

# ==========================================
# 🛠️ FUNÇÕES BASE E SEGURANÇA
# ==========================================
async def human_delay(min_sec=1.5, max_sec=3.5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def iniciar_navegador(p):
    browser = await p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={'width': 1366, 'height': 768}
    )
    page = browser.pages[0] if browser.pages else await browser.new_page()
    try:
        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
        else:
            playwright_stealth.stealth_sync(page)
    except: pass
    return browser, page

def salvar_vaga_pendente(termo, titulo, link):
    arquivo_existe = os.path.isfile(ARQUIVO_PENDENTES)
    try:
        with open(ARQUIVO_PENDENTES, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            if not arquivo_existe:
                writer.writerow(['Data_Hora', 'Termo_Busca', 'Titulo_Vaga', 'Link_Vaga'])
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([data_hora, termo, titulo, link])
    except Exception as e:
        print(f"⚠️ Erro ao salvar vaga pendente: {e}")

async def analisar_local_vaga(page):
    try:
        await human_delay(1, 2)
        detalhes = await page.locator(".job-details-jobs-unified-top-card__primary-description-container").inner_text()
        detalhes = detalhes.lower()

        is_presencial = "presencial" in detalhes or "on-site" in detalhes
        in_sp = "são paulo" in detalhes or " sp " in detalhes or " sp," in detalhes or ", sp" in detalhes

        if is_presencial and not in_sp:
            return False
            
        return True
    except Exception as e:
        return True

# ==========================================
# 🤖 INTERPRETADOR (O CÉREBRO)
# ==========================================
async def responder_perguntas_dinamicas(page):
    try:
        labels = await page.locator("label").all()
        for label in labels:
            texto_label = await label.inner_text()
            pergunta = texto_label.lower().strip()
            for_attr = await label.get_attribute("for")
            if not for_attr: continue
                
            campo = page.locator(f"#{for_attr}")
            if not await campo.is_visible(): continue
            tag_name = await campo.evaluate("el => el.tagName")
            
            if tag_name == "INPUT":
                if await campo.input_value() == "":
                    if any(word in pergunta for word in ["salário", "pretensão", "salary", "bruto", "gross"]):
                        if "pj" in pergunta or "jurídica" in pergunta or "contract" in pergunta:
                            await campo.fill(MEU_PERFIL["salario_pj"])
                        else:
                            await campo.fill(MEU_PERFIL["salario_clt"])
                            
                    elif "anos" in pergunta or "experiência" in pergunta or "experience" in pergunta:
                        respondido = False
                        for tec, anos in MEU_PERFIL["experiencia_anos"].items():
                            if tec in pergunta:
                                await campo.fill(anos)
                                respondido = True; break
                        if not respondido: await campo.fill(MEU_PERFIL["anos_padrao"])
                        
                    elif "telefone" in pergunta or "phone" in pergunta or "celular" in pergunta:
                        await campo.fill(MEU_PERFIL["telefone"])

            elif tag_name == "SELECT":
                if "inglês" in pergunta or "english" in pergunta or "idioma" in pergunta or "espanhol" in pergunta:
                    for idioma, nivel in MEU_PERFIL["idiomas_nivel"].items():
                        if idioma in pergunta:
                            try: await campo.select_option(label=nivel); break
                            except: pass
                            
                for termo_sim_nao, resposta in MEU_PERFIL["sim_nao"].items():
                    if termo_sim_nao in pergunta:
                        try: await campo.select_option(label=resposta)
                        except: pass

        fieldsets = await page.locator("fieldset").all()
        for fieldset in fieldsets:
            if await fieldset.is_visible():
                pergunta_legend = await fieldset.locator("legend").inner_text()
                pergunta_legend = pergunta_legend.lower().strip()
                for chave, resposta in MEU_PERFIL["sim_nao"].items():
                    if chave in pergunta_legend:
                        botao_resposta = fieldset.locator(f"label:has-text('{resposta}')")
                        if await botao_resposta.is_visible() and not await fieldset.locator(f"input[type='radio']:has-text('{resposta}')").is_checked():
                            await botao_resposta.click()
                        break
    except Exception as e:
        print(f"⚠️ Aviso no Interpretador: {e}")

async def preencher_formulario_dinamico(page):
    tentativas = 0
    while tentativas < 6:
        tentativas += 1
        await human_delay(2, 3)
        await responder_perguntas_dinamicas(page)
        await human_delay(1, 2)

        botoes_proximo = ["Avançar", "Próximo", "Next", "Review", "Revisar", "Continuar", "Continue"]
        clicou = False
        for texto in botoes_proximo:
            botao = page.get_by_role("button", name=texto, exact=False).filter(has_text=texto)
            if await botao.is_visible() and await botao.is_enabled():
                print(f"➡️ Clicando em: {texto}")
                await botao.click()
                clicou = True; break
        if clicou: continue

        botao_enviar = page.get_by_role("button", name="Enviar candidatura", exact=False)
        if await botao_enviar.is_visible() and await botao_enviar.is_enabled():
            print("🎉 Botão FINAL encontrado! Enviando candidatura...")
            await botao_enviar.click()
            await human_delay(3, 5)
            await page.keyboard.press("Escape")
            return True
        break
    return False

async def aplicar_na_vaga_atual(page):
    """
    Retorna uma tupla: (Tipo_Resultado, Mensagem)
    Tipo_Resultado: "SUCESSO", "PULO" (Skip), ou "ERRO"
    """
    try:
        await human_delay(1, 2)
        
        # 1. VERIFICAÇÃO DE VAGA JÁ APLICADA
        # Lemos todo o texto principal da vaga para buscar as flags de "Já aplicado"
        texto_vaga = await page.locator("main").inner_text()
        texto_vaga_lower = texto_vaga.lower()
        
        flags_aplicado = ["candidatura enviada", "você se candidatou", "applied to this job", "candidatou-se"]
        if any(flag in texto_vaga_lower for flag in flags_aplicado):
            return "PULO", "Vaga já aplicada anteriormente"

        # 2. VERIFICAÇÃO DE LOCALIZAÇÃO (Regra de Negócio)
        vaga_valida = await analisar_local_vaga(page)
        if not vaga_valida:
            return "PULO", "Bloqueada por Localização (Presencial fora de SP)"

        # 3. TENTA APLICAR
        botao_candidatura = page.locator(".jobs-apply-button").first
        if await botao_candidatura.is_visible():
            print("\n✨ Iniciando fluxo de candidatura...")
            await botao_candidatura.click()
            sucesso = await preencher_formulario_dinamico(page)
            if sucesso:
                return "SUCESSO", "Candidatura enviada"
            else:
                return "ERRO", "Travou no Formulário"
                
        return "PULO", "Botão 'Candidatura Simplificada' não disponível"
        
    except Exception as e:
        print(f"❌ Erro no fluxo inicial: {e}")
        return "ERRO", f"Erro Técnico: {e}"

# ==========================================
# 🚀 FUNÇÃO PRINCIPAL
# ==========================================
async def main():
    async with async_playwright() as p:
        browser, page = await iniciar_navegador(p)
        
        await page.goto("https://www.linkedin.com/jobs")
        await human_delay(3, 5)
        
        if "login" in page.url or await page.locator('button:has-text("Entrar")').is_visible():
            print("\n" + "="*50)
            print("⚠️  PAUSA PARA LOGIN MANUAL")
            print("1. Faça login na janela do navegador.")
            print("2. Vá até a aba de Vagas.")
            print("3. Volte aqui e pressione ENTER.")
            print("="*50)
            input("Pressione ENTER quando estiver logado... ")

        for termo in TERMOS_BUSCA:
            print(f"\n" + "="*40)
            print(f"🔎 BUSCANDO VAGAS PARA: {termo.upper()}")
            print("="*40)
            url_busca = f"https://www.linkedin.com/jobs/search/?keywords={termo}&f_TPR=r86400&f_E=2%2C3&f_AL=true"
            await page.goto(url_busca)
            await human_delay(4, 6)

            vagas_locators = await page.locator(".job-card-container--clickable").all()

            if not vagas_locators:
                print("⚠️ Nenhuma vaga encontrada para este termo.")
                continue

            print(f"📊 {len(vagas_locators)} vagas encontradas (limitando a 5 por termo para segurança)")

            for i in range(min(len(vagas_locators), 5)):
                try:
                    await vagas_locators[i].click()
                    await human_delay(2, 4)

                    try:
                        titulo_vaga = await page.locator(".job-details-jobs-unified-top-card__job-title").inner_text()
                        titulo_vaga = titulo_vaga.strip()
                    except:
                        titulo_vaga = "Título Indisponível"

                    link_vaga = page.url
                    print(f"\n➡️ [Vaga {i+1}] {titulo_vaga}")

                    await page.mouse.wheel(0, random.randint(200, 600))
                    await human_delay(1, 2)

                    # A MÁGICA DO ROTEAMENTO DE RESULTADOS AQUI:
                    status, motivo = await aplicar_na_vaga_atual(page)

                    if status == "SUCESSO":
                        print("✅ SUCESSO: Candidatura enviada com sucesso!")
                        
                    elif status == "PULO":
                        print(f"🟡 SKIP: {motivo} (Não será salva no CSV)")
                        
                    elif status == "ERRO":
                        print(f"🔴 FALHA: {motivo} | 📝 Salvando para análise manual no CSV...")
                        salvar_vaga_pendente(termo, titulo_vaga, link_vaga)
                        
                        # Limpa a tela fechando modais se o bot travou
                        await page.keyboard.press("Escape")
                        await human_delay(1, 2)
                        botao_descartar = page.get_by_role("button", name="Descartar", exact=False)
                        if await botao_descartar.is_visible():
                            await botao_descartar.click()

                    await human_delay(4, 8)

                except Exception as e:
                    print(f"❌ Erro fatal na vaga {i}: {e}")
                    continue

        print("\n✅ Ciclo finalizado com sucesso.")
        print(f"📁 Verifique '{ARQUIVO_PENDENTES}' APENAS para os formulários que o bot não soube preencher.")
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário.")