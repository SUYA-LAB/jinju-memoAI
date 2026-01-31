import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# 페이지 설정
st.set_page_config(
    page_title="진주햄 메시지 분석",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4f46e5;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #4338ca;
    }
    .team-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .team-brand {
        background-color: #dbeafe;
        color: #1e40af;
    }
    .team-meat {
        background-color: #fce7f3;
        color: #9f1239;
    }
    .team-business {
        background-color: #d1fae5;
        color: #065f46;
    }
    .result-box {
        background-color: #f0f9ff;
        border: 2px solid #3b82f6;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .history-item {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Secrets에서 설정 가져오기
def get_config():
    """Streamlit Secrets에서 설정 가져오기"""
    try:
        return {
            'cf_account_id': st.secrets['cloudflare']['account_id'],
            'cf_api_token': st.secrets['cloudflare']['api_token'],
            'apps_script_url_brand': st.secrets['google']['apps_script_url_brand'],
            'apps_script_url_meat': st.secrets['google']['apps_script_url_meat'],
            'sheet_name': st.secrets['google'].get('sheet_name', '지시사항분석')
        }
    except Exception as e:
        st.error(f"⚠️ Secrets 설정을 확인해주세요: {str(e)}")
        st.info("""
        **Streamlit Cloud > Settings > Secrets에 다음을 추가하세요:**
        ```toml
        [cloudflare]
        account_id = "your-account-id"
        api_token = "your-api-token"
        
        [google]
        apps_script_url_brand = "https://script.google.com/macros/s/AKfycbyM6mfPdYDXgwIKkjAv9CdZrenHLetP1grs_iWehzcAFEjz8zN_6kMjM4WnVCFAHvbM/exec"
        apps_script_url_meat = "https://script.google.com/macros/s/AKfycbwgqsJMK-hjBounu_cKNu3fNqTunlAJwt3VqaLGXkSdj-zXaOee8Z1BVGfIXShmXXggdg/exec"
        sheet_name = "지시사항분석"
        ```
        """)
        return None

# AI 분석 함수
def analyze_with_ai(directive_text, config):
    """Cloudflare Workers AI로 지시사항 분석"""
    url = f"https://api.cloudflare.com/client/v4/accounts/{config['cf_account_id']}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    
    headers = {
        'Authorization': f"Bearer {config['cf_api_token']}",
        'Content-Type': 'application/json'
    }
    
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "당신은 진주햄의 업무 분석 AI 비서입니다. 메시지를 분석하여 반드시 다음 형식으로만 답변하세요:\n\n📌 요약:\n(핵심 내용을 2-3문장으로 간결하게)\n\n🎯 의도:\n(메시지의 목적과 배경 설명)\n\n✅ 해야할 일:\n(메시지에서 언급된 모든 액션 아이템을 빠짐없이 명사형으로 나열. 갯수 제한 없음)\n1. 명사형으로 간결하게 (예: 더블링 25g/45g 판매 데이터 수집 및 분석)\n2. 명사형으로 간결하게 (예: 쿠팡 리뷰 등 소비자 VOC 조사)\n3. 명사형으로 간결하게 (예: 경쟁사 제품 가격 비교 분석)\n...(필요한 만큼 모두 나열)\n\n중요: 해야할 일은 메시지에서 언급된 모든 과제, 분석, 검토 사항을 빠뜨리지 말고 전부 포함해야 합니다. 해야할 일은 반드시 명사형으로 끝나야 하며(~하기, ~분석, ~조사, ~수집, ~검토, ~수립), 문장이 아닌 키워드 중심으로 작성하세요. 한국어로 답변하고, 육가공 산업 용어를 사용하세요."
            },
            {
                "role": "user",
                "content": f"다음 메시지를 분석해주세요:\n\n{directive_text}"
            }
        ],
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get('result', {}).get('response', '분석 결과를 가져올 수 없습니다.')
    except Exception as e:
        raise Exception(f"AI 분석 오류: {str(e)}")

# Google Sheets에 저장
def save_to_sheets(team, directive, analysis, config):
    """Google Sheets에 데이터 저장"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    data = {
        'sheetName': config['sheet_name'],
        'timestamp': timestamp,
        'team': team,
        'directive': directive,
        'analysis': analysis
    }
    
     # 팀별 URL 선택
    if team == '브랜드':
        url = config['apps_script_url_brand']
    elif team == '육가공':
        url = config['apps_script_url_meat']
    elif team == '사업관리':
        url = config['apps_script_url_business']
    else:
        url = config.get('apps_script_url', '')  # 기본값

    try:
        response = requests.post(
            url,
            json=data,
            timeout=10
        )
        return True
    except Exception as e:
        st.warning(f"Google Sheets 저장 실패: {str(e)}")
        return False

# Google Sheets에서 불러오기
def load_from_sheets(config):
    """Google Sheets에서 히스토리 불러오기 (브랜드 + 육가공 합치기)"""
    all_data = []
    
    # 브랜드 시트에서 불러오기
    try:
        url_brand = f"{config['apps_script_url_brand']}?sheetName={config['sheet_name']}"
        response_brand = requests.get(url_brand, timeout=10)
        data_brand = response_brand.json()
        if data_brand.get('success') and data_brand.get('data'):
            all_data.extend(data_brand['data'])
    except Exception as e:
        st.warning(f"브랜드 히스토리 로드 실패: {str(e)}")
    
    # 육가공 시트에서 불러오기
    try:
        url_meat = f"{config['apps_script_url_meat']}?sheetName={config['sheet_name']}"
        response_meat = requests.get(url_meat, timeout=10)
        data_meat = response_meat.json()
        if data_meat.get('success') and data_meat.get('data'):
            all_data.extend(data_meat['data'])
    except Exception as e:
        st.warning(f"육가공 히스토리 로드 실패: {str(e)}")
    
    return all_data

# 팀 뱃지 생성
def get_team_badge(team):
    """팀별 색상 뱃지 HTML 생성"""
    badge_classes = {
        '브랜드': 'team-brand',
        '육가공': 'team-meat',
        '사업관리': 'team-business'
    }
    badge_class = badge_classes.get(team, 'team-brand')
    return f'<span class="team-badge {badge_class}">{team}</span>'

# AI 분석 결과 파싱
def parse_analysis(analysis):
    """AI 분석 결과를 요약/의도/해야할일로 분리"""
    sections = {
        'summary': '',
        'intent': '',
        'tasks': ''
    }
    
    lines = analysis.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        if '요약:' in line or '📌 요약' in line:
            current_section = 'summary'
            continue
        elif '의도:' in line or '🎯 의도' in line:
            current_section = 'intent'
            continue
        elif '해야할 일:' in line or '✅ 해야할 일' in line or '해야 할 일:' in line:
            current_section = 'tasks'
            continue
        
        if current_section and line:
            sections[current_section] += line + '\n'
    
    return sections

# 메인 앱
def main():
    # 헤더
    st.title("📋 진주햄 메시지 분석")
    st.markdown("AI를 활용한 메시지 자동 분석 시스템")
    
    # 설정 확인
    config = get_config()
    if not config:
        st.stop()
    
    # 사이드바 - 통계
    with st.sidebar:
        st.markdown("### 📊 통계")
        
        # 히스토리 로드하여 통계 표시
        history = load_from_sheets(config)
        if history:
            teams = [h.get('team') for h in history if h.get('team')]
            st.metric("전체 분석 건수", len(history))
            
            if teams:
                team_counts = pd.Series(teams).value_counts()
                for team, count in team_counts.items():
                    st.metric(f"{team} 팀", count)
    
    # 메인 컨텐츠
    tab1, tab2 = st.tabs(["✍️ 메시지 분석", "📚 히스토리"])
    
    # Tab 1: 메시지 분석
    with tab1:
        st.header("메시지 입력")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            team = st.selectbox(
                "팀 구분",
                ["", "브랜드", "육가공", "사업관리"],
                index=0
            )
        
        with col2:
            pass
        
        directive_text = st.text_area(
            "메시지 내용",
            height=200,
            placeholder="메시지를 입력하세요..."
        )
        
        if st.button("🤖 AI 분석 시작", type="primary"):
            if not team:
                st.error("팀 구분을 선택해주세요.")
            elif not directive_text.strip():
                st.error("메시지 내용을 입력해주세요.")
            else:
                with st.spinner("AI가 메시지를 분석 중입니다..."):
                    try:
                        # AI 분석
                        analysis = analyze_with_ai(directive_text, config)
                        
                        # 결과 표시
                        st.markdown(f"### 🤖 AI 분석 결과 {get_team_badge(team)}", unsafe_allow_html=True)
                        
                        # 분석 결과를 섹션별로 파싱
                        sections = parse_analysis(analysis)
                        
                        # 요약
                        if sections.get('summary'):
                            st.markdown("#### 📌 요약")
                            st.info(sections['summary'])
                        
                        # 의도
                        if sections.get('intent'):
                            st.markdown("#### 🎯 의도")
                            st.warning(sections['intent'])
                        
                        # 해야할 일
                        if sections.get('tasks'):
                            st.markdown("#### ✅ 해야할 일")
                            st.success(sections['tasks'])
                        
                        # Google Sheets에 저장
                        if save_to_sheets(team, directive_text, analysis, config):
                            st.success("✅ 분석이 완료되고 Google Sheets에 저장되었습니다!")
                        
                        # 세션 상태 초기화 버튼
                        if st.button("새로운 분석 시작"):
                            st.rerun()
                        
                    except Exception as e:
                        st.error(f"오류 발생: {str(e)}")
    
    # Tab 2: 히스토리
    with tab2:
        st.header("메시지 히스토리")
        
        # 필터
        filter_col1, filter_col2 = st.columns([3, 1])
        
        with filter_col1:
            filter_team = st.radio(
                "팀 필터",
                ["전체", "브랜드", "육가공", "사업관리"],
                horizontal=True
            )
        
        with filter_col2:
            if st.button("🔄 새로고침"):
                st.rerun()
        
        # 히스토리 로드
        history = load_from_sheets(config)
        
        if not history:
            st.info("저장된 히스토리가 없습니다.")
        else:
            # 필터링
            if filter_team != "전체":
                history = [h for h in history if h.get('team') == filter_team]
            
            # 역순 정렬 (최신순)
            history = list(reversed(history))
            
            if not history:
                st.info(f"{filter_team} 팀의 히스토리가 없습니다.")
            else:
                st.markdown(f"**총 {len(history)}건의 분석 결과**")
                
                # 히스토리 표시
                for idx, item in enumerate(history):
                    with st.container():
                        st.markdown('<div class="history-item">', unsafe_allow_html=True)
                        
                        # 헤더
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(
                                f"{get_team_badge(item.get('team', ''))} "
                                f"<small style='color: #6b7280;'>{item.get('timestamp', '')}</small>",
                                unsafe_allow_html=True
                            )
                        
                        # 지시사항
                        st.markdown(f"**지시사항:**")
                        st.markdown(f"{item.get('directive', '')}")
                        
                        # 분석 결과 (expander로 접기)
                        with st.expander("📊 AI 분석 결과 보기"):
                            st.markdown(item.get('analysis', ''))
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown("---")

if __name__ == "__main__":
    main()
