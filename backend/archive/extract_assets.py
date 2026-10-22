import os
import re

html_path = r'c:\src\FinWise-ML-Projem\index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Extract CSS
style_pattern = re.compile(r'<style>(.*?)</style>', re.DOTALL)
styles = style_pattern.findall(content)

# The first style block is the main CSS
main_css = styles[0]
with open(r'c:\src\FinWise-ML-Projem\static\app.css', 'w', encoding='utf-8') as f:
    f.write(main_css.strip())

# Replace the first style block with a link tag
content = content.replace(f'<style>{main_css}</style>', '<link rel="stylesheet" href="/static/app.css">', 1)

# 2. Extract JS
script_pattern = re.compile(r'<script>(.*?)</script>', re.DOTALL)
scripts = script_pattern.findall(content)

# scripts[0] is tailwind config
# scripts[1] is appData (main logic)
# scripts[2] is chatbot logic

app_js = scripts[1]
with open(r'c:\src\FinWise-ML-Projem\static\app.js', 'w', encoding='utf-8') as f:
    f.write(app_js.strip())

chatbot_js = scripts[2]
with open(r'c:\src\FinWise-ML-Projem\static\chatbot.js', 'w', encoding='utf-8') as f:
    f.write(chatbot_js.strip())

# Replace them in HTML
content = content.replace(f'<script>{app_js}</script>', '<script src="/static/app.js"></script>', 1)
content = content.replace(f'<script>{chatbot_js}</script>', '<script src="/static/chatbot.js"></script>', 1)

# Write back to index.html
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Extraction successful.")
