# ===========================
# 📦 IMPORTAÇÕES
# ===========================
import os
import time
import logging
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv

load_dotenv()

# ===========================
# 🔧 CONFIGURAÇÕES
# ===========================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
LOCAL = os.getenv("LOCAL", "Salvador, BA")

# ===========================
# 📝 CONFIGURAÇÃO DE LOGS
# ===========================
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def log_info(message): logging.info(f"📝 {message}")
def log_error(message): logging.error(f"❌ {message}")
def log_success(message): logging.info(f"✅ {message}")

# ===========================
# 🛠️ CONFIGURAÇÃO CHROME
# ===========================

def setup_chrome():
    """Configuração para Chromium"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Especifica usar Chromium
    options.binary_location = "/usr/bin/chromium-browser"
    
    return options

def buscar_vagas_indeed():
    log_info("🌐 Buscando no Indeed...")
    driver = None
    
    try:
        options = setup_chrome()
        driver = webdriver.Chrome(options=options)
        
        url = f"https://br.indeed.com/jobs?q=desenvolvedor+OR+programador+OR+TI&l={LOCAL.replace(' ', '+')}"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(5)
        
        vagas = driver.find_elements(By.CSS_SELECTOR, "a.jcs-JobTitle")
        log_info(f"🔍 {len(vagas)} vagas encontradas")
        
        resultados = []
        for job in vagas[:5]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                if titulo and link and any(termo in titulo.lower() for termo in ['ti', 'desenvolvedor', 'programador', 'analista']):
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"✅ {titulo}")
            except:
                continue
                
        return resultados
        
    except Exception as e:
        log_error(f"Erro Indeed: {e}")
        return []
    finally:
        if driver:
            driver.quit()


# ===========================
# 🔍 BUSCA GLASSDOOR
# ===========================
def buscar_vagas_glassdoor():
    log_info("🌐 Buscando no Glassdoor...")
    driver = None
    
    try:
        options = setup_chrome()
        driver = webdriver.Chrome(options=options)
        
        url = f"https://www.glassdoor.com.br/Vaga/desenvolvedor-programador-TI-vagas-{LOCAL.replace(' ', '-')}-SRCH_KO0,25.htm"
        log_info(f"🔗 {url}")
        
        driver.get(url)
        time.sleep(5)
        
        # Seletores simples
        seletores = ["[data-test='job-link']", "a.jobLink", ".job-title"]
        vagas = []
        
        for seletor in seletores:
            try:
                vagas = driver.find_elements(By.CSS_SELECTOR, seletor)
                if vagas:
                    log_info(f"🔍 {len(vagas)} com {seletor}")
                    break
            except:
                continue
        
        resultados = []
        for job in vagas[:5]:
            try:
                titulo = job.text.strip()[:80]
                link = job.get_attribute("href")
                if titulo and link:
                    if link.startswith('/'):
                        link = f"https://www.glassdoor.com.br{link}"
                    resultados.append(f"**{titulo}**\n{link}")
                    log_success(f"✅ {titulo}")
            except:
                continue
                
        return resultados
        
    except Exception as e:
        log_error(f"Erro Glassdoor: {e}")
        return []
    finally:
        if driver:
            driver.quit()

# ===========================
# 🚀 ENVIAR DISCORD
# ===========================
def enviar_discord(vagas):
    if not vagas or not DISCORD_WEBHOOK_URL:
        log_info("📭 Nenhuma vaga para enviar")
        return
        
    mensagem = "🎯 **Vagas de TI Encontradas**\n\n" + "\n\n".join(vagas[:5])
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": mensagem}, timeout=10)
        log_success("📤 Mensagem enviada!")
    except Exception as e:
        log_error(f"Erro Discord: {e}")

# ===========================
# 🧠 FUNÇÃO PRINCIPAL
# ===========================
def main():
    setup_logging()
    log_info("🚀 Iniciando busca...")
    
    if not DISCORD_WEBHOOK_URL:
        log_error("❌ Discord webhook não configurado")
        return
    
    # Busca em ambas as plataformas
    vagas_indeed = buscar_vagas_indeed()
    vagas_glassdoor = buscar_vagas_glassdoor()
    
    # Combina resultados
    todas_vagas = vagas_indeed + vagas_glassdoor
    
    if todas_vagas:
        log_success(f"🎯 {len(todas_vagas)} vagas encontradas")
        enviar_discord(todas_vagas)
    else:
        log_info("📭 Nenhuma vaga encontrada")
    
    log_success("🏁 Concluído!")

if __name__ == "__main__":
    main()

