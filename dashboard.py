import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psutil

# 페이지 기본 설정
st.set_page_config(
    page_title="Music Bot Monitoring Dashboard",
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
        df['time'] = pd.to_datetime(df['time'], format='%H:%M:%S').dt.time
    return df

# 재생 통계 분석 함수
def analyze_play_statistics(df):
    if df.empty:
        return None, None, None, None, None
    
    total_plays = len(df)
    successful_plays = len(df[df['success'] == True])
    unique_tracks = df['video_id'].nunique()
    unique_users = df['user_id'].nunique()
    unique_servers = df['guild_id'].nunique()
    
    return total_plays, successful_plays, unique_tracks, unique_users, unique_servers

# 시간대별 재생 통계
def get_hourly_statistics(df):
    if df.empty:
        return pd.DataFrame()
    df['hour'] = pd.to_datetime(df['time'], format='%H:%M:%S').dt.hour
    return df.groupby('hour').size().reset_index(name='count')

def main():
    st.title("🎵 Music Bot Monitoring Dashboard")
    
    try:
        # 데이터 로드
        df_stats = load_statistics_data()
        
        # 탭 생성
        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Detailed Statistics", "Performance Metrics", "System Health"])
        
        with tab1:
            st.header("Overview")
            if not df_stats.empty:
                total_plays, successful_plays, unique_tracks, unique_users, unique_servers = analyze_play_statistics(df_stats)
                
                # KPI Metrics
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Total Plays", f"{total_plays:,}")
                with col2:
                    success_rate = (successful_plays / total_plays * 100) if total_plays > 0 else 0
                    st.metric("Success Rate", f"{success_rate:.1f}%")
                with col3:
                    st.metric("Unique Tracks", f"{unique_tracks:,}")
                with col4:
                    st.metric("Unique Users", f"{unique_users:,}")
                with col5:
                    st.metric("Unique Servers", f"{unique_servers:,}")

                # 일간 트렌드 차트
                daily_trend = df_stats.groupby('date').size().reset_index(name='plays')
                fig_trend = px.line(
                    daily_trend,
                    x='date',
                    y='plays',
                    title='Daily Play Count Trend'
                )
                st.plotly_chart(fig_trend, use_container_width=True)

                # Top Artists Chart
                top_artists = df_stats['artist'].value_counts().head(10)
                fig_artists = px.bar(
                    x=top_artists.index,
                    y=top_artists.values,
                    title='Top 10 Artists',
                    labels={'x': 'Artist', 'y': 'Plays'}
                )
                st.plotly_chart(fig_artists, use_container_width=True)

        with tab2:
            st.header("Detailed Statistics")
            
            # 날짜 범위 선택
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    min(df_stats['date']).date() if not df_stats.empty else datetime.now().date()
                )
            with col2:
                end_date = st.date_input(
                    "End Date",
                    max(df_stats['date']).date() if not df_stats.empty else datetime.now().date()
                )

            if not df_stats.empty:
                # 시간대별 재생 통계
                hourly_stats = get_hourly_statistics(df_stats)
                fig_hourly = px.bar(
                    hourly_stats,
                    x='hour',
                    y='count',
                    title='Plays by Hour of Day'
                )
                st.plotly_chart(fig_hourly, use_container_width=True)

                # Top Tracks Table
                st.subheader("Most Played Tracks")
                top_tracks = df_stats.groupby(['title', 'artist']).size()\
                    .reset_index(name='plays')\
                    .sort_values('plays', ascending=False)\
                    .head(10)
                st.dataframe(top_tracks, use_container_width=True)

        with tab3:
            st.header("Performance Metrics")
            
            # Success Rate Gauge
            if not df_stats.empty:
                success_rate = (successful_plays / total_plays * 100) if total_plays > 0 else 0
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=success_rate,
                    title={'text': "Play Success Rate"},
                    domain={'x': [0, 1], 'y': [0, 1]},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkgreen"},
                        'steps': [
                            {'range': [0, 60], 'color': "red"},
                            {'range': [60, 80], 'color': "yellow"},
                            {'range': [80, 100], 'color': "lightgreen"}
                        ]
                    }
                ))
                st.plotly_chart(fig_gauge, use_container_width=True)

                # Duration Distribution
                fig_duration = px.histogram(
                    df_stats,
                    x='duration',
                    title='Track Duration Distribution',
                    labels={'duration': 'Duration (seconds)'}
                )
                st.plotly_chart(fig_duration, use_container_width=True)

        with tab4:
            st.header("System Health")
            
            # CPU, Memory 사용량 모니터링
            col1, col2 = st.columns(2)
            with col1:
                cpu_usage = psutil.cpu_percent()
                st.metric("CPU Usage", f"{cpu_usage}%")
                
            with col2:
                memory = psutil.virtual_memory()
                memory_usage = memory.percent
                st.metric("Memory Usage", f"{memory_usage}%")
            
            # 디스크 사용량
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            st.progress(disk_usage / 100)
            st.text(f"Disk Usage: {disk_usage}%")

        # 설정 섹션
        with st.expander("Dashboard Settings"):
            st.write("Update Interval: 5 minutes")
            st.write("Data Retention: 30 days")
            if st.button("Clear Cache"):
                st.cache_data.clear()
                st.experimental_rerun()
                
    except Exception as e:
        st.error(f"An error occurred while loading the dashboard: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()