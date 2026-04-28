#!/usr/bin/env bash
################################################################################
# Library: wiki-common.sh
# Description: Shared utilities for Mnemosyne wiki maintenance scripts
# Author: James Stacy
# Version: 1.0.0
#
# Source this file; do not execute directly.
################################################################################

readonly WIKI_DIR="$(cd \
	"$(dirname "${BASH_SOURCE[0]}")/../../wiki" && pwd)"
readonly REPORTS_DIR="$WIKI_DIR/reports"
readonly LOG_FILE="$WIKI_DIR/log.md"
readonly INDEX_FILE="$WIKI_DIR/index.md"
readonly BUCKET_DIRS=(
	ideas admin reference journal people projects pursuits
)

# Models for --enrich mode
readonly HAIKU_MODEL='claude-haiku-4-5-20251001'
readonly SONNET_MODEL='claude-sonnet-4-6'

log_info() {
	echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

log_error() {
	echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

# Outputs null-delimited paths to all .md files in the 7 bucket directories
find_wiki_files() {
	local bucket
	for bucket in "${BUCKET_DIRS[@]}"; do
		local dir="$WIKI_DIR/$bucket"
		[[ -d $dir ]] || continue
		find "$dir" -maxdepth 1 -name '*.md' -print0
	done
}

# Populates an associative array: page_title -> 1 for all wiki pages
# Usage: load_page_titles myarray
load_page_titles() {
	local -n _ref=$1
	local f title
	# Bucket directories + _templates/ (bucket hub pages live there)
	while IFS= read -r -d '' f; do
		title="${f##*/}"
		title="${title%.md}"
		_ref["$title"]=1
	done < <(
		find_wiki_files
		find "$WIKI_DIR/_templates" -maxdepth 1 -name '*.md' -print0 \
			2>/dev/null
	)
}

# Outputs wikilink titles from a file, one per line
# Handles [[Title]] and [[Title|Alias]] — outputs Title only
extract_wikilinks() {
	local file=$1
	grep -oE '\[\[[^]]+\]\]' "$file" 2>/dev/null \
		| sed 's/^\[\[//; s/\]\]$//; s/|.*//'
}

# Extracts a single YAML frontmatter field value
# Usage: get_frontmatter_field <file> <field>
get_frontmatter_field() {
	local file=$1
	local field=$2
	awk -v f="$field" '
		BEGIN { fm=0 }
		/^---$/ { fm++; next }
		fm == 1 && $0 ~ "^" f ": " {
			sub("^" f ": ", ""); print; exit
		}
		fm >= 2 { exit }
	' "$file"
}

# Counts words in file body (content after frontmatter)
count_body_words() {
	local file=$1
	awk '
		BEGIN { fm=0 }
		/^---$/ { fm++; next }
		fm >= 2 { print }
	' "$file" | wc -w
}

# Converts a hyphenated slug to Title Case
# Usage: slug_to_title "ghost-links"  →  "Ghost Links"
slug_to_title() {
	local slug=$1
	local result='' word
	IFS=- read -ra words <<< "$slug"
	for word in "${words[@]}"; do
		result+="${word^} "
	done
	printf '%s' "${result% }"
}

# Writes a report to reports/ and appends a line to log.md
# Usage: write_report <slug> <date> <body>
write_report() {
	local slug=$1
	local report_date=$2
	local body=$3
	local filename="${slug}-report-${report_date}.md"
	local filepath="$REPORTS_DIR/$filename"
	local title
	title="$(slug_to_title "$slug") Report"
	local timestamp
	timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

	{
		printf -- '---\n'
		printf 'report: %s\n' "$slug"
		printf 'generated: %s\n' "$report_date"
		printf 'source: maintenance-script\n'
		printf -- '---\n\n'
		printf '%s\n' "$body"
	} > "$filepath"

	printf '%s | report | — | %s — %s | maintenance-script\n' \
		"$timestamp" "$title" "$report_date" \
		>> "$LOG_FILE"

	log_info "Report written: $filename"
}
