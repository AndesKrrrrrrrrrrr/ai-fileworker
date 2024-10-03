import argparse
from openai import OpenAI
import yaml
import glob
import os
import pathspec


def load_config(config_path):
    """Load configuration from the YAML file and merge with environment variables."""
    # Load config from file
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    # Override or set values from environment variables if present
    config["api_key"] = os.getenv("OPENAI_API_KEY", config.get("api_key"))
    config["model"] = os.getenv("OPENAI_MODEL", config.get("model", "gpt-4-turbo"))

    return config


def process_file(file_path, model, action, api_key, in_place):
    """Perform a requested action using OpenAI's API on a single file."""

    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    with open(file_path, "r") as file:
        file_content = file.read()

    if in_place:
        # If editing in-place, just get the result without streaming
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": action},
                {
                    "role": "user",
                    "content": f"{file_content}\n\n# Please only return the modified file content, and nothing else.",
                },
            ],
            model=model,
        )
        output = (chat_completion.choices[0].message.content or "").strip()

        # Write the output back to the file (in-place modification)
        with open(file_path, "w") as file:
            file.write(output)
        print(f"Updated file: {file_path}")
    else:
        # Stream output to stdout
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": action},
                {
                    "role": "user",
                    "content": f"{file_content}\n\n# Please only return the modified code, with no additional explanations or preface.",
                },
            ],
            model=model,
            stream=True,
        )
        print(f"Output for {file_path}:")
        for chunk in response:
            chunk_content = chunk.choices[0].delta.content or ""
            if chunk_content:
                print(chunk_content, end="")


def parse_cli_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Process files using OpenAI API.")
    parser.add_argument(
        "file_paths",
        metavar="file",
        type=str,
        nargs="+",
        help="File paths or glob patterns to process",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to the configuration YAML file (default: config.yaml)",
    )
    parser.add_argument(
        "--action", "-a", type=str, help="Custom action to perform (optional)"
    )
    parser.add_argument(
        "--in-place",
        "-i",
        "-w",
        action="store_true",
        help="Edit the files in-place instead of printing the output",
    )
    parser.add_argument(
        "--dry",
        "-n",
        action="store_true",
        help="Show which files would be modified without making changes",
    )

    return parser.parse_args()


def get_gitignore_spec():
    """Load gitignore rules and return a pathspec for filtering."""
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as gitignore:
            return pathspec.PathSpec.from_lines("gitwildmatch", gitignore)
    return None


def main():
    args = parse_cli_args()

    # Load configuration
    config = load_config(args.config)

    # Get OpenAI settings from config
    model = config.get("model")
    api_key = config.get("api_key")

    if not model or not api_key:
        print("Error: Config file must include both 'model' and 'api_key'.")
        return

    # Handle action input (if not provided via CLI, prompt the user)
    action = args.action or input("Enter the action you want to perform: ")

    # Initialize gitignore pathspec (if a .gitignore exists)
    gitignore_spec = get_gitignore_spec()

    # Expand file paths from globs (recursively), excluding git-ignored files
    file_paths = []
    print(f"Scanning files: {args.file_paths}")
    for file_pattern in args.file_paths:
        matched_files = glob.glob(file_pattern, recursive=True)

        # If gitignore rules exist, filter out ignored files
        if gitignore_spec:
            matched_files = [
                f for f in matched_files if not gitignore_spec.match_file(f)
            ]

        file_paths.extend(matched_files)
    print(f"Found {len(file_paths)} files to process")

    # Process each file
    for file_path in file_paths:
        if os.path.isfile(file_path):
            if args.dry:
                print(f"Would modify: {file_path}")
            else:
                process_file(file_path, model, action, api_key, args.in_place)
        else:
            print(f"File not found: {file_path}")


if __name__ == "__main__":
    main()
