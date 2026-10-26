# LinkedIn API JSON Parser

Convert LinkedIn profile JSON data into viewable LinkedIn-style HTML pages.

## Tools

### 1. Web Converter (converter.html)

A two-page browser tool to convert JSON without needing command line setup.

- Page 1: Paste LinkedIn profile JSON directly and click Convert.
- Page 2: View full-page LinkedIn profile preview, open in a new tab, or download the HTML file.
- Works offline in any modern web browser.

Usage:
Double-click converter.html or open it in your browser.

### 2. CLI Tool (linkedin_to_html.py)

A zero-dependency Python script to convert JSON files or stdin pipelines.

Usage:
```bash
python linkedin_to_html.py input.json -o profile.html
python linkedin_to_html.py input.json --open
type input.json | python linkedin_to_html.py > profile.html
```

Options:
- input: Path to the JSON file, or '-' to read from stdin.
- -o, --output: Path for the generated HTML file.
- --open: Automatically open the output HTML file in the default browser.
- -h, --help: Show command help and options.

Supported JSON input formats:
- Scraper wrappers with data.profile
- Wrappers with profile
- Direct profile objects with fields like fullName, headline, summary, positions, education, skills, certifications
