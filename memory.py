class MemoryNode:
    def __init__(self, id: str, content: str, tags: list[str]):
        self.id = id
        self.content = content
        self.tags = tags

    def to_dict(self) -> dict:
        """Convert MemoryNode to dictionary for JSON serialization."""
        return {"id": self.id, "content": self.content, "tags": self.tags}

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryNode":
        """Create MemoryNode from dictionary (JSON deserialization)."""
        return cls(id=data["id"], content=data["content"], tags=data["tags"])


class MemoryConnection:
    def __init__(self, from_id: str, to_id: str, type: str):
        self.from_id = from_id
        self.to_id = to_id
        self.type = type

    def to_dict(self) -> dict:
        """Convert MemoryConnection to dictionary for JSON serialization."""
        return {"from_id": self.from_id, "to_id": self.to_id, "type": self.type}

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryConnection":
        """Create MemoryConnection from dictionary (JSON deserialization)."""
        return cls(from_id=data["from_id"], to_id=data["to_id"], type=data["type"])


class Memory:
    def __init__(self):
        self.nodes: list[MemoryNode] = []
        self.connections: list[MemoryConnection] = []

    def add_node(self, node: MemoryNode) -> None:
        """Add a node to the memory."""
        self.nodes.append(node)

    def add_connection(self, connection: MemoryConnection) -> None:
        """Add a connection between nodes in the memory."""
        # Make sure both nodes exist before adding the connection
        if any(n.id == connection.from_id for n in self.nodes) and any(
            n.id == connection.to_id for n in self.nodes
        ):
            self.connections.append(connection)
        else:
            raise ValueError("Both nodes must exist in memory to create a connection.")

    def get_tags(self) -> list[str]:
        """Get all unique tags from the memory nodes."""
        tags = set()
        for node in self.nodes:
            tags.update(node.tags)
        return list(tags)

    def recall(self, tags: list[str]) -> list[tuple]:
        """
        Recall nodes that match the given tags.

        Returns a list of tuples, each containing:
        - node: The MemoryNode object
        - is_direct_match: Boolean indicating if the node was directly matched by tags
        - connections: List of connection details (only for related nodes)
          Each connection is a tuple of (connection_type, connected_node_id)
        """
        # Find nodes that match the given tags
        matched_nodes = []
        matched_ids = set()
        for node in self.nodes:
            if set(tags).intersection(node.tags):
                matched_nodes.append(node)
                matched_ids.add(node.id)

        # Create a lookup dictionary for better performance
        node_lookup = {node.id: node for node in self.nodes}

        # Prepare result list with direct matches
        result = [(node, True, []) for node in matched_nodes]

        # Find and add related nodes with connection information
        related_nodes = {}  # Dictionary to track related nodes and their connections

        for conn in self.connections:
            # Check connections from matched nodes to other nodes
            if conn.from_id in matched_ids and conn.to_id not in matched_ids:
                if conn.to_id not in related_nodes:
                    related_nodes[conn.to_id] = []
                related_nodes[conn.to_id].append((conn.type, conn.from_id))

            # Check connections from other nodes to matched nodes
            elif conn.to_id in matched_ids and conn.from_id not in matched_ids:
                if conn.from_id not in related_nodes:
                    related_nodes[conn.from_id] = []
                related_nodes[conn.from_id].append((conn.type, conn.to_id))

        # Add related nodes to result
        for node_id, connections in related_nodes.items():
            if node_id in node_lookup:
                result.append((node_lookup[node_id], False, connections))

        return result

    def __len__(self) -> int:
        """Return the number of nodes in memory."""
        return len(self.nodes)

    def __iter__(self):
        """Make Memory iterable over nodes."""
        return iter(self.nodes)

    def to_dict(self) -> dict:
        """Convert Memory to dictionary for JSON serialization."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": [conn.to_dict() for conn in self.connections],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        """Create Memory from dictionary (JSON deserialization)."""
        memory = cls()
        memory.nodes = [
            MemoryNode.from_dict(node_data) for node_data in data.get("nodes", [])
        ]
        memory.connections = [
            MemoryConnection.from_dict(conn_data)
            for conn_data in data.get("connections", [])
        ]
        return memory

    def save_to_file(self, filepath: str) -> None:
        """Save memory to JSON file."""
        import json

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, filepath: str) -> "Memory":
        """Load memory from JSON file."""
        import json
        import os

        if not os.path.exists(filepath):
            return cls()  # Return empty memory if file doesn't exist

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
