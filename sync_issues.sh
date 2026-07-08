#!/bin/bash

# Define the local issue storage directory
ISSUE_DIR=".github/issues"

echo "🔄 Syncing local workspace with live GitHub issues..."

# 1. Clean out the old local tracking files to remove closed/completed tasks
if [ -d "$ISSUE_DIR" ]; then
    echo "🧹 Purging old local tracking files..."
    rm -f "$ISSUE_DIR"/issue-*.md
else
    mkdir -p "$ISSUE_DIR"
fi

# 2. Fetch active open issues using the safe JSON data channel
echo "📥 Fetching current open issues from GitHub..."
RAW_ISSUES=$(gh issue list --state open --limit 50 --json number,title,body,createdAt,author 2>/dev/null)

# Verify if the GitHub CLI returned a valid array or if it's empty
if [ -z "$RAW_ISSUES" ] || [ "$RAW_ISSUES" == "[]" ]; then
    echo "✅ No open issues found. Your local issue folder is clean!"
    exit 0
fi

# 3. Process the live issues and write them out as Markdown
echo "$RAW_ISSUES" | jq -c '.[]' | while read -r row; do
  num=$(echo "$row" | jq -r '.number')
  title=$(echo "$row" | jq -r '.title')
  author=$(echo "$row" | jq -r '.author.login')
  date=$(echo "$row" | jq -r '.createdAt')
  body=$(echo "$row" | jq -r '.body')

  # Write out a clean, properly formatted markdown file
  cat << EOF > "$ISSUE_DIR/issue-$num.md"
# Issue #$num: $title
- **Author:** $author
- **Created:** $date

## Description
$body
EOF
done

echo "🎉 Done! Your local issue backlog is perfectly up to date."
