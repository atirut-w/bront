from agents import Agent, TResponseInputItem, function_tool, trace, Runner
import asyncio
import json
import os
import signal
import sys
from typing import Dict, Any
from memory import Memory, MemoryNode, MemoryConnection


# Memory file configuration
MEMORY_FILE = "bront_memory.json"

# Global memory instance
long_term_memory: Memory = Memory()


def load_memory() -> None:
    """Load long-term memory from JSON file."""
    global long_term_memory
    try:
        long_term_memory = Memory.load_from_file(MEMORY_FILE)
        print(f"Loaded {len(long_term_memory)} memory entries from {MEMORY_FILE}")
    except Exception as e:
        print(f"Error loading memory file: {e}")
        long_term_memory = Memory()


def save_memory() -> None:
    """Save long-term memory to JSON file."""
    try:
        long_term_memory.save_to_file(MEMORY_FILE)
        print(f"Saved {len(long_term_memory)} memory entries to {MEMORY_FILE}")
    except Exception as e:
        print(f"Error saving memory file: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals to save memory before exit."""
    print("\nShutting down gracefully...")
    save_memory()
    sys.exit(0)


@function_tool
async def forget_memory(content_pattern: str, tags: list[str]) -> str:
    """
    Use this to forget specific memories. You can forget by content pattern or tags.
    - content_pattern: Remove memories containing this text (case-insensitive). Use empty string "" if not filtering by content.
    - tags: Remove memories that have any of these tags. Use empty list [] if not filtering by tags.
    If both content_pattern and tags are provided, memories matching either condition will be removed.
    """
    global long_term_memory
    
    if not content_pattern and not tags:
        return "Please provide either content_pattern or tags to forget specific memories."
    
    print(f"Forgetting memories with pattern: '{content_pattern}', tags: {tags}")
    
    original_count = len(long_term_memory)
    nodes_to_keep = []
    connections_to_keep = []
    forgotten_ids = set()
    
    # Find nodes to forget
    for node in long_term_memory.nodes:
        should_forget = False
        
        # Check content pattern
        if content_pattern and content_pattern.lower() in node.content.lower():
            should_forget = True
        
        # Check tags
        if tags and set(tags).intersection(node.tags):
            should_forget = True
        
        if should_forget:
            forgotten_ids.add(node.id)
            print(f"Forgetting memory [{node.id}]: {node.content[:60]}...")
        else:
            nodes_to_keep.append(node)
    
    # Keep connections that don't involve forgotten nodes
    for conn in long_term_memory.connections:
        if conn.from_id not in forgotten_ids and conn.to_id not in forgotten_ids:
            connections_to_keep.append(conn)
    
    # Update memory
    long_term_memory.nodes = nodes_to_keep
    long_term_memory.connections = connections_to_keep
    forgotten_count = original_count - len(long_term_memory)
    
    if forgotten_count > 0:
        save_memory()  # Save after forgetting
        return f"Forgot {forgotten_count} memory entries. {len(long_term_memory)} memories remain."
    else:
        return "No memories matched the criteria. Nothing was forgotten."


@function_tool
async def list_memory_tags() -> str:
    """
    Use this to get a list of all unique tags used in long-term memory.
    """
    if not long_term_memory:
        return "No memories stored, so no tags available."
    
    all_tags = long_term_memory.get_tags()
    
    if not all_tags:
        return "No tags found in stored memories."
    
    sorted_tags = sorted(all_tags)
    return f"Available tags ({len(sorted_tags)}): {', '.join(sorted_tags)}"


@function_tool
async def get_user_input() -> str:
    """
    Use this to end the current turn and get user input.
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
async def remember_memory(content: str, tags: list[str]) -> None:
    """
    Use this to remember something. This tool will store the content in long-term memory with optional tags.
    """
    # Generate a unique ID for the new node
    node_id = str(len(long_term_memory.nodes))
    node = MemoryNode(id=node_id, content=content, tags=tags)
    long_term_memory.add_node(node)
    save_memory()  # Automatically save after adding new memory
    print(f"Remembered: {content} with tags {tags}")


@function_tool
async def recall_memory(tags: list[str]) -> str:
    """
    Use this to recall something from long-term memory. This tool will return all entries that match the given tags,
    along with related memories and their relation types.
    """
    if not tags:
        return "No tags provided."
    
    recalled_items = long_term_memory.recall(tags)
    if not recalled_items:
        return "No entries found for the given tags."
    
    entries = []
    for node, is_direct_match, connections in recalled_items:
        if is_direct_match:
            # Direct match - show with tags
            entries.append(f"[{node.id}] {node.content} (tags: {', '.join(node.tags)})")
        else:
            # Related memory - show with relation type
            relation_info = []
            for conn_type, connected_id in connections:
                relation_info.append(f"{conn_type} to [{connected_id}]")
            
            relation_str = ", ".join(relation_info)
            entries.append(f"[{node.id}] {node.content} (related: {relation_str})")
    
    print(f"Recalled {len(recalled_items)} entries for tags {tags}.")
    return "\n".join(entries)


@function_tool
async def connect_memories(from_id: str, to_id: str, connection_type: str) -> str:
    """
    Use this to create a connection between two memories.
    - from_id: ID of the source memory node
    - to_id: ID of the target memory node
    - connection_type: Type of connection
    """
    try:
        connection = MemoryConnection(from_id=from_id, to_id=to_id, type=connection_type)
        long_term_memory.add_connection(connection)
        save_memory()
        print(f"Created connection: {from_id} -> {to_id} ({connection_type})")
        return f"Created {connection_type} connection from memory {from_id} to memory {to_id}"
    except ValueError as e:
        return f"Error creating connection: {e}"


@function_tool
async def disconnect_memories(from_id: str, to_id: str, connection_type: str = "") -> str:
    """
    Use this to remove a connection between two memories.
    - from_id: ID of the source memory node
    - to_id: ID of the target memory node
    - connection_type: Type of connection to remove (optional - if empty, removes all connections between the nodes)
    """
    print(f"Disconnecting memories: {from_id} -> {to_id}" + (f" ({connection_type})" if connection_type else ""))
    
    original_count = len(long_term_memory.connections)
    connections_to_keep = []
    
    for conn in long_term_memory.connections:
        should_remove = False
        
        # Check if this connection matches the criteria
        if conn.from_id == from_id and conn.to_id == to_id:
            if not connection_type or conn.type == connection_type:
                should_remove = True
        
        if not should_remove:
            connections_to_keep.append(conn)
    
    long_term_memory.connections = connections_to_keep
    removed_count = original_count - len(long_term_memory.connections)
    
    if removed_count > 0:
        print(f"Removed {removed_count} connection(s)")
        save_memory()
        if connection_type:
            return f"Removed {removed_count} '{connection_type}' connection(s) from memory {from_id} to memory {to_id}"
        else:
            return f"Removed {removed_count} connection(s) from memory {from_id} to memory {to_id}"
    else:
        print("No matching connections found")
        return f"No connections found between memory {from_id} and memory {to_id}" + (f" of type '{connection_type}'" if connection_type else "")


@function_tool
async def list_memory_connections() -> str:
    """
    List all memory connections.
    """
    connections = long_term_memory.connections
    if not connections:
        return "No memory connections found."

    connection_lines = []
    for conn in connections:
        connection_lines.append(f"[{conn.from_id}] -> [{conn.to_id}] ({conn.type})")
    return "\n".join(connection_lines)


bront = Agent(
    name="Bront",
    tools=[
        get_user_input,
        get_env_info,
        run_command,
        remember_memory,
        recall_memory,
        forget_memory,
        list_memory_tags,
        list_memory_connections,
        connect_memories,
        disconnect_memories,
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
            "content": f"""# System Instructions
This chat has been started without prior context.

## Chat interface
The system, for agentic purposes, does not automatically ask the user for input. Instead, it waits for you to call a tool to get user input. You are free to ask the user for input at any time as you see fit.

## Memory
If you need additional context, information, or things not available in this session, you can use your memory-related tools to recall and manage memories.
You have access to a long-term memory system that allows you to store and recall information. You can remember new information, recall existing memories, and manage connections between memories.
You can also forget memories based on content patterns or tags.

## Memory Status
- Total memory entries: {memory_count}
- Total unique tags: {len(long_term_memory.get_tags())}
""",
        }
    ]
    
    try:
        with trace("Bront"):
            while True:
                result = await Runner.run(
                    bront,
                    context,
                )
                print(f"Bront: {result.final_output}")
                context = result.to_input_list()
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
