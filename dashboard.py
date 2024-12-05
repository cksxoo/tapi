import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# 페이지 기본 설정
st.set_page_config(
    page_title="Music Bot Statistics",
    page_icon="🎵",
    layout="wide"
)

# 데이터베이스 연결 함수
@st.cache_resource
def get_database_connection():
    return sqlite3.connect('musicbot/db/discord.db', check_same_thread=False)

# 통계 데이터 로드 함수
@st.cache_data
def load_statistics_data():
    conn = get_database_connection()
    df = pd.read_sql_query("SELECT * FROM statistics", conn)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

# 언어 설정 데이터 로드 함수
@st.cache_data
def load_language_data():
    conn = get_database_connection()
    return pd.read_sql_query("SELECT * FROM language", conn)

# 반복 재생 설정 데이터 로드 함수
@st.cache_data
def load_loop_settings():
    conn = get_database_connection()
    return pd.read_sql_query("SELECT * FROM loop_setting", conn)

# 셔플 설정 데이터 로드 함수
@st.cache_data
def load_shuffle_settings():
    conn = get_database_connection()
    return pd.read_sql_query("SELECT * FROM shuffle", conn)

def main():
    st.title("🎵 Music Bot Statistics Dashboard")
    
    try:
        # 데이터 로드
        df_stats = load_statistics_data()
        df_language = load_language_data()
        df_loop = load_loop_settings()
        df_shuffle = load_shuffle_settings()
        
        # 탭 생성
        tab1, tab2, tab3 = st.tabs(["재생 통계", "서버 설정", "사용자 설정"])
        
        with tab1:
            st.header("음악 재생 통계")
            
            if df_stats.empty:
                st.warning("아직 재생 통계 데이터가 없습니다.")
            else:
                # 날짜 범위 선택
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "시작일",
                        min(df_stats['date']).date()
                    )
                with col2:
                    end_date = st.date_input(
                        "종료일",
                        max(df_stats['date']).date()
                    )
                
                # 데이터 필터링
                mask = (df_stats['date'].dt.date >= start_date) & (df_stats['date'].dt.date <= end_date)
                filtered_df = df_stats.loc[mask]
                
                if filtered_df.empty:
                    st.warning("선택한 날짜 범위에 데이터가 없습니다.")
                else:
                    # 일별 재생 횟수 차트
                    daily_plays = filtered_df.groupby('date').sum()['count'].reset_index()
                    fig_daily = px.line(
                        daily_plays,
                        x='date',
                        y='count',
                        title='일별 음악 재생 횟수'
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)
                    
                    # 가장 많이 재생된 곡 Top 10
                    top_songs = filtered_df.groupby('video_id')['count'].sum().sort_values(ascending=False).head(10)
                    fig_top = px.bar(
                        x=top_songs.index,
                        y=top_songs.values,
                        title='가장 많이 재생된 곡 Top 10',
                        labels={'x': '비디오 ID', 'y': '재생 횟수'}
                    )
                    st.plotly_chart(fig_top, use_container_width=True)
                    
                    # 통계 요약
                    st.subheader("통계 요약")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("총 재생 횟수", filtered_df['count'].sum())
                    with col2:
                        st.metric("재생된 곡 수", filtered_df['video_id'].nunique())
                    with col3:
                        st.metric("일평균 재생 횟수", round(filtered_df['count'].mean(), 1))
        
        with tab2:
            st.header("서버 설정 통계")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if df_loop.empty:
                    st.warning("반복 재생 설정 데이터가 없습니다.")
                else:
                    # 반복 재생 설정 분포
                    loop_counts = df_loop['loop_set'].value_counts()
                    fig_loop = px.pie(
                        values=loop_counts.values,
                        names=['Off', 'Single', 'All'] if len(loop_counts) == 3 else loop_counts.index,
                        title='반복 재생 설정 분포'
                    )
                    st.plotly_chart(fig_loop)
            
            with col2:
                if df_shuffle.empty:
                    st.warning("셔플 설정 데이터가 없습니다.")
                else:
                    # 셔플 설정 분포
                    shuffle_counts = df_shuffle['shuffle'].value_counts()
                    fig_shuffle = px.pie(
                        values=shuffle_counts.values,
                        names=['Off', 'On'] if len(shuffle_counts) == 2 else shuffle_counts.index,
                        title='셔플 설정 분포'
                    )
                    st.plotly_chart(fig_shuffle)
        
        with tab3:
            st.header("사용자 언어 설정")
            
            if df_language.empty:
                st.warning("언어 설정 데이터가 없습니다.")
            else:
                # 언어별 사용자 수
                language_counts = df_language['language'].value_counts()
                fig_language = px.pie(
                    values=language_counts.values,
                    names=language_counts.index,
                    title='언어별 사용자 분포'
                )
                st.plotly_chart(fig_language)
                
                # 언어 설정 데이터 테이블
                st.subheader("상세 언어 설정")
                st.dataframe(df_language)
            
    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()