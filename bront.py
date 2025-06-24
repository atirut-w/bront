from agents import Agent, TResponseInputItem, function_tool, trace, Runner
import asyncio
import json
import os
import signal
import sys
from typing import Dict, Any


class MemoryEntry:
    def __init__(self, content: str, tags: list[str]):
        self.content = content
        self.tags = tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MemoryEntry to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create MemoryEntry from dictionary (JSON deserialization)."""
        return cls(
            content=data.get("content", ""),
            tags=data.get("tags", [])
        )


# Memory file configuration
MEMORY_FILE = "bront_memory.json"

long_term_memory: list[MemoryEntry] = []


def load_memory() -> None:
    """Load long-term memory from JSON file."""
    global long_term_memory
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                long_term_memory = [MemoryEntry.from_dict(entry) for entry in data]
            print(f"Loaded {len(long_term_memory)} memory entries from {MEMORY_FILE}")
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Error loading memory file: {e}")
            long_term_memory = []
    else:
        print(f"No existing memory file found at {MEMORY_FILE}")
        long_term_memory = []


def save_memory() -> None:
    """Save long-term memory to JSON file."""
    try:
        data = [entry.to_dict() for entry in long_term_memory]
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(long_term_memory)} memory entries to {MEMORY_FILE}")
    except Exception as e:
        print(f"Error saving memory file: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals to save memory before exit."""
    print("\nShutting down gracefully...")
    save_memory()
    sys.exit(0)


@function_tool
async def forget(content_pattern: str, tags: list[str]) -> str:
    """
    Use this to forget specific memories. You can forget by content pattern or tags.
    - content_pattern: Remove memories containing this text (case-insensitive). Use empty string "" if not filtering by content.
    - tags: Remove memories that have any of these tags. Use empty list [] if not filtering by tags.
    If both content_pattern and tags are provided, memories matching either condition will be removed.
    """
    global long_term_memory
    
    if not content_pattern and not tags:
        return "Please provide either content_pattern or tags to forget specific memories."
    
    original_count = len(long_term_memory)
    memories_to_keep = []
    
    for entry in long_term_memory:
        should_forget = False
        
        # Check content pattern
        if content_pattern and content_pattern.lower() in entry.content.lower():
            should_forget = True
        
        # Check tags
        if tags and set(tags).intersection(entry.tags):
            should_forget = True
        
        if not should_forget:
            memories_to_keep.append(entry)
    
    long_term_memory = memories_to_keep
    forgotten_count = original_count - len(long_term_memory)
    
    if forgotten_count > 0:
        save_memory()  # Save after forgetting
        return f"Forgot {forgotten_count} memory entries. {len(long_term_memory)} memories remain."
    else:
        return "No memories matched the criteria. Nothing was forgotten."


@function_tool
async def list_tags() -> str:
    """
    Use this to get a list of all unique tags used in long-term memory.
    """
    if not long_term_memory:
        return "No memories stored, so no tags available."
    
    all_tags = set()
    for entry in long_term_memory:
        all_tags.update(entry.tags)
    
    if not all_tags:
        return "No tags found in stored memories."
    
    sorted_tags = sorted(list(all_tags))
    return f"Available tags ({len(sorted_tags)}): {', '.join(sorted_tags)}"


@function_tool
async def get_user_input() -> str:
    """
    Use this to get answers from the user. This tool will prompt the user for input and return their response.
    """
    return input("> ")


@function_tool
async def get_env_info() -> str:
    """
    Use this to get information about the environment. This tool will return the current environment variables.
    """
    import os

    return str(os.environ)

@function_tool
async def read_file(path: str) -> str:
    """
    Use this to read the contents of a file.
    - path: The path to the file to read.
    Returns the file contents as a string, or an error message if the file cannot be read.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{path}': {e}"

@function_tool
async def write_file(path: str, content: str) -> str:
    """
    Use this to write content to a file.
    - path: The path to the file to write.
    - content: The content to write to the file.
    Overwrites the file if it exists, or creates it if it does not.
    Returns a success or error message.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to file '{path}'."
    except Exception as e:
        return f"Error writing to file '{path}': {e}"

@function_tool
async def diff_edit_file(path: str, search: str, replace: str) -> str:
    """
    Use this to edit a file by replacing a specific block of text.
    - path: The path to the file to edit.
    - search: The exact text to search for in the file.
    - replace: The text to replace the search block with.
    Returns a success or error message.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if search not in content:
            return f"Search text not found in '{path}'. No changes made."
        new_content = content.replace(search, replace, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Successfully replaced text in '{path}'."
    except Exception as e:
        return f"Error editing file '{path}': {e}"

@function_tool
async def run_command(command: str) -> str:
    """
    Use this to run a shell command. This tool will execute the command and return its output.
    """
    import subprocess

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else result.stderr



@function_tool
async def remember(content: str, tags: list[str]) -> None:
    """
    Use this to remember something. This tool will store the content in long-term memory with optional tags.
    """
    long_term_memory.append(MemoryEntry(content, tags))
    save_memory()  # Automatically save after adding new memory
    print(f"Remembered: {content} with tags {tags}")


@function_tool
async def recall(tags: list[str]) -> str:
    """
    Use this to recall something from long-term memory. This tool will return all entries that match the given tags.
    """
    if not tags:
        return "No tags provided."
    
    entries = [entry.content for entry in long_term_memory if set(tags).intersection(entry.tags)]
    return "\n".join(entries) if entries else "No entries found for the given tags."


bront = Agent(
    name="Bront",
    tools=[
        get_user_input,
        get_env_info,
        run_command,
        remember,
        recall,
        forget,
        list_tags,
        read_file,
        write_file,
        diff_edit_file,
    ],
)
context: list[TResponseInputItem] = []


async def main():
    global context
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load memory at startup
    load_memory()
    
    # Initialize context with memory information
    memory_count = len(long_term_memory)
    context = [
        {
            "role": "system",
            "content": f"Chat started. You can get user input using the get_user_input tool. Your long-term memory is automatically loaded from and saved to 'bront_memory.json'. You currently have {memory_count} memories stored. Use the remember tool to store information, recall to retrieve it, and forget to remove specific memories.",
        }
    ]
    
    try:
        with trace("Bront"):
            while True:
                result = await Runner.run(
                    bront,
                    context,
                )
                context = result.to_input_list()
                print(result.final_output)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        save_memory()
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        save_memory()  # Save memory even on unexpected errors
        raise


if __name__ == "__main__":
    asyncio.run(main())
