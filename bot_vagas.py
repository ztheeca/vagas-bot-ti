# ===========================
# 📦 IMPORTAÇÕES
# ===========================
import os
import time
import random
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

# 🧠 Selenium para busca no Indeed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_chrome_github_actions():
    """Configuração específica para GitHub Actions"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")
    
    # User agent para Linux
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return options

# Carrega variáveis do arquivo .env
load_dotenv()

# ===========================
# 🔧 CONFIGURAÇÕES
# ===========================

# Webhook do Discord
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
# Local padrão
LOCAL = os.getenv("LOCAL", "Salvador, BA")

# Configurações do .env
MAX_VAGAS_POR_PLATAFORMA = int(os.getenv("MAX_VAGAS_POR_PLATAFORMA", "6"))
TENTATIVAS_BUSCA = int(os.getenv("TENTATIVAS_BUSCA", "2"))
TIMEOUT_PAGINA = int(os.getenv("TIMEOUT_PAGINA", "25"))
GRUPO_MENSAGEM_DISCORD = int(os.getenv("GRUPO_MENSAGEM_DISCORD", "3"))

# Termos que queremos procurar
PALAVRAS_CHAVE = ["junior", "assistente", "auxiliar", "desenvolvedor", "programador", "TI", "tecnologia", "sistema", "software", "analista"]
# Termos para filtrar vagas de TI
TERMOS_TI = ["TI", "tecnologia", "desenvolvedor", "programador", "sistema", "software", "analista", "dados", "web", "mobile", "backend", "frontend", "dev", "engenharia", "computação"]

# ===========================
# 📝 CONFIGURAÇÃO DE LOGS
# ===========================
def setup_logging():
    """Configura o sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def log_info(message):
    """Log de informações"""
    logging.info(f"📝 {message}")

def log_error(message):
    """Log de erros"""
    logging.error(f"❌ {message}")

def log_success(message):
    """Log de sucesso"""
    logging.info(f"✅ {message}")

# ===========================
# 🛠️ FUNÇÕES AUXILIARES
# ===========================
def validar_vaga(titulo, link):
    """Valida se os dados da vaga são consistentes"""
    if not titulo or not link:
        return False
    
    # Remove vagas com títulos muito curtos ou genéricos
    if len(titulo.strip()) < 5:
        return False
    
    # Verifica se o link é válido
    if not link.startswith(('http://', 'https://')):
        return False
    
    return True

def normalizar_titulo(titulo):
    """Remove espaços extras e normaliza o título"""
    return ' '.join(titulo.split())

def buscar_vagas_com_tentativas(funcao_busca, nome_plataforma, tentativas=TENTATIVAS_BUSCA):
    """Executa a busca com múltiplas tentativas em caso de falha"""
    for tentativa in range(tentativas):
        try:
            log_info(f"Tentativa {tentativa + 1} para {nome_plataforma}")
            vagas = funcao_busca()
            if vagas:
                log_success(f"{nome_plataforma}: {len(vagas)} vagas encontradas")
                return vagas
            else:
                log_info(f"{nome_plataforma}: Nenhuma vaga encontrada na tentativa {tentativa + 1}")
                
        except Exception as e:
            log_error(f"Erro na tentativa {tentativa + 1} para {nome_plataforma}: {str(e)}")
            if tentativa < tentativas - 1:
                log_info(f"Aguardando 5 segundos antes da próxima tentativa...")
                time.sleep(5)
    
    log_error(f"Todas as {tentativas} tentativas falharam para {nome_plataforma}")
    return []

# ===========================
# 🔍 FUNÇÃO: Buscar vagas no Indeed
# ===========================
def buscar_vagas_indeed():
    log_info("🌐 Iniciando busca no Indeed...")
    
    vagas_encontradas = []
    driver = None
    
    try:
        # Configuração para GitHub Actions
        options = setup_chrome_github_actions()
        
        # Usar Chrome diretamente (SEM WebDriver Manager)
        driver = webdriver.Chrome(options=options)
        
        # Monta URL
        termos = "+OR+".join(PALAVRAS_CHAVE)
        url = f"https://br.indeed.com/jobs?q={termos}&l={LOCAL.replace(' ', '+')}"
        log_info(f"🔗 Acessando: {url}")
        
        # Acessa a página
        driver.get(url)
        
        # Aguarda carregamento
        WebDriverWait(driver, TIMEOUT_PAGINA).until(
            lambda d: "Indeed" in d.title
        )
        log_info(f"📄 Página carregada: {driver.title}")
        
        time.sleep(3)
        
        # Captura vagas
        vagas = driver.find_elements(By.CSS_SELECTOR, "a.jcs-JobTitle")
        log_info(f"🔍 {len(vagas)} elementos de vaga encontrados")
        
        # Processa vagas
        for job in vagas[:MAX_VAGAS_POR_PLATAFORMA]:
            try:
                titulo = job.text.strip()
                link = job.get_attribute("href")
                
                if not validar_vaga(titulo, link):
                    continue
                
                # Filtra por termos de TI
                titulo_lower = titulo.lower()
                if any(termo.lower() in titulo_lower for termo in TERMOS_TI):
                    vaga_formatada = f"**{titulo}**\n{link}"
                    vagas_encontradas.append(vaga_formatada)
                    log_success(f"Vaga filtrada (TI): {titulo}")
                    
            except Exception as e:
                log_error(f"Erro ao processar vaga individual: {e}")
                continue
        
        log_success(f"Indeed: {len(vagas_encontradas)} vagas de TI válidas encontradas")
        
    except Exception as e:
        log_error(f"Erro geral na busca Indeed: {e}")
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    return vagas_encontradas

# ===========================
# 🔍 FUNÇÃO: Buscar vagas no Glassdoor
# ===========================
def buscar_vagas_glassdoor():
    log_info("🌐 Iniciando busca no Glassdoor...")
    
    vagas_encontradas = []
    driver = None
    
    try:
        # Configuração para GitHub Actions
        options = setup_chrome_github_actions()
        driver = webdriver.Chrome(options=options)
        
        # Monta URL do Glassdoor
        termos = " ".join(PALAVRAS_CHAVE)
        local_formatado = LOCAL.replace(" ", "%20")
        url = f"https://www.glassdoor.com.br/Vaga/{termos.replace(' ', '-')}-vagas-{local_formatado}-SRCH_KO0,14.htm"
        log_info(f"🔗 Acessando: {url}")
        
        # Acessa a página
        driver.get(url)
        
        # Aguarda carregamento
        time.sleep(5)
        
        # Tenta capturar vagas com vários seletores
        seletores_vagas = [
            "[data-test='jobListing']",
            ".jobListing", 
            ".jl",
            ".react-job-listing",
            "a.jobLink"
        ]
        
        vagas = []
        for seletor in seletores_vagas:
            try:
                vagas = driver.find_elements(By.CSS_SELECTOR, seletor)
                if vagas:
                    log_info(f"🔍 {len(vagas)} vagas encontradas com seletor: {seletor}")
                    break
            except:
                continue
        
        # Processa vagas
        for job in vagas[:MAX_VAGAS_POR_PLATAFORMA]:
            try:
                titulo = job.text.strip()[:100]  # Limita tamanho
                link = job.get_attribute("href")
                
                if not validar_vaga(titulo, link):
                    continue
                
                # Garante link absoluto
                if link and link.startswith('/'):
                    link = f"https://www.glassdoor.com.br{link}"
                
                # Filtra por termos de TI
                titulo_lower = titulo.lower()
                if any(termo.lower() in titulo_lower for termo in TERMOS_TI):
                    vaga_formatada = f"**{titulo}**\n{link}"
                    vagas_encontradas.append(vaga_formatada)
                    log_success(f"Vaga filtrada (TI): {titulo}")
                    
            except Exception as e:
                log_error(f"Erro ao processar vaga Glassdoor: {e}")
                continue
        
        log_success(f"Glassdoor: {len(vagas_encontradas)} vagas de TI válidas encontradas")
        
    except Exception as e:
        log_error(f"Erro geral na busca Glassdoor: {e}")
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    return vagas_encontradas

# ===========================
# 🚀 FUNÇÃO: Enviar mensagem para o Discord
# ===========================
def enviar_discord(vagas):
    if not DISCORD_WEBHOOK_URL:
        log_error("DISCORD_WEBHOOK_URL não configurada!")
        return
    
    if not vagas:
        log_info("Nenhuma vaga para enviar")
        return
    
    for i in range(0, len(vagas), GRUPO_MENSAGEM_DISCORD):
        grupo = vagas[i:i + GRUPO_MENSAGEM_DISCORD]
        conteudo = "\n\n".join(grupo)
        
        mensagem = {
            "content": f"🎯 **Vagas de TI em {LOCAL}**\n\n{conteudo}"
        }
        
        try:
            resposta = requests.post(DISCORD_WEBHOOK_URL, json=mensagem, timeout=15)
            if resposta.status_code == 204:
                log_success("Mensagem enviada para Discord!")
            else:
                log_error(f"Erro Discord: {resposta.status_code}")
        except Exception as e:
            log_error(f"Erro ao enviar para Discord: {e}")

# ===========================
# 🧠 FUNÇÃO PRINCIPAL
# ===========================
def main():
    """Função principal"""
    setup_logging()
    log_info("🚀 Iniciando busca de vagas...")
    
    if not DISCORD_WEBHOOK_URL:
        log_error("DISCORD_WEBHOOK_URL não configurada!")
        return
    
    # Busca vagas
    vagas_indeed = buscar_vagas_com_tentativas(buscar_vagas_indeed, "Indeed")
    vagas_glassdoor = buscar_vagas_com_tentativas(buscar_vagas_glassdoor, "Glassdoor")
    
    # Combina resultados
    todas_vagas = vagas_indeed + vagas_glassdoor
    
    if not todas_vagas:
        log_info("📭 Nenhuma vaga encontrada")
        return
    
    # Remove duplicatas
    vagas_unicas = []
    titulos_vistos = set()
    
    for vaga in todas_vagas:
        titulo = vaga.split('\n')[0]
        titulo_normalizado = normalizar_titulo(titulo)
        
        if titulo_normalizado not in titulos_vistos:
            vagas_unicas.append(vaga)
            titulos_vistos.add(titulo_normalizado)
    
    log_info(f"📊 Total de vagas únicas: {len(vagas_unicas)}")
    
    # Envia para Discord
    enviar_discord(vagas_unicas)
    log_success("🏁 Busca concluída!")

if __name__ == "__main__":
    main()
