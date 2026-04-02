<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Playwright-2496ED?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow?style=for-the-badge" alt="Status">
</p>

<h1 align="center">🤖 AutoApply-LinkedIn</h1>

<p align="center">
  <strong>Solução de RPA Inteligente para Candidaturas Estratégicas no LinkedIn</strong>
</p>

---

### 📝 Sobre o Projeto
O **AutoApply-LinkedIn** não é apenas um disparador de currículos. É uma ferramenta de automação (RPA) desenvolvida para agir como um assistente pessoal na busca por vagas. Ele interpreta perguntas, filtra localizações indesejadas e gerencia exceções de forma autônoma.

> **Diferencial:** O bot possui uma lógica de "Fila de Auditoria", garantindo que você nunca perca uma oportunidade por causa de formulários complexos.

---

### ✨ Funcionalidades Principais

* **🧠 Cérebro Interpretador:** Preenchimento inteligente de anos de experiência, pretensão salarial e níveis de idioma.
* **📍 Geofencing de Vagas:** Triagem automática para evitar vagas 100% presenciais fora do estado de São Paulo (SP).
* **⚖️ Lógica Financeira:** Diferenciação de valores para regimes CLT e PJ automaticamente.
* **🛡️ Stealth Architecture:** Navegação furtiva para proteção da conta e simulação de comportamento humano.
* **📋 Dead Letter Queue (DLQ):** Registro automático de vagas pendentes no arquivo `vagas_pendentes.csv`.

---

### 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python 3.14
* **Engine:** Playwright (Async)
* **Segurança:** Playwright-Stealth
* **Dados:** CSV / Logs Estruturados

---

### 🚀 Como Configurar e Rodar

1. **Instale as dependências:**
   ```bash
   pip install playwright playwright-stealth
   playwright install chromium
