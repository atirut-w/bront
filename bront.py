from agents import Agent, TResponseInputItem, function_tool, trace, Runner
import asyncio


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
async def run_command(command: str) -> str:
    """
    Use this to run a shell command. This tool will execute the command and return its output.
    """
    import subprocess
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else result.stderr


bront = Agent(
    name="Bront",
    tools=[
        get_user_input,
        get_env_info,
        run_command,
    ],
)
context: list[TResponseInputItem] = [
    {
        "role": "system",
        "content": "Chat started. You can get user input using the get_user_input tool.",
    }
]


async def main():
    global context
    with trace("Bront"):
        while True:
            result = await Runner.run(
                bront,
                context,
            )
            context = result.to_input_list()
            print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
