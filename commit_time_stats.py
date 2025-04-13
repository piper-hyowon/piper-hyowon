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
        try:
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
                except Exception as e:
                    print(f"커밋 데이터 처리 중 오류: {e}")
                    continue
            
            page += 1
        except Exception as e:
            print(f"저장소 {repo_name} API 요청 중 오류: {e}")
            break
    
    print(f"{repo_name}: {len(commits)}개의 커밋을 가져왔습니다.")
    return commits

def analyze_commit_times(all_commits):
    hourly_commits = defaultdict(int)
    
    for commit_date in all_commits:
        try:
            dt = datetime.datetime.strptime(commit_date, '%Y-%m-%dT%H:%M:%SZ')
            kr_hour = (dt.hour + 9) % 24
            hourly_commits[kr_hour] += 1
        except Exception as e:
            print(f"날짜 분석 중 오류: {e}, 날짜: {commit_date}")
            continue
    
    return dict(hourly_commits)

def generate_commit_graph(hourly_commits):
    try:
        hours = list(range(24))
        
        counts = []
        for hour in hours:
            if hour in hourly_commits:
                counts.append(hourly_commits[hour])
            else:
                counts.append(0)
        
        if sum(counts) == 0:
            print("커밋 데이터가 없습니다.")
            return
        
        colors = []
        for hour in hours:
            if 5 <= hour < 9: 
                colors.append('#FF9D6C')
            elif 9 <= hour < 12: 
                colors.append('#FFCD56')
            elif 12 <= hour < 18:
                colors.append('#4BC0C0')
            elif 18 <= hour < 22:
                colors.append('#36A2EB')
            else:
                colors.append('#9966FF')
        
        plt.figure(figsize=(12, 6))
        plt.style.use('ggplot')
        
        bars = plt.bar(hours, counts, color=colors, width=0.8, alpha=0.7)
        
        plt.title('Hourly Commit Distribution (KST)', fontsize=16, fontweight='bold')
        plt.xlabel('Hour of Day', fontsize=12)
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
    except Exception as e:
        print(f"그래프 생성 중 오류 발생: {e}")

def main():
    try:
        repos = get_user_repos()
        
        print(f"총 {len(repos)}개의 저장소를 찾았습니다.")
        
        all_commits = []
        for repo in repos:
            commits = get_commits_for_repo(repo)
            all_commits.extend(commits)
        
        print(f"총 {len(all_commits)}개의 커밋을 분석합니다.")
        
        hourly_commits = analyze_commit_times(all_commits)
        
        print("시간대별 커밋 수:")
        for hour in range(24):
            print(f"{hour:02d}시: {hourly_commits.get(hour, 0)}개")
        
        generate_commit_graph(hourly_commits)
        
        try:
            readme_path = 'README.md'
            
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            start_marker = "<!-- HOURLY-COMMIT-GRAPH:START -->"
            end_marker = "<!-- HOURLY-COMMIT-GRAPH:END -->"
            
            if start_marker in content and end_marker in content:
                start_index = content.find(start_marker) + len(start_marker)
                end_index = content.find(end_marker)
                new_content = (content[:start_index] + 
                              "\n![Hourly Commit Distribution](./commit_time_stats.png)\n" + 
                              content[end_index:])
            else:
                waka_end_marker = "<!--END_SECTION:waka-->"
                if waka_end_marker in content:
                    waka_end_index = content.find(waka_end_marker) + len(waka_end_marker)
                    
                    if start_marker in content:
                        print("마커가 이미 존재하지만, 마커 쌍이 완전하지 않습니다. 수정하지 않습니다.")
                        return
                    
                    new_content = (content[:waka_end_index] + "\n\n" + 
                                  start_marker + "\n" +
                                  "![Hourly Commit Distribution](./commit_time_stats.png)\n" + 
                                  end_marker + "\n" +
                                  content[waka_end_index:])
                else:
                    if start_marker in content:
                        print("마커가 이미 존재하지만, 마커 쌍이 완전하지 않습니다. 수정하지 않습니다.")
                        return
                    
                    new_content = (content + "\n\n" + 
                                  start_marker + "\n" +
                                  "![Hourly Commit Distribution](./commit_time_stats.png)\n" + 
                                  end_marker + "\n")
            
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("README 업데이트가 완료되었습니다.")
            
        except Exception as e:
            print(f"README 업데이트 중 오류 발생: {e}")
    
    except Exception as e:
        print(f"스크립트 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()