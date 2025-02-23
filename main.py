from fastapi import FastAPI
import openai
import requests
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format=
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
)
logger = logging.getLogger(__name__)

# Add file handler for persistent logs
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = FastAPI()

OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY")  # Get API key from environment variable
REPLIT_API_URL = "https://replit.com/api/v1/execute"

client = openai.OpenAI(api_key=OPENAI_API_KEY)  # Updated client initialization


def suggest_stack(task: str) -> str:
    """Asks OpenAI to suggest the best possible stack based on the project requirements."""
    logger.debug(f"Starting stack suggestion for task: {task}")
    logger.info(f"Suggesting tech stack for task: {task}")
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{
            "role":
            "user",
            "content":
            f"Suggest the best tech stack for this project: {task}. Include frontend, backend, mobile (if applicable), and any required libraries."
        }],
    )
    logger.debug(f"Stack suggestion response: {response}")
    content = response.choices[0].message.content
    if content is None:
        return "Unknown stack"  # Return a default value
    return content


def generate_code(task: str, stack: str) -> str:
    """Asks OpenAI to generate full-stack web app code based on the chosen stack."""
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{
            "role":
            "user",
            "content":
            f"Generate a application for {task}. Use {stack} and apply best practices."
        }],
    )
    logger.debug(f"Code generation response: {response}")
    content = response.choices[0].message.content
    if content is None:
        return "Unknown code"  # Return a default value
    return content


def execute_code(code: str):
    """Executes the generated code on Replit."""
    logger.debug(f"Attempting to execute code at: {datetime.now()}")
    try:
        response = requests.post(REPLIT_API_URL,
                                 json={
                                     "language": "python",
                                     "code": code
                                 })
        if response.status_code == 200:
            logger.info("Code execution successful")
            return response.json()
        else:
            logger.error(
                f"Code execution failed with status code: {response.status_code}"
            )
            return {
                "error": f"Execution failed with status {response.status_code}"
            }
    except Exception as e:
        logger.exception("Exception during code execution")
        return {"error": str(e)}


def refine_code(task: str, stack: str, prev_code: str,
                execution_result: str) -> str:
    """Asks OpenAI to improve the generated application code based on execution results."""
    refinement_prompt = (
        f"The following full-stack application code was generated for task: {task}\n"
        f"Stack: {stack}\n"
        f"Code:\n{prev_code}\n"
        f"Execution Result:\n{execution_result}\n"
        f"Please improve the code to fix errors and optimize performance.")
    return generate_code(refinement_prompt, stack)


@app.post("/generate_and_run_code/")
async def generate_and_run_code(task: str = "A ToDo App",
                                stack: str = "Angular"):
    logger.info(f"Received code generation request - Task: {task}")
    logger.debug(f"Parameters - Stack: {stack}")
    if not stack:
        stack = suggest_stack(task)

    code = generate_code(task, stack)

    execution_result = execute_code(code)

    if "error" in execution_result:
        logger.error(f"Execution error: {execution_result['error']}")
        improved_code = refine_code(task, stack, code,
                                    execution_result["error"])
        return {
            "error": execution_result["error"],
            "improved_code": improved_code
        }

    return {"generated_code": code, "execution_result": execution_result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
