import os
import re

template_dir = 'app/templates'

for filename in os.listdir(template_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(template_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Fix pattern: url_for('blueprint.endpoint'', ...) -> url_for('blueprint.endpoint', ...)
        content = re.sub(r"url_for\('([^']+)''", r"url_for('\1'", content)
        content = re.sub(r'url_for\("([^"]+)""', r'url_for("\1"', content)
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Fixed: {filename}")
        else:
            print(f"No changes: {filename}")

print("\nDone!")
