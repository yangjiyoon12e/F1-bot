import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from deep_translator import GoogleTranslator
import os
import io

NTFY_TOPIC = "FIA-F1-DOCS"
URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14"
HISTORY_FILE = "last_link.txt"

def run_bot():
    try:
        # 1. 봇이 예전에 본 문서들(기억) 불러오기
        seen_links = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                seen_links = f.read().splitlines()

        # 2. FIA 사이트에서 최신 문서 위에서부터 10개 가져오기
        response = requests.get(URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        docs = soup.find_all('li', class_='document-row')[:10]
        
        new_links_found = []

        # 3. 오래된 문서부터 최신 문서 순서로(거꾸로) 확인하여 빠짐없이 알림
        for doc in reversed(docs):
            title = doc.find('div', class_='title').text.strip()
            link = "https://www.fia.com" + doc.find('a')['href']

            if link not in seen_links:
                print(f"새 문서 발견: {title}")
                
                try:
                    # PDF 다운로드 및 텍스트 추출
                    pdf_response = requests.get(link)
                    pdf_file = io.BytesIO(pdf_response.content)
                    reader = PdfReader(pdf_file)
                    
                    raw_text = ""
                    for i in range(min(2, len(reader.pages))):
                        page_text = reader.pages[i].extract_text()
                        if page_text:
                            raw_text += page_text + " "
                            
                    cleaned_text = ' '.join(raw_text.split())
                    
                    # 헤더(200자) 날리고 핵심 내용(800자) 추출 (번역기 오류 방지용 최적 길이)
                    if len(cleaned_text) > 200:
                        core_text = cleaned_text[200:1000]
                    else:
                        core_text = cleaned_text[:800]
                    
                    # 4. 번역 시도 (에러 나도 멈추지 않음)
                    translator = GoogleTranslator(source='auto', target='ko')
                    trans_title = translator.translate(title)
                    
                    try:
                        trans_text = translator.translate(core_text)
                    except:
                        # 번역기가 뻗으면 영어 원문이라도 보냄
                        trans_text = f"[번역 실패 - 원문 표시]\n{core_text}"

                    # 5. ntfy로 알림 쏘기
                    message = f"🚨 {trans_title}\n\n[내용 요약]\n{trans_text}...\n\n🔗 원본: {link}"
                    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode('utf-8'))
                    
                    new_links_found.append(link)
                    
                except Exception as e:
                    print(f"PDF 처리 중 오류: {e}")

        # 6. 새로 확인한 문서들을 기억(history)에 추가 (최대 50개 유지)
        if new_links_found:
            updated_links = (seen_links + new_links_found)[-50:]
            with open(HISTORY_FILE, "w") as f:
                f.write("\n".join(updated_links))
            print("업데이트 완료!")
        else:
            print("새로 올라온 문서가 없습니다.")

    except Exception as e:
        print(f"전체 오류 발생: {e}")

if __name__ == "__main__":
    run_bot()
