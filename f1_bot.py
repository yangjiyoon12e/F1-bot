import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from deep_translator import GoogleTranslator
import os
import io

# 설정
NTFY_TOPIC = "FIA-F1-DOCS"
URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"

def run_bot():
    try:
        # 1. FIA 웹사이트 확인
        response = requests.get(URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        latest_doc = soup.find('li', class_='document-row')
        
        title = latest_doc.find('div', class_='title').text.strip()
        link = "https://www.fia.com" + latest_doc.find('a')['href']

        # 2. 이전에 확인한 문서인지 비교
        last_link = ""
        if os.path.exists("last_link.txt"):
            with open("last_link.txt", "r") as f:
                last_link = f.read().strip()

        if link != last_link:
            print("새로운 문서 발견!")
            
            # 3. PDF 다운로드 및 글자 읽기
            pdf_response = requests.get(link)
            pdf_file = io.BytesIO(pdf_response.content)
            reader = PdfReader(pdf_file)
            
            # PDF 첫 페이지 텍스트만 추출 (가장 중요한 내용이 있음)
            first_page_text = reader.pages[0].extract_text()
            
            # 번역기 한도 보호를 위해 핵심이 되는 앞부분 1500자만 자르기
            extract = first_page_text[:1500] 
            
            # 4. 구글 번역기로 한국어 번역
            translator = GoogleTranslator(source='auto', target='ko')
            translated_title = translator.translate(title)
            translated_extract = translator.translate(extract)
            
            # 5. ntfy(태블릿)로 알림 보내기
            message = f"🚨 F1 새 문서: {translated_title}\n\n[PDF 주요내용 번역]\n{translated_extract}...\n\n🔗 원본 링크: {link}"
            requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode('utf-8'))
            
            # 6. 현재 문서를 '마지막 문서'로 저장
            with open("last_link.txt", "w") as f:
                f.write(link)
        else:
            print("새로 올라온 문서가 없습니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    run_bot()
