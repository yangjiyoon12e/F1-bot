import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from deep_translator import GoogleTranslator
import os
import io

NTFY_TOPIC = "FIA-F1-DOCS"
URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"

def run_bot():
    try:
        response = requests.get(URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        latest_doc = soup.find('li', class_='document-row')
        
        title = latest_doc.find('div', class_='title').text.strip()
        link = "https://www.fia.com" + latest_doc.find('a')['href']

        last_link = ""
        if os.path.exists("last_link.txt"):
            with open("last_link.txt", "r") as f:
                last_link = f.read().strip()

        if link != last_link:
            print("새로운 문서 발견!")
            
            pdf_response = requests.get(link)
            pdf_file = io.BytesIO(pdf_response.content)
            reader = PdfReader(pdf_file)
            
            # 1. 1페이지와 2페이지 텍스트 모두 가져오기 (사유가 2페이지에 있는 경우 대비)
            raw_text = ""
            for i in range(min(2, len(reader.pages))):
                raw_text += reader.pages[i].extract_text() + " "
                
            # 2. 불필요한 줄바꿈과 공백을 정리하여 데이터 압축
            cleaned_text = ' '.join(raw_text.split())
            
            # 3. F1 문서 특성상 앞부분 250자(로고, 날짜, 수신자 등)는 버리고 핵심 내용만 3500자 추출
            if len(cleaned_text) > 250:
                core_text = cleaned_text[250:3750]
            else:
                core_text = cleaned_text
            
            # 4. 구글 번역기로 한국어 번역
            translator = GoogleTranslator(source='auto', target='ko')
            translated_title = translator.translate(title)
            
            try:
                translated_extract = translator.translate(core_text)
            except:
                translated_extract = "번역 중 오류 발생 (내용을 읽을 수 없음)."
            
            # 5. ntfy로 알림 보내기
            message = f"🚨 F1 새 문서: {translated_title}\n\n[PDF 상세 내용]\n{translated_extract}\n\n🔗 원본 PDF 링크: {link}"
            requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode('utf-8'))
            
            with open("last_link.txt", "w") as f:
                f.write(link)
        else:
            print("새로 올라온 문서가 없습니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    run_bot()
