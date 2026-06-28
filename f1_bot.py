import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from deep_translator import GoogleTranslator
import os
import io

# 설정
NTFY_TOPIC = "FIA-F1-DOCS"
URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"

# 봇 차단 방지를 위한 브라우저 헤더 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def run_bot():
    try:
        # 1. FIA 웹사이트 확인 (Headers 추가)
        response = requests.get(URL, headers=HEADERS)
        response.raise_for_status() # 접속 에러 시 바로 Exception으로 이동
        
        soup = BeautifulSoup(response.content, 'html.parser')
        latest_doc = soup.find('li', class_='document-row')
        
        if not latest_doc:
            print("문서 요소를 찾을 수 없습니다. 사이트 구조를 확인하세요.")
            return

        title = latest_doc.find('div', class_='title').text.strip()
        link = "https://www.fia.com" + latest_doc.find('a')['href']

        # 2. 이전에 확인한 문서인지 비교
        last_link = ""
        if os.path.exists("last_link.txt"):
            with open("last_link.txt", "r") as f:
                last_link = f.read().strip()

        if link != last_link:
            print(f"새로운 문서 발견!: {title}")
            
            # 3. PDF 다운로드 및 글자 읽기
            pdf_response = requests.get(link, headers=HEADERS)
            pdf_file = io.BytesIO(pdf_response.content)
            reader = PdfReader(pdf_file)
            
            # 텍스트 추출 안정성 강화
            first_page_text = ""
            if reader.pages:
                first_page_text = reader.pages[0].extract_text() or ""
            
            extract = first_page_text[:1500] 
            
            # 4. 구글 번역기로 한국어 번역
            translated_title = title
            translated_extract = "내용 없음"
            
            translator = GoogleTranslator(source='auto', target='ko')
            if title:
                translated_title = translator.translate(title)
            if extract.strip():
                translated_extract = translator.translate(extract)
            
            # 5. ntfy로 알림 보내기 (안정적인 구조로 변경)
            message = f"[PDF 주요내용 번역]\n{translated_extract}...\n\n🔗 원본 링크: {link}"
            
            # 한글 깨짐 방지를 위해 body는utf-8 인코딩, 제목은 X-Title 헤더로 전송
            ntfy_headers = {
                "Title": translated_title.encode('utf-8'), # ntfy가 utf-8 제목을 처리하도록 바이트 전달
                "Tags": "rotating_light,formula1" # 알림에 이모지 태그 추가 (선택사항)
            }
            
            ntfy_url = f"https://ntfy.sh/{NTFY_TOPIC}"
            ntfy_response = requests.post(ntfy_url, data=message.encode('utf-8'), headers=ntfy_headers)
            
            if ntfy_response.status_code == 200:
                print("ntfy 알림 전송 완료!")
                # 6. 성공했을 때만 '마지막 문서'로 저장
                with open("last_link.txt", "w") as f:
                    f.write(link)
            else:
                print(f"ntfy 전송 실패 (상태코드: {ntfy_response.status_code})")
        else:
            print("새로 올라온 문서가 없습니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    run_bot()
