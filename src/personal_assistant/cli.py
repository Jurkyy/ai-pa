import click
import requests
import os
from pathlib import Path

BASE_URL = os.getenv("PA_API_URL", "http://localhost:8000/api/v1")
TOKEN_FILE = Path.home() / ".pa_token"

def get_token():
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None

def save_token(token):
    TOKEN_FILE.write_text(token)

@click.group()
def cli():
    """Personal Assistant CLI Tool"""
    pass

@cli.command()
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
def register(username, password):
    """Register a new user"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        click.echo(response.json()["message"])
    except requests.exceptions.RequestException as e:
        click.echo(f"Error registering user: {e.response.text if e.response else e}")

@cli.command()
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
def login(username, password):
    """Login and save the token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        save_token(token)
        click.echo("Login successful. Token saved.")
    except requests.exceptions.RequestException as e:
        click.echo(f"Error logging in: {e.response.text if e.response else e}")

@cli.command()
@click.argument("directory_path", type=click.Path(exists=True, file_okay=False))
def add_docs(directory_path):
    """Add documents from a directory to the RAG database"""
    token = get_token()
    if not token:
        click.echo("Please login first using `pa-cli login`")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(
            f"{BASE_URL}/rag/add-directory",
            headers=headers,
            json={"directory_path": directory_path} # Pass as JSON
        )
        response.raise_for_status()
        click.echo(response.json()["message"])
    except requests.exceptions.RequestException as e:
        click.echo(f"Error adding documents: {e.response.text if e.response else e}")

@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
def upload_doc(file_path):
    """Upload a single document to the RAG database"""
    token = get_token()
    if not token:
        click.echo("Please login first using `pa-cli login`")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f)}
            response = requests.post(
                f"{BASE_URL}/rag/upload",
                headers=headers,
                files=files
            )
        response.raise_for_status()
        click.echo(response.json()["message"])
    except requests.exceptions.RequestException as e:
        click.echo(f"Error uploading file: {e.response.text if e.response else e}")

@cli.command()
@click.argument("query")
@click.option("-k", default=4, help="Number of results to retrieve")
def search(query, k):
    """Search the RAG database"""
    token = get_token()
    if not token:
        click.echo("Please login first using `pa-cli login`")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(
            f"{BASE_URL}/rag/search",
            headers=headers,
            json={"query": query, "k": k}
        )
        response.raise_for_status()
        results = response.json()["results"]
        if results:
            click.echo(f"Found {len(results)} results:")
            for i, res in enumerate(results):
                click.echo(f"\n--- Result {i+1} ---")
                click.echo(f"Content: {res['content']}")
                click.echo(f"Metadata: {res['metadata']}")
                click.echo(f"Score: {res['score']:.4f}")
        else:
            click.echo("No results found.")
    except requests.exceptions.RequestException as e:
        click.echo(f"Error searching: {e.response.text if e.response else e}")

@cli.command()
@click.argument("text")
def process(text):
    """Send a natural language command to the assistant"""
    token = get_token()
    if not token:
        click.echo("Please login first using `pa-cli login`")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(
            f"{BASE_URL}/conversation/process",
            headers=headers,
            json={"text": text}
        )
        response.raise_for_status()
        click.echo("Assistant response:")
        click.echo(response.json())
    except requests.exceptions.RequestException as e:
        click.echo(f"Error processing command: {e.response.text if e.response else e}")

if __name__ == "__main__":
    cli() 