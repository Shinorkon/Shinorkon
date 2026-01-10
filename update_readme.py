#!/usr/bin/env python3
"""
Script to automatically update README.md with latest repository information
"""
import json
import sys
from datetime import datetime

def format_repo_data(repos):
    """Format repository data for README"""
    # Sort repos by updated_at date (most recent first)
    repos.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    
    # Group by language
    language_counts = {}
    for repo in repos:
        lang = repo.get('language') or 'Other'
        language_counts[lang] = language_counts.get(lang, 0) + 1
    
    return repos, language_counts

def generate_featured_projects(repos):
    """Generate featured projects section"""
    featured = []
    
    # Find specific repos to feature
    featured_names = ['Event_Planner', 'Shnuk', 'Project', 'Discord_bot', 'panels-dev', 'PracticalExam']
    
    for name in featured_names:
        repo = next((r for r in repos if r['name'] == name), None)
        if repo:
            featured.append(repo)
    
    return featured

def generate_readme_content(repos_data):
    """Generate complete README content"""
    repos, language_counts = format_repo_data(repos_data)
    featured = generate_featured_projects(repos)
    
    # Get descriptions for featured repos
    featured_descriptions = {
        'Event_Planner': 'A Next.js-based event planning application built with TypeScript. Features a modern UI and comprehensive event management capabilities.',
        'Shnuk': 'A mobile nutrition and meal tracking app designed for Maldivians. Features traditional Maldivian foods, bilingual support (English/Dhivehi), and comprehensive nutrition tracking.',
        'Project': 'A full-featured TypeScript project showcasing modern web development practices.',
        'Discord_bot': 'A Discord bot built with Go, demonstrating backend development skills.',
        'panels-dev': 'Development project for building reusable UI panels and components.',
        'PracticalExam': 'Python practical test showcasing problem-solving skills.'
    }
    
    featured_tech = {
        'Event_Planner': 'TypeScript, Next.js, React',
        'Shnuk': 'Python, Dart, Flutter, FastAPI, PostgreSQL',
        'Project': 'TypeScript',
        'Discord_bot': 'Go',
        'panels-dev': 'TypeScript',
        'PracticalExam': 'Python'
    }
    
    readme = """# Hi there, I'm Falulaan! 👋

Welcome to my GitHub profile! I'm a passionate developer who loves building modern web applications and exploring various technologies.

## 🚀 About Me

I'm a software developer with experience across multiple programming languages and frameworks. I enjoy creating practical solutions and learning new technologies along the way.

## 💻 Featured Projects

"""
    
    # Add featured projects
    for repo in featured:
        name = repo['name']
        url = repo['html_url']
        desc = featured_descriptions.get(name, repo.get('description', 'A featured project'))
        tech = featured_tech.get(name, repo.get('language', 'Multiple'))
        
        emoji_map = {
            'Event_Planner': '🎯',
            'Shnuk': '🍽️',
            'Project': '📦',
            'Discord_bot': '🤖',
            'panels-dev': '🎨',
            'PracticalExam': '🐍'
        }
        emoji = emoji_map.get(name, '📁')
        
        readme += f"### {emoji} [{name}]({url})\n"
        readme += f"{desc}\n"
        readme += f"- **Tech Stack**: {tech}\n"
        if name == 'Event_Planner':
            readme += "- **Status**: Active Development\n"
        elif name == 'Shnuk':
            readme += "- **Status**: Active Development\n"
            readme += "- **Features**: Calorie tracking, meal logging, traditional Maldivian food database\n"
        readme += "\n"
    
    readme += """## 🛠️ Technology Stack

### Languages
![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![JavaScript](https://img.shields.io/badge/-JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Dart](https://img.shields.io/badge/-Dart-0175C2?style=flat-square&logo=dart&logoColor=white)
![Go](https://img.shields.io/badge/-Go-00ADD8?style=flat-square&logo=go&logoColor=white)

### Frameworks & Libraries
![Flutter](https://img.shields.io/badge/-Flutter-02569B?style=flat-square&logo=flutter&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/-Next.js-000000?style=flat-square&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/-React-61DAFB?style=flat-square&logo=react&logoColor=black)
![Node.js](https://img.shields.io/badge/-Node.js-339933?style=flat-square&logo=node.js&logoColor=white)

## 📊 GitHub Stats

![Shinorkon's GitHub stats](https://github-readme-stats.vercel.app/api?username=Shinorkon&show_icons=true&theme=radical)

## 📈 Repository Overview

### By Language
"""
    
    # Add language counts
    for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
        readme += f"- **{lang}**: {count} repositor{'y' if count == 1 else 'ies'}\n"
    
    readme += f"\n### Total Public Repositories: {len(repos)}\n\n"
    
    readme += """## 🔗 All My Repositories

| Repository | Language | Description | Stars |
|------------|----------|-------------|-------|
"""
    
    # Add all repos to table
    for repo in repos:
        name = repo['name']
        url = repo['html_url']
        lang = repo.get('language') or '-'
        desc = repo.get('description') or f"{lang} project"
        if len(desc) > 60:
            desc = desc[:57] + "..."
        stars = repo.get('stargazers_count', 0)
        
        readme += f"| [{name}]({url}) | {lang} | {desc} | ⭐ {stars} |\n"
    
    readme += """
## 📫 Connect with Me

Feel free to explore my repositories and reach out if you'd like to collaborate on any projects!

---

*This profile is automatically updated to reflect my latest work and contributions.*
"""
    
    return readme

def main():
    """Main function"""
    # Read repos data from stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            repos_data = json.load(f)
    else:
        repos_data = json.load(sys.stdin)
    
    # Generate README content
    readme_content = generate_readme_content(repos_data)
    
    # Write to README.md
    with open('README.md', 'w') as f:
        f.write(readme_content)
    
    print("README.md updated successfully!")

if __name__ == '__main__':
    main()
