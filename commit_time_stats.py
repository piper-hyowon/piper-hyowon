import os
import requests
import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

GITHUB_TOKEN = os.environ.get('GH_TOKEN')
USERNAME = os.environ.get('GITHUB_USERNAME')

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}


def get_user_repos():
    repos = []
    page = 1
    while True:
        response = requests.get(
            f'https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}',
            headers=headers
        )
        if response.status_code != 200:
            print(f"API 호출 실패: {response.status_code}")
            print(response.text)
            break
        
        new_repos = response.json()
        if not new_repos:
            break
        
        repos.extend([repo['name'] for repo in new_repos if not repo['fork']])
        page += 1
    
    return repos

def get_commits_for_repo(repo_name):
    commits = []
    page = 1
    while True:
        response = requests.get(
            f'https://api.github.com/repos/{USERNAME}/{repo_name}/commits?per_page=100&page={page}&author={USERNAME}',
            headers=headers
        )
        if response.status_code != 200:
            print(f"저장소 {repo_name}에서 커밋 가져오기 실패: {response.status_code}")
            print(response.text)
            break
        
        new_commits = response.json()
        if not new_commits:
            break
        
        for commit in new_commits:
            try:
                if 'commit' in commit and 'author' in commit['commit'] and 'date' in commit['commit']['author']:
                    commits.append(commit['commit']['author']['date'])
            except:
                continue
        
        page += 1
    
    return commits

def analyze_commit_times(all_commits):
    hourly_commits = defaultdict(int)
    
    for commit_date in all_commits:
        try:
            dt = datetime.datetime.strptime(commit_date, '%Y-%m-%dT%H:%M:%SZ')
            kr_hour = (dt.hour + 9) % 24
            hourly_commits[kr_hour] += 1
        except:
            continue
    
    return hourly_commits

def generate_commit_graph(hourly_commits):
    hours = list(range(24))
    counts = [hourly_commits[hour] for hour in hours]
    
    if sum(counts) == 0:
        print("커밋 데이터가 없습니다.")
        return
    
    colors = []
    for hour in hours:
        if 5 <= hour < 9:  # 새벽 (5시-9시)
            colors.append('#FF9D6C')
        elif 9 <= hour < 12:  # 아침 (9시-12시)
            colors.append('#FFCD56')
        elif 12 <= hour < 18:  # 오후 (12시-18시)
            colors.append('#4BC0C0')
        elif 18 <= hour < 22:  # 저녁 (18시-22시)
            colors.append('#36A2EB')
        else:  # 밤 (22시-5시)
            colors.append('#9966FF')
    
    plt.figure(figsize=(12, 6))
    plt.style.use('ggplot')
    
    bars = plt.bar(hours, counts, color=colors, width=0.8, alpha=0.7)
    
    plt.title('Hourly Commit Distribution', fontsize=16, fontweight='bold')
    plt.xlabel('Hour of Day (KST)', fontsize=12)
    plt.ylabel('Number of Commits', fontsize=12)
    plt.xticks(hours, [f'{h:02d}:00' for h in hours], rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1, 
                    int(height), ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    plt.savefig('commit_time_stats.png', dpi=100, bbox_inches='tight')
    print("시간대별 커밋 그래프가 생성되었습니다.")

def generate_markdown_graph(hourly_commits):
    hours = list(range(24))
    counts = [hourly_commits[hour] for hour in hours]
    
    max_count = max(counts) if counts else 0
    if max_count == 0:
        return "커밋 데이터가 없습니다."
    
    markdown = "## ⏰ Hourly Commit Distribution\n\n```text\n"
    
    # 시간대별 이모지 추가
    for hour in hours:
        # 이모지 선택
        if 5 <= hour < 9:
            emoji = "🌅"  # 새벽
        elif 9 <= hour < 12:
            emoji = "🌞"  # 아침
        elif 12 <= hour < 18:
            emoji = "🌇"  # 오후
        elif 18 <= hour < 22:
            emoji = "🌃"  # 저녁
        else:
            emoji = "🌙"  # 밤
        
        # 막대 그래프 생성
        count = hourly_commits[hour]
        percentage = (count / max_count) * 100 if max_count > 0 else 0
        bar_length = int(percentage / 5)  # 20개의 막대를 100%로 설정
        
        bar = '█' * bar_length
        spaces = ' ' * (20 - bar_length)
        
        # 출력 형식 (시간:00 [막대] 커밋수 퍼센트%)
        markdown += f"{emoji} {hour:02d}:00   {bar}{spaces}   {count} commits   {percentage:.2f}%\n"
    
    markdown += "```\n"
    return markdown

def main():
    repos = get_user_repos()
    print(f"{len(repos)}개의 저장소를 찾았습니다.")
    
    all_commits = []
    for repo in repos:
        commits = get_commits_for_repo(repo)
        all_commits.extend(commits)
        print(f"{repo}: {len(commits)}개의 커밋 가져옴")
    
    print(f"총 {len(all_commits)}개의 커밋을 분석합니다.")
    
    hourly_commits = analyze_commit_times(all_commits)
    
    generate_commit_graph(hourly_commits)
    
    markdown_graph = generate_markdown_graph(hourly_commits)
    
    readme_path = 'README.md'
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        start_marker = "<!-- HOURLY-COMMIT-STATS:START -->"
        end_marker = "<!-- HOURLY-COMMIT-STATS:END -->"
        
        if start_marker in content and end_marker in content:
            start_index = content.find(start_marker) + len(start_marker)
            end_index = content.find(end_marker)
            new_content = content[:start_index] + "\n" + markdown_graph + "\n" + content[end_index:]
        else:
            waka_end_marker = "<!--END_SECTION:waka-->"
            if waka_end_marker in content:
                waka_end_index = content.find(waka_end_marker) + len(waka_end_marker)
                new_content = (content[:waka_end_index] + "\n\n" + 
                              start_marker + "\n" + markdown_graph + "\n" + end_marker + "\n" +
                              content[waka_end_index:])
            else:
                new_content = content + "\n\n" + start_marker + "\n" + markdown_graph + "\n" + end_marker + "\n"
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("README 파일이 업데이트되었습니다.")
        
    except Exception as e:
        print(f"README 업데이트 중 오류 발생: {e}")

if __name__ == "__main__":
    main()