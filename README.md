<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Playwright-2496ED?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/Gemini_AI-8E75B2?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow?style=for-the-badge" alt="Status">
</p>

<h1 align="center">🤖 AutoApply-LinkedIn (V7.0 PRO)</h1>

<p align="center">
  <strong>Hiperautomação de Candidaturas com Motor de Decisão de 5 Camadas e IA Generativa</strong>
</p>

---

### 📝 Sobre o Projeto
O **AutoApply-LinkedIn** evoluiu de um simples script para uma solução robusta de RPA (Robotic Process Automation). O projeto agora utiliza uma arquitetura de **Hiperautomação**, integrando o **Google Gemini AI** a um motor de regras local. O grande diferencial é a eficiência de custos: o bot prioriza o processamento local e a memória de banco de dados antes de consumir tokens de IA.

> **Diferencial:** Implementação de uma arquitetura baseada em FinOps, reduzindo em até 80% o consumo de API externa através de heurísticas e persistência em SQLite.

---

### ✨ Funcionalidades Principais

* **🧠 Motor de 5 Camadas:** Priorização de respostas: (1) Hardcode -> (2) Heurística Local -> (3) Memória SQLite -> (4) Cache RAM -> (5) Gemini AI.
* **💾 Memória de Elefante (SQLite):** O bot nunca pergunta a mesma coisa duas vezes. Ele armazena cada decisão e resposta em um banco de dados relacional permanente.
* **📍 Geofencing Inteligente:** Triagem automática que ignora vagas 100% presenciais fora da região de Santos ou São Paulo (SP).
* **⚖️ Lógica de Regimes:** Diferenciação automática de pretensão salarial para regimes CLT (R$ 3.500) e PJ (R$ 5.500).
* **🛡️ Stealth Architecture:** Bypass de detecção de bots com simulação de movimentos de mouse e atrasos humanos variáveis.
* **📢 Telegram Alerts:** Notificações em tempo real diretamente no seu celular para cada candidatura realizada com sucesso.

---

### 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python 3.11+
* **Inteligência Artificial:** Google Gemini 1.5 Flash (via GenerativeAI SDK)
* **Engine de Automação:** Playwright (Async) & Playwright-Stealth
* **Persistência de Dados:** SQLite 3
* **Notificações:** Telegram Bot API

---

### 🚀 Como Configurar e Rodar

1. **Instale as dependências:**
   ```bash
   pip install playwright playwright-stealth google-generativeai python-dotenv requests
   playwright install chromium
