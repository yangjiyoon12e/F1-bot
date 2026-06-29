import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import os
import io

NTFY_TOPIC = "FIA-F1-DOCS"
URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"
HISTORY_FILE = "last_link.txt"

def run_bot():
    try:
        seen_links = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                seen_links = f.read().splitlines()

        response = requests.get(URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        docs = soup.find_all('li', class_='document-row')[:5] # 최신 5개만 확인
        
        new_links_found = []

        for doc in reversed(docs):
            title = doc.find('div', class_='title').text.strip()
            link = "https://www.fia.com" + doc.find('a')['href']

            if link not in seen_links:
                print(f"New Doc Found: {title}")
                
                try:
                    pdf_response = requests.get(link)
                    pdf_file = io.BytesIO(pdf_response.content)
                    reader = PdfReader(pdf_file)
                    
                    full_text = ""
                    # PDF의 모든 페이지에서 텍스트 추출 (최대 3,800자까지)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += page_text + "\n"
                        if len(full_text) > 3800: break
                            
                    # ntfy 전송 (영어 원문 그대로)
                    # 메시지가 너무 길면 ntfy가 거부할 수 있으므로 3900자로 안전하게 자름
                    safe_text = full_text[:3900]
                    
                    message = f"🏎️ [F1 DOC] {title}\n\n{safe_text}\n\n🔗 Link: {link}"
                    
                    requests.post(
                        f"https://ntfy.sh/{NTFY_TOPIC}",
                        data=message.encode('utf-8'),
                        headers={
                            "Title": f"New FIA Document: {title[:50]}",
                            "Priority": "high"
                        }
                    )
                    
                    new_links_found.append(link)
                    
                except Exception as e:
                    print(f"Error processing PDF: {e}")

        if new_links_found:
            updated_links = (seen_links + new_links_found)[-50:]
            with open(HISTORY_FILE, "w") as f:
                f.write("\n".join(updated_links))
            print("Successfully updated history.")
        else:
            print("No new documents.")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    run_bot()
