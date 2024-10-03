from typing import TypedDict, Union
import glob
import os
import yaml
from pathlib import Path
from openai import OpenAI
import pathspec

PROJECT_NAME = "ai-fileworker"


class Config(TypedDict, total=False):
    api_key: str
    model: str
    api_base_url: str
    action: str
    in_place: Union[bool, str]  # Can be bool or str when loaded from environment


def load_config(config_filename: str = "config.yaml") -> Config:
    """Load configuration from environment variables and YAML file. Search in current directory and XDG config directory."""

    # Search for config file in current directory and XDG config directory
    config_path = Path(config_filename)
    if not config_path.exists():
        xdg_config_home = Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser()
        config_path = xdg_config_home / PROJECT_NAME / config_filename

    # Load config from file if it exists
    config: Config = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

    # Define a mapping of config keys to environment variable names
    env_var_mapping = {
        "api_key": "API_KEY",
        "model": "MODEL",
        "api_base_url": "API_BASE_URL",
        "action": "ACTION",
        "in_place": "IN_PLACE",
    }

    # Loop through the mapping and set values from environment variables, with precedence over config file
    for config_key, env_var in env_var_mapping.items():
        env_value = os.getenv(env_var)

        # Special handling for boolean conversion
        if config_key in ("in_place", "is_verbose"):
            env_value = (
                (str(env_value).lower() in ("yes", "true", "1", "on"))
                if env_value is not None
                else None
            )
        config[config_key] = env_value or config.get(config_key)

    # Set default values if not provided in config or environment
    config.setdefault("model", "gpt-4-turbo")
    config.setdefault("api_base_url", "https://api.openai.com/v1")
    config.setdefault("action", "Summarize this text")

    return config


def process_file(file_path: str, config: Config) -> None:
    """Perform a requested action using OpenAI's API on a single file."""

    # Extract values from the config dictionary
    model = config.get("model") or ""
    action = config.get("action") or ""
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_base_url = config.get("api_base_url")
    in_place = config.get("in_place")

    # Initialize the OpenAI client with the base URL
    client = OpenAI(api_key=api_key, base_url=api_base_url)

    with open(file_path, "r") as file:
        file_content = file.read()

    ai_args = {
        "messages": [
            {"role": "system", "content": action},
            {
                "role": "user",
                "content": f"{file_content}\n\n# Please only return the modified file content, and nothing else.",
            },
        ],
        "model": model,
        "stream": not in_place,
    }

    chat_completion = client.chat.completions.create(**ai_args)

    if in_place:
        # If editing in-place, just get the result without streaming
        output = (chat_completion.choices[0].message.content or "").strip()

        # Write the output back to the file (in-place modification)
        with open(file_path, "w") as file:
            file.write(output)
        print(f"Updated file: {file_path}")
    else:
        # Stream output to stdout
        response = client.chat.completions.create(**ai_args)
        print(f"Output for {file_path}:")
        for chunk in response:
            chunk_content = chunk.choices[0].delta.content or ""
            if chunk_content:
                print(chunk_content, end="")


def parse_cli_args():
    """Parse command line arguments."""
    import argparse

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
    parser.add_argument(
        "--api-base-url",
        "-u",
        type=str,
        help="Set a custom OpenAI API base URL (optional)",
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

    if args.action:
        # Handle action input (if not provided via CLI, prompt the user)
        args.action = args.action or input("Enter the action you want to perform: ")
        config["action"] = args.action
    if args.api_base_url:
        config["api_base_url"] = args.api_base_url
    if args.in_place is not None:
        config["in_place"] = args.in_place

    # Get OpenAI settings from config
    model = config.get("model")
    api_key = config.get("api_key")

    if not model or not api_key:
        print("Error: Config file must include both 'model' and 'api_key'.")
        return

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
    print(f"Found {len(file_paths)} files to process: {file_paths}")
    args.file_paths = file_paths

    # Process each file
    for file_path in args.file_paths:
        if os.path.isfile(file_path):
            if args.dry:
                print(f"Would modify: {file_path}")
            else:
                process_file(file_path, config)
        else:
            print(f"File not found: {file_path}")


if __name__ == "__main__":
    main()
