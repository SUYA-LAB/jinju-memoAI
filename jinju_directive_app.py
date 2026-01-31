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
            'apps_script_url': st.secrets['google']['apps_script_url'],
            'sheet_name': st.secrets['google'].get('sheet_name', '메시지분석')
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
        apps_script_url = "https://script.google.com/macros/s/.../exec"
        sheet_name = "메시지분석"
        ```
        """)
        return None

# AI 분석 함수
def analyze_with_ai(directive_text, config):
    """Cloudflare Workers AI로 메시지 분석"""
    url = f"https://api.cloudflare.com/client/v4/accounts/{config['cf_account_id']}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    
    headers = {
        'Authorization': f"Bearer {config['cf_api_token']}",
        'Content-Type': 'application/json'
    }
    
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "당신은 진주햄의 업무 분석 AI 비서입니다. 메시지을 분석하여 반드시 다음 형식으로만 답변하세요:\n\n📌 요약:\n(핵심 내용을 2-3문장으로 간결하게)\n\n🎯 의도:\n(메시지의 목적과 배경 설명)\n\n✅ 해야할 일:\n1. (구체적인 액션 아이템)\n2. (구체적인 액션 아이템)\n3. (구체적인 액션 아이템)\n\n한국어로 답변하고, 육가공 산업 용어를 사용하세요."
            },
            {
                "role": "user",
                "content": f"다음 메시지을 분석해주세요:\n\n{directive_text}"
            }
        ],
        "max_tokens": 1000
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
    
    try:
        response = requests.post(
            config['apps_script_url'],
            json=data,
            timeout=10
        )
        return True
    except Exception as e:
        st.warning(f"Google Sheets 저장 실패: {str(e)}")
        return False

# Google Sheets에서 불러오기
def load_from_sheets(config):
    """Google Sheets에서 히스토리 불러오기"""
    try:
        url = f"{config['apps_script_url']}?sheetName={config['sheet_name']}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('success') and data.get('data'):
            return data['data']
        return []
    except Exception as e:
        st.error(f"히스토리 로드 실패: {str(e)}")
        return []

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

# 메인 앱
def main():
    # 헤더
    st.title("📋 진주햄 메시지 분석")
    st.markdown("Workers AI를 활용한 메시지 자동 분석 시스템")
    
    # 설정 확인
    config = get_config()
    if not config:
        st.stop()
    
    # 사이드바 - 비밀번호 인증 (선택사항)
    with st.sidebar:
        st.header("🔐 접근 제어")
        
        # 비밀번호 설정 (Secrets에 추가 가능)
        password = st.text_input("비밀번호", type="password")
        
        # Secrets에 비밀번호가 설정되어 있으면 확인
        if 'password' in st.secrets:
            if password != st.secrets['password']:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
                st.stop()
            else:
                st.success("✅ 인증되었습니다.")
        
        st.markdown("---")
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
            placeholder="메시지을 입력하세요..."
        )
        
        if st.button("🤖 AI 분석 시작", type="primary"):
            if not team:
                st.error("팀 구분을 선택해주세요.")
            elif not directive_text.strip():
                st.error("메시지 내용을 입력해주세요.")
            else:
                with st.spinner("AI가 메시지을 분석 중입니다..."):
                    try:
                        # AI 분석
                        analysis = analyze_with_ai(directive_text, config)
                        
                        # 결과 표시
                        st.markdown(f"### 🤖 AI 분석 결과 {get_team_badge(team)}", unsafe_allow_html=True)
                        st.markdown(f'<div class="result-box">{analysis}</div>', unsafe_allow_html=True)
                        
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
                        
                        # 메시지
                        st.markdown(f"**메시지:**")
                        st.markdown(f"{item.get('directive', '')}")
                        
                        # 분석 결과 (expander로 접기)
                        with st.expander("📊 AI 분석 결과 보기"):
                            st.markdown(item.get('analysis', ''))
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown("---")

if __name__ == "__main__":
    main()
