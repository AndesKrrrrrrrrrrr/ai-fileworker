# OpenAI File Processor CLI

A simple command-line tool that processes text files using OpenAI's API. It allows
users to apply custom actions to files (e.g., summarization, code modification)
and outputs the result either to stdout or edits the file in place. Supports recursive
file globbing and respects `.gitignore` rules.

## Features

- Process files using custom actions with OpenAI's API.
- Modify files in place or output to stdout.
- Recursively match file paths.
- Exclude files ignored by `.gitignore`.
- Dry-run option to show which files would be modified without making changes.

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/openai-file-processor.git
   cd openai-file-processor
   ```

2. **Install dependencies**:

   Ensure you have Python installed, then run:

   ```bash
   pip install -r requirements.txt
   ```

3. **(Optional) Install `PyInstaller`**:

   To create a standalone binary:

   ```bash
   pip install pyinstaller
   ```

4. **Create a binary** (optional):

   ```bash
   pyinstaller --onefile main.py
   ```

## Usage

### Basic Usage

```bash
python main.py "path/to/files/*.txt" \
  --config config.yaml \
  --action "Summarize this text"
```

### In-place Modification

```bash
python main.py "path/to/files/*.txt" \
  --config config.yaml
  --action "Refactor the following code" \
  --in-place
```

### Dry-run Mode

To see which files would be modified without making changes:

```bash
python main.py "path/to/files/**/*.txt" --config config.yaml --dry
```

### Help

```bash
python main.py --help
```

### Example Command for the Binary

If you created the standalone binary with `PyInstaller`, you can run it like this:

```bash
./dist/main --config config.yaml --action "Fix grammar" "documents/**/*.md"
```

## Configuration

By default, the tool looks for a `config.yaml` file to load the OpenAI API key and
model. You can provide this file, or use environment variables (`OPENAI_API_KEY`
and `OPENAI_MODEL`).

### Example `config.yaml`

```yaml
model: "gpt-4"
api_key: "your-openai-api-key"
```

Alternatively, set the environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL="gpt-4"
```

## License

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for details.

